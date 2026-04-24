from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from core.database import get_db
from core.security import get_current_user
from services.barbero_service import BarberoService
from schemas.all_schemas import BarberoCreate, BarberoUpdate, BarberoResponse

router = APIRouter(prefix="/api/barberos", tags=["Barberos"])


def get_service(db: Session = Depends(get_db)) -> BarberoService:
    return BarberoService(db)


@router.get("/", response_model=List[BarberoResponse])
def listar(
    service: BarberoService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    return service.listar(current_user.id)


@router.post("/", response_model=BarberoResponse, status_code=201)
def crear(
    data: BarberoCreate,
    service: BarberoService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    return service.crear(current_user.id, data)


@router.put("/{barbero_id}", response_model=BarberoResponse)
def actualizar(
    barbero_id: int,
    data: BarberoUpdate,
    service: BarberoService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    return service.actualizar(current_user.id, barbero_id, data)


@router.delete("/{barbero_id}", status_code=204)
def eliminar(
    barbero_id: int,
    service: BarberoService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    service.eliminar(current_user.id, barbero_id)
