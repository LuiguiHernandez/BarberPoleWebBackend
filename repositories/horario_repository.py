from typing import List, Optional
from sqlalchemy.orm import Session
from models.all_models import Horario, DiaSemana
from .base_repository import BaseRepository


class HorarioRepository(BaseRepository[Horario]):
    def __init__(self, db: Session):
        super().__init__(Horario, db)

    def get_by_negocio(self, negocio_id: int) -> List[Horario]:
        return (
            self.db.query(Horario)
            .filter(Horario.negocio_id == negocio_id, Horario.barbero_id == None)
            .order_by(Horario.dia)
            .all()
        )

    def get_by_dia(self, negocio_id: int, dia: DiaSemana) -> Optional[Horario]:
        return (
            self.db.query(Horario)
            .filter(
                Horario.negocio_id == negocio_id,
                Horario.dia == dia,
                Horario.barbero_id == None,
            )
            .first()
        )
