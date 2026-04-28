from typing import List
from sqlalchemy.orm import Session
from fastapi import HTTPException
from models.all_models import CarlosIndicacion
from repositories.carlos_repository import CarlosIndicacionRepository
from repositories.conversacion_repository import MensajeRepository
from repositories.cita_repository import CitaRepository
from repositories.negocio_repository import NegocioRepository
from schemas.all_schemas import CarlosStats, CarlosIndicacionCreate, CarlosIndicacionUpdate


class CarlosService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CarlosIndicacionRepository(db)
        self.negocio_repo = NegocioRepository(db)
        self.msg_repo = MensajeRepository(db)
        self.cita_repo = CitaRepository(db)

    def _negocio_id(self, usuario_id: int) -> int:
        negocio = self.negocio_repo.get_by_usuario_id(usuario_id)
        if not negocio:
            raise HTTPException(status_code=404, detail="Negocio no encontrado")
        return negocio.id

    def stats(self, usuario_id: int) -> CarlosStats:
        negocio_id = self._negocio_id(usuario_id)
        mensajes = self.msg_repo.count_Carlos_by_negocio(negocio_id)
        citas_Carlos = self.cita_repo.count_creadas_por_Carlos(negocio_id)
        total_entrantes = self.msg_repo.count_cliente_by_negocio(negocio_id)
        tasa = (mensajes / total_entrantes * 100) if total_entrantes > 0 else 0
        return CarlosStats(
            mensajes_respondidos=mensajes,
            citas_creadas_por_Carlos=citas_Carlos,
            tasa_respuesta=round(tasa, 1),
        )

    def indicaciones(self, usuario_id: int) -> List[CarlosIndicacion]:
        return self.repo.get_by_negocio(self._negocio_id(usuario_id))

    def crear_indicacion(self, usuario_id: int, data: CarlosIndicacionCreate) -> CarlosIndicacion:
        negocio_id = self._negocio_id(usuario_id)
        ind = CarlosIndicacion(negocio_id=negocio_id, texto=data.texto)
        return self.repo.create(ind)

    def toggle_indicacion(
        self, usuario_id: int, ind_id: int, data: CarlosIndicacionUpdate
    ) -> CarlosIndicacion:
        negocio_id = self._negocio_id(usuario_id)
        ind = self.repo.get_by_id_and_negocio(ind_id, negocio_id)
        if not ind:
            raise HTTPException(status_code=404, detail="Indicación no encontrada")
        ind.activa = data.activa
        return self.repo.update(ind)

    def eliminar_indicacion(self, usuario_id: int, ind_id: int) -> None:
        negocio_id = self._negocio_id(usuario_id)
        ind = self.repo.get_by_id_and_negocio(ind_id, negocio_id)
        if not ind:
            raise HTTPException(status_code=404, detail="Indicación no encontrada")
        self.repo.delete(ind)

    def obtener_contexto_Carlos(self, negocio_id: int) -> str:
        """Obtiene todas las indicaciones activas y las une en un solo texto"""
        indicaciones = self.repo.get_activas(negocio_id) # Asegúrate que el repo tenga get_activas
        if not indicaciones:
            return "Eres una recepcionista amable de una barbería."
        
        return " ".join([ind.texto for ind in indicaciones])

    def obtener_historial_reciente(self, conversacion_id: int, limite: int = 5) -> str:
        """Trae los últimos mensajes para que Carlos no sea amnésica"""
        mensajes = self.msg_repo.get_recent_by_conversacion(conversacion_id, limite)
        historial = ""
        for m in mensajes:
            rol = "Cliente" if m.enviado_por == "cliente" else "Carlos"
            historial += f"{rol}: {m.contenido}\n"
        return historial
