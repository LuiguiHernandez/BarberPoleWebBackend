from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from core.database import get_db
from core.security import get_current_user
from services.luna_service import LunaService
from schemas.all_schemas import (
    LunaStats, LunaIndicacionCreate, LunaIndicacionResponse, LunaIndicacionUpdate
)

router = APIRouter(prefix="/api/luna", tags=["Luna IA"])


def get_service(db: Session = Depends(get_db)) -> LunaService:
    return LunaService(db)


@router.get("/stats", response_model=LunaStats)
def get_stats(
    service: LunaService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    return service.stats(current_user.id)


@router.get("/indicaciones", response_model=List[LunaIndicacionResponse])
def get_indicaciones(
    service: LunaService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    return service.indicaciones(current_user.id)


@router.post("/indicaciones", response_model=LunaIndicacionResponse, status_code=201)
def crear_indicacion(
    data: LunaIndicacionCreate,
    service: LunaService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    return service.crear_indicacion(current_user.id, data)


@router.put("/indicaciones/{ind_id}", response_model=LunaIndicacionResponse)
def toggle_indicacion(
    ind_id: int,
    data: LunaIndicacionUpdate,
    service: LunaService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    return service.toggle_indicacion(current_user.id, ind_id, data)


@router.delete("/indicaciones/{ind_id}", status_code=204)
def eliminar_indicacion(
    ind_id: int,
    service: LunaService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    service.eliminar_indicacion(current_user.id, ind_id)
