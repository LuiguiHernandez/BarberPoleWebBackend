from typing import List
from sqlalchemy.orm import Session
from fastapi import HTTPException
from models.all_models import Horario
from repositories.horario_repository import HorarioRepository
from repositories.negocio_repository import NegocioRepository
from schemas.all_schemas import HorarioUpdate


class HorarioService:
    def __init__(self, db: Session):
        self.repo = HorarioRepository(db)
        self.negocio_repo = NegocioRepository(db)
        self.db = db

    def _negocio_id(self, usuario_id: int) -> int:
        negocio = self.negocio_repo.get_by_usuario_id(usuario_id)
        if not negocio:
            raise HTTPException(status_code=404, detail="Negocio no encontrado")
        return negocio.id

    def listar(self, usuario_id: int) -> List[Horario]:
        return self.repo.get_by_negocio(self._negocio_id(usuario_id))

    def actualizar(self, usuario_id: int, horarios_data: List[HorarioUpdate]) -> List[Horario]:
        negocio_id = self._negocio_id(usuario_id)
        for h_data in horarios_data:
            horario = self.repo.get_by_dia(negocio_id, h_data.dia)
            if horario:
                horario.abierto = h_data.abierto
                horario.hora_inicio = h_data.hora_inicio
                horario.hora_fin = h_data.hora_fin
            else:
                nuevo = Horario(
                    negocio_id=negocio_id,
                    dia=h_data.dia,
                    abierto=h_data.abierto,
                    hora_inicio=h_data.hora_inicio,
                    hora_fin=h_data.hora_fin,
                )
                self.db.add(nuevo)
        self.db.commit()
        return self.repo.get_by_negocio(negocio_id)
