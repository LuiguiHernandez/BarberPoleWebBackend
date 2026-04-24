from typing import Optional
from sqlalchemy.orm import Session
from models.all_models import Negocio
from .base_repository import BaseRepository


class NegocioRepository(BaseRepository[Negocio]):
    def __init__(self, db: Session):
        super().__init__(Negocio, db)

    def get_by_usuario_id(self, usuario_id: int) -> Optional[Negocio]:
        return self.db.query(Negocio).filter(Negocio.usuario_id == usuario_id).first()

    def get_by_slug(self, slug: str) -> Optional[Negocio]:
        return self.db.query(Negocio).filter(Negocio.slug == slug).first()
