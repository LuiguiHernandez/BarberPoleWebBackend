from typing import List, Optional
from datetime import datetime, date, timedelta
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from models.all_models import Cita, EstadoCita
from .base_repository import BaseRepository


class CitaRepository(BaseRepository[Cita]):
    def __init__(self, db: Session):
        super().__init__(Cita, db)

    def get_by_id_and_negocio(self, cita_id: int, negocio_id: int) -> Optional[Cita]:
        return (
            self.db.query(Cita)
            .filter(Cita.id == cita_id, Cita.negocio_id == negocio_id)
            .first()
        )

    def listar(
        self,
        negocio_id: int,
        inicio: Optional[datetime],
        fin: Optional[datetime],
        barbero_id: Optional[int],
    ) -> List[Cita]:
        query = (
            self.db.query(Cita)
            .options(
                joinedload(Cita.cliente),
                joinedload(Cita.barbero),
                joinedload(Cita.servicio),
            )
            .filter(Cita.negocio_id == negocio_id)
        )
        if barbero_id:
            query = query.filter(Cita.barbero_id == barbero_id)
        if inicio:
            query = query.filter(Cita.fecha_hora >= inicio)
        if fin:
            query = query.filter(Cita.fecha_hora < fin)
        return query.order_by(Cita.fecha_hora).all()

    def get_con_relaciones(self, cita_id: int) -> Optional[Cita]:
        return (
            self.db.query(Cita)
            .options(
                joinedload(Cita.cliente),
                joinedload(Cita.barbero),
                joinedload(Cita.servicio),
            )
            .filter(Cita.id == cita_id)
            .first()
        )

    def count_hoy(self, negocio_id: int, inicio: datetime, fin: datetime) -> int:
        return (
            self.db.query(Cita)
            .filter(
                Cita.negocio_id == negocio_id,
                Cita.fecha_hora >= inicio,
                Cita.fecha_hora <= fin,
                Cita.estado != EstadoCita.cancelada,
            )
            .count()
        )

    def sum_ingresos_hoy(self, negocio_id: int, inicio: datetime, fin: datetime) -> float:
        return (
            self.db.query(func.sum(Cita.precio))
            .filter(
                Cita.negocio_id == negocio_id,
                Cita.fecha_hora >= inicio,
                Cita.fecha_hora <= fin,
                Cita.estado == EstadoCita.completada,
            )
            .scalar()
            or 0.0
        )

    def count_semana(self, negocio_id: int, inicio_semana: datetime) -> int:
        return (
            self.db.query(Cita)
            .filter(
                Cita.negocio_id == negocio_id,
                Cita.fecha_hora >= inicio_semana,
                Cita.estado != EstadoCita.cancelada,
            )
            .count()
        )

    def count_confirmadas_hoy(self, negocio_id: int, inicio: datetime, fin: datetime) -> int:
        return (
            self.db.query(Cita)
            .filter(
                Cita.negocio_id == negocio_id,
                Cita.fecha_hora >= inicio,
                Cita.fecha_hora <= fin,
                Cita.estado == EstadoCita.confirmada,
            )
            .count()
        )

    def get_en_periodo(self, negocio_id: int, inicio: datetime, fin: datetime) -> List[Cita]:
        return (
            self.db.query(Cita)
            .filter(
                Cita.negocio_id == negocio_id,
                Cita.fecha_hora >= inicio,
                Cita.fecha_hora <= fin,
            )
            .all()
        )

    def count_creadas_por_Carlos(self, negocio_id: int) -> int:
        return (
            self.db.query(Cita)
            .filter(Cita.negocio_id == negocio_id, Cita.creada_por_Carlos == True)
            .count()
        )
