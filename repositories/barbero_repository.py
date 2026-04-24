from typing import List, Optional
from sqlalchemy.orm import Session
from models.all_models import Barbero
from .base_repository import BaseRepository


class BarberoRepository(BaseRepository[Barbero]):
    def __init__(self, db: Session):
        super().__init__(Barbero, db)

    def get_by_negocio(self, negocio_id: int) -> List[Barbero]:
        return self.db.query(Barbero).filter(Barbero.negocio_id == negocio_id).all()

    def get_by_id_and_negocio(self, barbero_id: int, negocio_id: int) -> Optional[Barbero]:
        return (
            self.db.query(Barbero)
            .filter(Barbero.id == barbero_id, Barbero.negocio_id == negocio_id)
            .first()
        )

    def get_activos(self, negocio_id: int) -> List[Barbero]:
        return (
            self.db.query(Barbero)
            .filter(Barbero.negocio_id == negocio_id, Barbero.activo == True)
            .all()
        )
