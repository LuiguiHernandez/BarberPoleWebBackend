from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from models.all_models import Conversacion, Mensaje
from .base_repository import BaseRepository

class ConversacionRepository(BaseRepository[Conversacion]):
    def __init__(self, db: Session):
        super().__init__(Conversacion, db)

    def get_by_negocio(self, negocio_id: int, q: Optional[str] = None) -> List[Conversacion]:
        query = self.db.query(Conversacion).options(joinedload(Conversacion.cliente))\
            .filter(Conversacion.negocio_id == negocio_id)
        if q:
            search = f"%{q}%"
            query = query.filter(Conversacion.nombre_contacto.ilike(search) | Conversacion.telefono.ilike(search))
        return query.order_by(Conversacion.ultimo_mensaje_en.desc()).all()

    def get_by_telefono(self, negocio_id: int, telefono: str) -> Optional[Conversacion]:
        return self.db.query(Conversacion).filter(
            Conversacion.negocio_id == negocio_id,
            Conversacion.telefono == telefono.strip()
        ).first()

    def get_by_id_and_negocio(self, conv_id: int, negocio_id: int) -> Optional[Conversacion]:
        return self.db.query(Conversacion).filter(
            Conversacion.id == conv_id, 
            Conversacion.negocio_id == negocio_id
        ).first()

class MensajeRepository(BaseRepository[Mensaje]):
    def __init__(self, db: Session):
        super().__init__(Mensaje, db)

    def get_by_conversacion(self, conversacion_id: int) -> List[Mensaje]:
        return self.db.query(Mensaje).filter(Mensaje.conversacion_id == conversacion_id)\
            .order_by(Mensaje.enviado_en.asc()).all()

    def marcar_leidos(self, conversacion_id: int) -> None:
        self.db.query(Mensaje).filter(Mensaje.conversacion_id == conversacion_id, Mensaje.leido == False)\
            .update({"leido": True}, synchronize_session=False)

    # --- MÉTODO PARA SOLUCIONAR EL ATTRIBUTE ERROR ---
    def count_Carlos_by_negocio(self, negocio_id: int) -> int:
        """
        Cuenta los mensajes enviados por el asistente (Carlos) para un negocio específico.
        Se hace un join con Conversacion para filtrar por negocio_id.
        """
        return (
            self.db.query(Mensaje)
            .join(Conversacion)
            .filter(
                Conversacion.negocio_id == negocio_id,
                Mensaje.enviado_por == 'Carlos' # Verifica si este es el valor exacto en tu BD
            )
            .count()
        )