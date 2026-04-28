from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from core.database import get_db
from core.security import get_current_user
from services.conversacion_service import ConversacionService
from schemas.all_schemas import (
    ConversacionResponse, MensajeResponse, EnviarMensajeRequest
)

router = APIRouter()


def get_service(db: Session = Depends(get_db)) -> ConversacionService:
    return ConversacionService(db)


@router.get("/", response_model=List[ConversacionResponse])
def listar(
    q: Optional[str] = None,
    service: ConversacionService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    return service.listar(current_user.id, q)


@router.get("/{conv_id}/mensajes", response_model=List[MensajeResponse])
def get_mensajes(
    conv_id: int,
    service: ConversacionService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    return service.mensajes(current_user.id, conv_id)


@router.post("/{conv_id}/responder")
async def responder(
    conv_id: int,
    data: EnviarMensajeRequest,
    service: ConversacionService = Depends(get_service),
    current_user=Depends(get_current_user),
):
    return await service.responder(current_user.id, conv_id, data.contenido)
