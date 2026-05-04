from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
import httpx
from core.config import settings
from core.database import get_db
from core.security import get_current_user
from services.conversacion_service import ConversacionService
from repositories.conversacion_repository import MensajeRepository, ConversacionRepository
from models.all_models import Mensaje
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


@router.post("/{conv_id}/sincronizar")
async def sincronizar_historial(
    conv_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Trae el historial de mensajes de Evolution API e importa los que faltan en la BD.
    Útil para ver mensajes anteriores a la configuración del webhook.
    """
    service = get_service(db)
    negocio_id = service._negocio_id(current_user.id)
    conv_repo = ConversacionRepository(db)
    conv = conv_repo.get_by_id_and_negocio(conv_id, negocio_id)
    if not conv:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Conversación no encontrada")

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{settings.EVOLUTION_API_URL}/chat/findMessages/{settings.EVOLUTION_INSTANCE}",
                headers={"apikey": settings.EVOLUTION_API_KEY},
                json={"where": {"key": {"remoteJid": f"{conv.telefono}@s.whatsapp.net"}}},
                timeout=15,
            )
            resp.raise_for_status()
            data_ev = resp.json()
    except httpx.HTTPStatusError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=502, detail=f"Evolution API error {e.response.status_code}")
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail=f"No se pudo conectar a Evolution API: {str(e)}")

    records = []
    if isinstance(data_ev, dict):
        records = data_ev.get("messages", {}).get("records", []) or data_ev.get("records", [])
    elif isinstance(data_ev, list):
        records = data_ev

    msg_repo = MensajeRepository(db)
    importados = 0
    for msg in records:
        contenido = (
            msg.get("message", {}).get("conversation")
            or msg.get("message", {}).get("extendedTextMessage", {}).get("text")
            or msg.get("message", {}).get("imageMessage", {}).get("caption")
        )
        if not contenido:
            continue

        from_me = msg.get("key", {}).get("fromMe", False)
        timestamp = msg.get("messageTimestamp")
        if not timestamp:
            continue

        try:
            msg_dt = datetime.fromtimestamp(int(timestamp), tz=timezone.utc).replace(tzinfo=None)
        except Exception:
            continue

        enviado_por = "barberia" if from_me else "cliente"

        existe = db.query(Mensaje).filter(
            Mensaje.conversacion_id == conv_id,
            Mensaje.enviado_en == msg_dt,
            Mensaje.enviado_por == enviado_por,
        ).first()

        if not existe:
            db.add(Mensaje(
                conversacion_id=conv_id,
                contenido=contenido,
                enviado_por=enviado_por,
                enviado_en=msg_dt,
                leido=True,
            ))
            importados += 1

    if importados > 0:
        db.commit()

    return {"ok": True, "mensajes_importados": importados, "total_en_whatsapp": len(records)}
