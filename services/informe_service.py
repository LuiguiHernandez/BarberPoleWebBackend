from typing import Optional
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException
from models.all_models import EstadoCita, Barbero
from repositories.cita_repository import CitaRepository
from repositories.negocio_repository import NegocioRepository
from schemas.all_schemas import InformesStats


class InformeService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CitaRepository(db)
        self.negocio_repo = NegocioRepository(db)

    def _negocio_id(self, usuario_id: int) -> int:
        negocio = self.negocio_repo.get_by_usuario_id(usuario_id)
        if not negocio:
            raise HTTPException(status_code=404, detail="Negocio no encontrado")
        return negocio.id

    def _calcular_rango(
        self,
        periodo: str,
        fecha_inicio: Optional[str],
        fecha_fin: Optional[str],
    ) -> tuple[datetime, datetime]:
        hoy = date.today()
        if periodo == "hoy":
            inicio = datetime.combine(hoy, datetime.min.time())
            fin = datetime.combine(hoy, datetime.max.time())
        elif periodo == "ayer":
            ayer = hoy - timedelta(days=1)
            inicio = datetime.combine(ayer, datetime.min.time())
            fin = datetime.combine(ayer, datetime.max.time())
        elif periodo == "7d":
            inicio = datetime.combine(hoy - timedelta(days=7), datetime.min.time())
            fin = datetime.combine(hoy, datetime.max.time())
        elif periodo == "personalizado" and fecha_inicio and fecha_fin:
            inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d")
            fin = datetime.strptime(fecha_fin, "%Y-%m-%d").replace(hour=23, minute=59)
        else:
            inicio = datetime.combine(hoy - timedelta(days=30), datetime.min.time())
            fin = datetime.combine(hoy, datetime.max.time())
        return inicio, fin

    def stats(
        self,
        usuario_id: int,
        periodo: str,
        fecha_inicio: Optional[str],
        fecha_fin: Optional[str],
    ) -> InformesStats:
        negocio_id = self._negocio_id(usuario_id)
        inicio, fin = self._calcular_rango(periodo, fecha_inicio, fecha_fin)
        citas = self.repo.get_en_periodo(negocio_id, inicio, fin)

        total = len(citas)
        completadas = sum(1 for c in citas if c.estado == EstadoCita.completada)
        ingresos = sum(c.precio for c in citas if c.estado == EstadoCita.completada)
        tasa = (completadas / total * 100) if total > 0 else 0

        por_estado: dict = {}
        for c in citas:
            por_estado[c.estado.value] = por_estado.get(c.estado.value, 0) + 1

        barberos_ingresos: dict = {}
        for c in citas:
            if c.estado == EstadoCita.completada and c.barbero_id:
                barbero = self.db.query(Barbero).filter(Barbero.id == c.barbero_id).first()
                nombre = barbero.nombre if barbero else "Sin asignar"
                barberos_ingresos[nombre] = barberos_ingresos.get(nombre, 0) + c.precio

        return InformesStats(
            total_citas=total,
            completadas=completadas,
            ingresos_totales=ingresos,
            tasa_completadas=round(tasa, 1),
            citas_por_estado=por_estado,
            ingresos_por_barbero=[
                {"barbero": k, "ingresos": v} for k, v in barberos_ingresos.items()
            ],
        )
