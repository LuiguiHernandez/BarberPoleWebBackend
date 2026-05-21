from typing import List
from sqlalchemy.orm import Session
from fastapi import HTTPException
from models.all_models import Barbero as Profesional
from repositories.profesional_repository import ProfesionalRepository
from repositories.negocio_repository import NegocioRepository
from schemas.all_schemas import ProfesionalCreate, ProfesionalUpdate


class ProfesionalService:
    def __init__(self, db: Session):
        self.repo = ProfesionalRepository(db)
        self.negocio_repo = NegocioRepository(db)
        self.db = db

    def _negocio_id(self, usuario_id: int) -> int:
        negocio = self.negocio_repo.get_by_usuario_id(usuario_id)
        if not negocio:
            raise HTTPException(status_code=404, detail="Negocio no encontrado")
        return negocio.id

    def listar(self, usuario_id: int) -> List[Profesional]:
        return self.repo.get_by_negocio(self._negocio_id(usuario_id))

    def crear(self, usuario_id: int, data: ProfesionalCreate) -> Profesional:
        negocio_id = self._negocio_id(usuario_id)
        profesional = Profesional(negocio_id=negocio_id, **data.model_dump())
        return self.repo.create(profesional)

    def actualizar(self, usuario_id: int, profesional_id: int, data: ProfesionalUpdate) -> Profesional:
        negocio_id = self._negocio_id(usuario_id)
        profesional = self.repo.get_by_id_and_negocio(profesional_id, negocio_id)
        if not profesional:
            raise HTTPException(status_code=404, detail="Profesional no encontrado")
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(profesional, field, value)
        return self.repo.update(profesional)

    def eliminar(self, usuario_id: int, profesional_id: int) -> None:
        negocio_id = self._negocio_id(usuario_id)
        profesional = self.repo.get_by_id_and_negocio(profesional_id, negocio_id)
        if not profesional:
            raise HTTPException(status_code=404, detail="Profesional no encontrado")
        self.repo.delete(profesional)

    async def upload_foto(self, usuario_id: int, profesional_id: int, file) -> dict:
        import os, aiofiles
        negocio_id = self._negocio_id(usuario_id)
        profesional = self.db.query(Profesional).filter(
            Profesional.id == profesional_id,
            Profesional.negocio_id == negocio_id
        ).first()
        if not profesional:
            raise HTTPException(status_code=404, detail="Profesional no encontrado")
        os.makedirs("uploads/profesionales", exist_ok=True)
        ext = (file.filename or "foto.jpg").split(".")[-1].lower()
        filename = f"uploads/profesionales/profesional_{profesional_id}.{ext}"
        async with aiofiles.open(filename, "wb") as f:
            content = await file.read()
            await f.write(content)
        profesional.foto_url = f"/{filename}"
        self.db.commit()
        self.db.refresh(profesional)
        return {"foto_url": profesional.foto_url}
