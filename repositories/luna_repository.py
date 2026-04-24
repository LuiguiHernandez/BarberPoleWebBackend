from typing import List, Optional
from sqlalchemy.orm import Session
from models.all_models import LunaIndicacion
from .base_repository import BaseRepository


class LunaIndicacionRepository(BaseRepository[LunaIndicacion]):
    def __init__(self, db: Session):
        super().__init__(LunaIndicacion, db)

    def get_by_negocio(self, negocio_id: int) -> List[LunaIndicacion]:
        return (
            self.db.query(LunaIndicacion)
            .filter(LunaIndicacion.negocio_id == negocio_id)
            .all()
        )

    def get_activas(self, negocio_id: int) -> List[LunaIndicacion]:
        return (
            self.db.query(LunaIndicacion)
            .filter(
                LunaIndicacion.negocio_id == negocio_id,
                LunaIndicacion.activa == True,
            )
            .all()
        )

    def get_by_id_and_negocio(self, ind_id: int, negocio_id: int) -> Optional[LunaIndicacion]:
        return (
            self.db.query(LunaIndicacion)
            .filter(
                LunaIndicacion.id == ind_id,
                LunaIndicacion.negocio_id == negocio_id,
            )
            .first()
        )
