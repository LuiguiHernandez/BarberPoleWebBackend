from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from core.database import get_db
from core.security import get_current_user
from services.Carlos_service import CarlosService
from schemas.all_schemas import (
    CarlosStats, CarlosIndicacionCreate, CarlosIndicacionResponse, CarlosIndicacionUpdate
)

router = APIRouter()


def get_service(db: Session = Depends(get_db)) -> CarlosService:
    return CarlosService(db)


@router.get("/stats", response_model=CarlosStats)
def get_stats(
    service: CarlosService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    return service.stats(current_user.id)


@router.get("/indicaciones", response_model=List[CarlosIndicacionResponse])
def get_indicaciones(
    service: CarlosService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    return service.indicaciones(current_user.id)


@router.post("/indicaciones", response_model=CarlosIndicacionResponse, status_code=201)
def crear_indicacion(
    data: CarlosIndicacionCreate,
    service: CarlosService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    return service.crear_indicacion(current_user.id, data)


@router.put("/indicaciones/{ind_id}", response_model=CarlosIndicacionResponse)
def toggle_indicacion(
    ind_id: int,
    data: CarlosIndicacionUpdate,
    service: CarlosService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    return service.toggle_indicacion(current_user.id, ind_id, data)


@router.delete("/indicaciones/{ind_id}", status_code=204)
def eliminar_indicacion(
    ind_id: int,
    service: CarlosService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    service.eliminar_indicacion(current_user.id, ind_id)
