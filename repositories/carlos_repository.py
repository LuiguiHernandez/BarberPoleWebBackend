from typing import List, Optional
from sqlalchemy.orm import Session
from models.all_models import CarlosIndicacion
from .base_repository import BaseRepository


class CarlosIndicacionRepository(BaseRepository[CarlosIndicacion]):
    def __init__(self, db: Session):
        super().__init__(CarlosIndicacion, db)

    def get_by_negocio(self, negocio_id: int) -> List[CarlosIndicacion]:
        return (
            self.db.query(CarlosIndicacion)
            .filter(CarlosIndicacion.negocio_id == negocio_id)
            .all()
        )

    def get_activas(self, negocio_id: int) -> List[CarlosIndicacion]:
        return (
            self.db.query(CarlosIndicacion)
            .filter(
                CarlosIndicacion.negocio_id == negocio_id,
                CarlosIndicacion.activa == True,
            )
            .all()
        )

    def get_by_id_and_negocio(self, ind_id: int, negocio_id: int) -> Optional[CarlosIndicacion]:
        return (
            self.db.query(CarlosIndicacion)
            .filter(
                CarlosIndicacion.id == ind_id,
                CarlosIndicacion.negocio_id == negocio_id,
            )
            .first()
        )
