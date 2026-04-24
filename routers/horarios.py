from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from core.database import get_db
from core.security import get_current_user
from services.horario_service import HorarioService
from schemas.all_schemas import HorarioUpdate, HorarioResponse

router = APIRouter(prefix="/api/horarios", tags=["Horarios"])


def get_service(db: Session = Depends(get_db)) -> HorarioService:
    return HorarioService(db)


@router.get("/", response_model=List[HorarioResponse])
def get_horarios(
    service: HorarioService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    return service.listar(current_user.id)


@router.put("/", response_model=List[HorarioResponse])
def update_horarios(
    horarios: List[HorarioUpdate],
    service: HorarioService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    return service.actualizar(current_user.id, horarios)
