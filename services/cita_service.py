from typing import List, Optional
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException
from models.all_models import Cita, Cliente, Servicio, EstadoCita
from repositories.cita_repository import CitaRepository
from repositories.negocio_repository import NegocioRepository
from repositories.cliente_repository import ClienteRepository
from repositories.servicio_repository import ServicioRepository
from schemas.all_schemas import CitaCreate, CitaUpdate, DashboardStats
from services.gcal_service import GoogleCalendarService
import logging

logger = logging.getLogger(__name__)


class CitaService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CitaRepository(db)
        self.negocio_repo = NegocioRepository(db)
        self.cliente_repo = ClienteRepository(db)
        self.servicio_repo = ServicioRepository(db)

    def _negocio_id(self, usuario_id: int) -> int:
        negocio = self.negocio_repo.get_by_usuario_id(usuario_id)
        if not negocio:
            raise HTTPException(status_code=404, detail="Negocio no encontrado")
        return negocio.id

    def dashboard_stats(self, usuario_id: int) -> DashboardStats:
        negocio_id = self._negocio_id(usuario_id)
        hoy = date.today()
        inicio_hoy = datetime.combine(hoy, datetime.min.time())
        fin_hoy = datetime.combine(hoy, datetime.max.time())
        inicio_semana = datetime.combine(
            hoy - timedelta(days=hoy.weekday()), datetime.min.time()
        )
        return DashboardStats(
            citas_hoy=self.repo.count_hoy(negocio_id, inicio_hoy, fin_hoy),
            ingresos_hoy=self.repo.sum_ingresos_hoy(negocio_id, inicio_hoy, fin_hoy),
            citas_semana=self.repo.count_semana(negocio_id, inicio_semana),
            confirmadas_hoy=self.repo.count_confirmadas_hoy(negocio_id, inicio_hoy, fin_hoy),
        )

    def listar(
        self,
        usuario_id: int,
        fecha: Optional[str],
        vista: str,
        barbero_id: Optional[int],
    ) -> List[Cita]:
        negocio_id = self._negocio_id(usuario_id)
        inicio, fin = None, None

        if fecha:
            try:
                fecha_dt = datetime.strptime(fecha, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(
                    status_code=400, detail="Formato de fecha inválido, usa YYYY-MM-DD"
                )
            if vista == "dia":
                inicio = datetime.combine(fecha_dt, datetime.min.time())
                fin = datetime.combine(fecha_dt, datetime.max.time())
            elif vista == "semana":
                inicio = datetime.combine(
                    fecha_dt - timedelta(days=fecha_dt.weekday()), datetime.min.time()
                )
                fin = inicio + timedelta(days=7)
            elif vista == "mes":
                inicio = datetime.combine(fecha_dt.replace(day=1), datetime.min.time())
                if fecha_dt.month == 12:
                    fin = datetime.combine(
                        fecha_dt.replace(year=fecha_dt.year + 1, month=1, day=1),
                        datetime.min.time(),
                    )
                else:
                    fin = datetime.combine(
                        fecha_dt.replace(month=fecha_dt.month + 1, day=1),
                        datetime.min.time(),
                    )
            else:
                inicio = datetime.combine(fecha_dt, datetime.min.time())
                fin = datetime.combine(fecha_dt, datetime.max.time())

        return self.repo.listar(negocio_id, inicio, fin, barbero_id)

    def crear(self, usuario_id: int, data: CitaCreate) -> Cita:
        negocio_id = self._negocio_id(usuario_id)

        cliente_id = data.cliente_id
        if not cliente_id and (data.cliente_nombre or data.cliente_telefono):
            cliente = None
            if data.cliente_telefono:
                cliente = self.cliente_repo.get_by_telefono(negocio_id, data.cliente_telefono)
            if not cliente:
                cliente = Cliente(
                    negocio_id=negocio_id,
                    nombre=data.cliente_nombre or data.cliente_telefono or "Cliente",
                    telefono=data.cliente_telefono,
                )
                self.db.add(cliente)
                self.db.flush()
            elif data.cliente_nombre and not cliente.nombre:
                # actualizar nombre si antes no tenía
                cliente.nombre = data.cliente_nombre
                self.db.flush()
            cliente_id = cliente.id

        precio, duracion = 0.0, 30
        if data.servicio_id:
            servicio = self.servicio_repo.get_by_id(data.servicio_id)
            if servicio:
                precio = servicio.precio
                duracion = servicio.duracion_minutos

        cita = Cita(
            negocio_id=negocio_id,
            cliente_id=cliente_id,
            barbero_id=data.barbero_id,
            servicio_id=data.servicio_id,
            fecha_hora=data.fecha_hora,
            duracion_minutos=duracion,
            precio=precio,
            notas=data.notas,
            estado=EstadoCita.pendiente,
            creada_manualmente=True,
            fuente=getattr(data, "fuente", "admin") or "admin",
        )
        self.db.add(cita)
        self.db.commit()
        self.db.refresh(cita)

        # Cargar relaciones y crear evento en Google Calendar
        cita_completa = self.repo.get_con_relaciones(cita.id)
        try:
            gcal = GoogleCalendarService(self.db)
            event_id = gcal.crear_evento(negocio_id, cita_completa)
            if event_id:
                cita.gcal_event_id = event_id
                self.db.commit()
                logger.info(f"[CITA] Evento GCal creado: {event_id}")
        except Exception as e:
            logger.warning(f"[CITA] GCal no disponible (no crítico): {e}")

        return self.repo.get_con_relaciones(cita.id)

    def actualizar(self, usuario_id: int, cita_id: int, data: CitaUpdate) -> Cita:
        negocio_id = self._negocio_id(usuario_id)
        cita = self.repo.get_by_id_and_negocio(cita_id, negocio_id)
        if not cita:
            raise HTTPException(status_code=404, detail="Cita no encontrada")

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(cita, field, value)

        if data.servicio_id:
            servicio = self.servicio_repo.get_by_id(data.servicio_id)
            if servicio:
                cita.precio = servicio.precio
                cita.duracion_minutos = servicio.duracion_minutos

        self.db.commit()

        # Actualizar título del evento en Google Calendar si cambió el estado
        if data.estado and cita.gcal_event_id:
            try:
                cita_completa = self.repo.get_con_relaciones(cita.id)
                gcal = GoogleCalendarService(self.db)
                if data.estado == "cancelada":
                    gcal.eliminar_evento(negocio_id, cita.gcal_event_id)
                    cita.gcal_event_id = None
                    self.db.commit()
                else:
                    gcal.actualizar_evento(negocio_id, cita_completa)
            except Exception as e:
                logger.warning(f"[CITA] GCal actualizar no crítico: {e}")

        return self.repo.get_con_relaciones(cita.id)

    def cancelar(self, usuario_id: int, cita_id: int) -> None:
        negocio_id = self._negocio_id(usuario_id)
        cita = self.repo.get_by_id_and_negocio(cita_id, negocio_id)
        if not cita:
            raise HTTPException(status_code=404, detail="Cita no encontrada")
        cita.estado = EstadoCita.cancelada
        self.db.commit()

        # Eliminar evento de Google Calendar si existe
        if cita.gcal_event_id:
            try:
                gcal = GoogleCalendarService(self.db)
                gcal.eliminar_evento(negocio_id, cita.gcal_event_id)
            except Exception as e:
                logger.warning(f"[CITA] No se pudo eliminar evento GCal: {e}")
