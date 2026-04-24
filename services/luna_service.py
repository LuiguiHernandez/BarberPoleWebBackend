from typing import List
from sqlalchemy.orm import Session
from fastapi import HTTPException
from models.all_models import LunaIndicacion
from repositories.luna_repository import LunaIndicacionRepository
from repositories.conversacion_repository import MensajeRepository
from repositories.cita_repository import CitaRepository
from repositories.negocio_repository import NegocioRepository
from schemas.all_schemas import LunaStats, LunaIndicacionCreate, LunaIndicacionUpdate


class LunaService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = LunaIndicacionRepository(db)
        self.negocio_repo = NegocioRepository(db)
        self.msg_repo = MensajeRepository(db)
        self.cita_repo = CitaRepository(db)

    def _negocio_id(self, usuario_id: int) -> int:
        negocio = self.negocio_repo.get_by_usuario_id(usuario_id)
        if not negocio:
            raise HTTPException(status_code=404, detail="Negocio no encontrado")
        return negocio.id

    def stats(self, usuario_id: int) -> LunaStats:
        negocio_id = self._negocio_id(usuario_id)
        mensajes = self.msg_repo.count_luna_by_negocio(negocio_id)
        citas_luna = self.cita_repo.count_creadas_por_luna(negocio_id)
        total_entrantes = self.msg_repo.count_cliente_by_negocio(negocio_id)
        tasa = (mensajes / total_entrantes * 100) if total_entrantes > 0 else 0
        return LunaStats(
            mensajes_respondidos=mensajes,
            citas_creadas_por_luna=citas_luna,
            tasa_respuesta=round(tasa, 1),
        )

    def indicaciones(self, usuario_id: int) -> List[LunaIndicacion]:
        return self.repo.get_by_negocio(self._negocio_id(usuario_id))

    def crear_indicacion(self, usuario_id: int, data: LunaIndicacionCreate) -> LunaIndicacion:
        negocio_id = self._negocio_id(usuario_id)
        ind = LunaIndicacion(negocio_id=negocio_id, texto=data.texto)
        return self.repo.create(ind)

    def toggle_indicacion(
        self, usuario_id: int, ind_id: int, data: LunaIndicacionUpdate
    ) -> LunaIndicacion:
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
