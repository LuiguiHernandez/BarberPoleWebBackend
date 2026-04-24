import os
import aiofiles
from sqlalchemy.orm import Session
from fastapi import HTTPException, UploadFile
from models.all_models import Negocio
from repositories.negocio_repository import NegocioRepository
from schemas.all_schemas import NegocioUpdate, NegocioResponse


class NegocioService:
    def __init__(self, db: Session):
        self.repo = NegocioRepository(db)

    def _get_or_404(self, usuario_id: int) -> Negocio:
        negocio = self.repo.get_by_usuario_id(usuario_id)
        if not negocio:
            raise HTTPException(status_code=404, detail="Negocio no encontrado")
        return negocio

    def get(self, usuario_id: int) -> Negocio:
        return self._get_or_404(usuario_id)

    def update(self, usuario_id: int, data: NegocioUpdate) -> Negocio:
        negocio = self._get_or_404(usuario_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(negocio, field, value)
        return self.repo.update(negocio)

    async def upload_logo(self, usuario_id: int, file: UploadFile) -> dict:
        negocio = self._get_or_404(usuario_id)
        os.makedirs("uploads/logos", exist_ok=True)
        ext = file.filename.split(".")[-1]
        filename = f"uploads/logos/negocio_{negocio.id}.{ext}"
        async with aiofiles.open(filename, "wb") as f:
            content = await file.read()
            await f.write(content)
        negocio.logo_url = f"/{filename}"
        self.repo.update(negocio)
        return {"logo_url": negocio.logo_url}
