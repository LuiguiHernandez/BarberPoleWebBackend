from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from core.database import get_db
from core.security import get_current_user
from services.lealtad_service import LealtadService
from schemas.all_schemas import DarSelloRequest, LealtadResumen, ClienteResponse

router = APIRouter(prefix="/api/lealtad", tags=["Lealtad"])


def get_service(db: Session = Depends(get_db)) -> LealtadService:
    return LealtadService(db)


@router.get("/clientes", response_model=List[ClienteResponse])
def get_clientes(
    q: Optional[str] = None,
    service: LealtadService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    return service.clientes(current_user.id, q)


@router.post("/sello")
def dar_sello(
    data: DarSelloRequest,
    service: LealtadService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    return service.dar_sello(current_user.id, data.telefono)


@router.get("/resumen", response_model=LealtadResumen)
def get_resumen(
    service: LealtadService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    return service.resumen(current_user.id)
