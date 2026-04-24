from typing import List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session
from models.all_models import Cliente
from .base_repository import BaseRepository


class ClienteRepository(BaseRepository[Cliente]):
    def __init__(self, db: Session):
        super().__init__(Cliente, db)

    def get_by_negocio(self, negocio_id: int, q: Optional[str] = None) -> List[Cliente]:
        query = self.db.query(Cliente).filter(Cliente.negocio_id == negocio_id)
        if q:
            query = query.filter(
                Cliente.nombre.ilike(f"%{q}%") | Cliente.telefono.ilike(f"%{q}%")
            )
        return query.order_by(Cliente.nombre).all()

    def get_by_telefono(self, negocio_id: int, telefono: str) -> Optional[Cliente]:
        return (
            self.db.query(Cliente)
            .filter(Cliente.negocio_id == negocio_id, Cliente.telefono == telefono)
            .first()
        )

    def count_by_negocio(self, negocio_id: int) -> int:
        return self.db.query(Cliente).filter(Cliente.negocio_id == negocio_id).count()

    def sum_recompensas(self, negocio_id: int) -> int:
        return (
            self.db.query(func.sum(Cliente.recompensas_canjeadas))
            .filter(Cliente.negocio_id == negocio_id)
            .scalar()
            or 0
        )
