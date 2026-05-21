from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from core.database import get_db
from core.security import get_current_user
from services.profesional_service import ProfesionalService
from schemas.all_schemas import ProfesionalCreate, ProfesionalUpdate, ProfesionalResponse

router = APIRouter()


def get_service(db: Session = Depends(get_db)) -> ProfesionalService:
    return ProfesionalService(db)


@router.get("/", response_model=List[ProfesionalResponse])
def listar(
    service: ProfesionalService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    return service.listar(current_user.id)


@router.post("/", response_model=ProfesionalResponse, status_code=201)
def crear(
    data: ProfesionalCreate,
    service: ProfesionalService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    return service.crear(current_user.id, data)


@router.put("/{profesional_id}", response_model=ProfesionalResponse)
def actualizar(
    profesional_id: int,
    data: ProfesionalUpdate,
    service: ProfesionalService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    return service.actualizar(current_user.id, profesional_id, data)


@router.delete("/{profesional_id}", status_code=204)
def eliminar(
    profesional_id: int,
    service: ProfesionalService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    service.eliminar(current_user.id, profesional_id)


@router.post("/{profesional_id}/foto")
async def upload_foto(
    profesional_id: int,
    file: UploadFile = File(...),
    service: ProfesionalService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    """Sube foto de perfil del profesional."""
    return await service.upload_foto(current_user.id, profesional_id, file)
