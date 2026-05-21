from typing import List, Optional
from sqlalchemy.orm import Session
from models.all_models import Barbero as Profesional
from .base_repository import BaseRepository


class ProfesionalRepository(BaseRepository[Profesional]):
    def __init__(self, db: Session):
        super().__init__(Profesional, db)

    def get_by_negocio(self, negocio_id: int) -> List[Profesional]:
        return self.db.query(Profesional).filter(Profesional.negocio_id == negocio_id).all()

    def get_by_id_and_negocio(self, profesional_id: int, negocio_id: int) -> Optional[Profesional]:
        return (
            self.db.query(Profesional)
            .filter(Profesional.id == profesional_id, Profesional.negocio_id == negocio_id)
            .first()
        )

    def get_activos(self, negocio_id: int) -> List[Profesional]:
        return (
            self.db.query(Profesional)
            .filter(Profesional.negocio_id == negocio_id, Profesional.activo == True)
            .all()
        )
