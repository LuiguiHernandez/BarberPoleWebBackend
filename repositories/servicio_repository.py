from typing import List, Optional
from sqlalchemy.orm import Session
from models.all_models import Servicio
from .base_repository import BaseRepository


class ServicioRepository(BaseRepository[Servicio]):
    def __init__(self, db: Session):
        super().__init__(Servicio, db)

    def get_by_negocio(self, negocio_id: int) -> List[Servicio]:
        return self.db.query(Servicio).filter(Servicio.negocio_id == negocio_id).all()

    def get_by_id_and_negocio(self, servicio_id: int, negocio_id: int) -> Optional[Servicio]:
        return (
            self.db.query(Servicio)
            .filter(Servicio.id == servicio_id, Servicio.negocio_id == negocio_id)
            .first()
        )

    def get_activos(self, negocio_id: int) -> List[Servicio]:
        return (
            self.db.query(Servicio)
            .filter(Servicio.negocio_id == negocio_id, Servicio.activo == True)
            .all()
        )
