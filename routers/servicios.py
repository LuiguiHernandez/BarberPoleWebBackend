from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from core.database import get_db
from core.security import get_current_user
from services.servicio_service import ServicioService
from schemas.all_schemas import ServicioCreate, ServicioUpdate, ServicioResponse

router = APIRouter()


def get_service(db: Session = Depends(get_db)) -> ServicioService:
    return ServicioService(db)


@router.get("/", response_model=List[ServicioResponse])
def listar(
    service: ServicioService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    return service.listar(current_user.id)


@router.post("/", response_model=ServicioResponse, status_code=201)
def crear(
    data: ServicioCreate,
    service: ServicioService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    return service.crear(current_user.id, data)


@router.put("/{servicio_id}", response_model=ServicioResponse)
def actualizar(
    servicio_id: int,
    data: ServicioUpdate,
    service: ServicioService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    return service.actualizar(current_user.id, servicio_id, data)


@router.delete("/{servicio_id}", status_code=204)
def eliminar(
    servicio_id: int,
    service: ServicioService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    service.eliminar(current_user.id, servicio_id)
