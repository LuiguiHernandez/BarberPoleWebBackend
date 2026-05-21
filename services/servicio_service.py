from typing import List
from sqlalchemy.orm import Session
from fastapi import HTTPException
from models.all_models import Servicio
from repositories.servicio_repository import ServicioRepository
from repositories.negocio_repository import NegocioRepository
from schemas.all_schemas import ServicioCreate, ServicioUpdate


class ServicioService:
    def __init__(self, db: Session):
        self.repo = ServicioRepository(db)
        self.negocio_repo = NegocioRepository(db)

    def _negocio_id(self, usuario_id: int) -> int:
        negocio = self.negocio_repo.get_by_usuario_id(usuario_id)
        if not negocio:
            raise HTTPException(status_code=404, detail="Negocio no encontrado")
        return negocio.id

    def listar(self, usuario_id: int) -> List[Servicio]:
        return self.repo.get_by_negocio(self._negocio_id(usuario_id))

    def crear(self, usuario_id: int, data: ServicioCreate) -> Servicio:
        negocio_id = self._negocio_id(usuario_id)
        servicio = Servicio(negocio_id=negocio_id, **data.model_dump())
        return self.repo.create(servicio)

    def actualizar(self, usuario_id: int, servicio_id: int, data: ServicioUpdate) -> Servicio:
        negocio_id = self._negocio_id(usuario_id)
        servicio = self.repo.get_by_id_and_negocio(servicio_id, negocio_id)
        if not servicio:
            raise HTTPException(status_code=404, detail="Servicio no encontrado")
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(servicio, field, value)
        return self.repo.update(servicio)

    def eliminar(self, usuario_id: int, servicio_id: int) -> None:
        negocio_id = self._negocio_id(usuario_id)
        servicio = self.repo.get_by_id_and_negocio(servicio_id, negocio_id)
        if not servicio:
            raise HTTPException(status_code=404, detail="Servicio no encontrado")
        self.repo.delete(servicio)

    async def upload_imagen(self, usuario_id: int, servicio_id: int, file) -> dict:
        import os, aiofiles
        from sqlalchemy.orm import Session
        negocio_id = self._negocio_id(usuario_id)
        servicio = self.repo.db.query(Servicio).filter(
            Servicio.id == servicio_id, Servicio.negocio_id == negocio_id
        ).first()
        if not servicio:
            raise HTTPException(status_code=404, detail="Servicio no encontrado")
        os.makedirs("uploads/servicios", exist_ok=True)
        ext = file.filename.split(".")[-1].lower()
        filename = f"uploads/servicios/servicio_{servicio_id}.{ext}"
        async with aiofiles.open(filename, "wb") as f:
            content = await file.read()
            await f.write(content)
        servicio.imagen_url = f"/{filename}"
        self.repo.db.commit()
        self.repo.db.refresh(servicio)
        return {"imagen_url": servicio.imagen_url}
