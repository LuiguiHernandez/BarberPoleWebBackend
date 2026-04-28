from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from core.database import get_db
from core.security import get_current_user
from services.cita_service import CitaService
from schemas.all_schemas import CitaCreate, CitaUpdate, CitaResponse, DashboardStats

router = APIRouter()


def get_service(db: Session = Depends(get_db)) -> CitaService:
    return CitaService(db)


@router.get("/dashboard", response_model=DashboardStats)
def get_dashboard_stats(
    service: CitaService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    return service.dashboard_stats(current_user.id)


@router.get("/", response_model=List[CitaResponse])
def listar_citas(
    fecha: Optional[str] = Query(None, description="YYYY-MM-DD"),
    vista: str = Query("dia", description="dia | semana | mes"),
    barbero_id: Optional[int] = None,
    service: CitaService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    return service.listar(current_user.id, fecha, vista, barbero_id)


@router.post("/", response_model=CitaResponse, status_code=201)
def crear_cita(
    data: CitaCreate,
    service: CitaService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    return service.crear(current_user.id, data)


@router.put("/{cita_id}", response_model=CitaResponse)
def actualizar_cita(
    cita_id: int,
    data: CitaUpdate,
    service: CitaService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    return service.actualizar(current_user.id, cita_id, data)


@router.delete("/{cita_id}", status_code=204)
def cancelar_cita(
    cita_id: int,
    service: CitaService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    service.cancelar(current_user.id, cita_id)
