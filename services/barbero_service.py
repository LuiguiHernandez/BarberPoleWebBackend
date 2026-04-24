from typing import List
from sqlalchemy.orm import Session
from fastapi import HTTPException
from models.all_models import Barbero
from repositories.barbero_repository import BarberoRepository
from repositories.negocio_repository import NegocioRepository
from schemas.all_schemas import BarberoCreate, BarberoUpdate


class BarberoService:
    def __init__(self, db: Session):
        self.repo = BarberoRepository(db)
        self.negocio_repo = NegocioRepository(db)

    def _negocio_id(self, usuario_id: int) -> int:
        negocio = self.negocio_repo.get_by_usuario_id(usuario_id)
        if not negocio:
            raise HTTPException(status_code=404, detail="Negocio no encontrado")
        return negocio.id

    def listar(self, usuario_id: int) -> List[Barbero]:
        return self.repo.get_by_negocio(self._negocio_id(usuario_id))

    def crear(self, usuario_id: int, data: BarberoCreate) -> Barbero:
        negocio_id = self._negocio_id(usuario_id)
        barbero = Barbero(negocio_id=negocio_id, **data.model_dump())
        return self.repo.create(barbero)

    def actualizar(self, usuario_id: int, barbero_id: int, data: BarberoUpdate) -> Barbero:
        negocio_id = self._negocio_id(usuario_id)
        barbero = self.repo.get_by_id_and_negocio(barbero_id, negocio_id)
        if not barbero:
            raise HTTPException(status_code=404, detail="Barbero no encontrado")
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(barbero, field, value)
        return self.repo.update(barbero)

    def eliminar(self, usuario_id: int, barbero_id: int) -> None:
        negocio_id = self._negocio_id(usuario_id)
        barbero = self.repo.get_by_id_and_negocio(barbero_id, negocio_id)
        if not barbero:
            raise HTTPException(status_code=404, detail="Barbero no encontrado")
        self.repo.delete(barbero)
