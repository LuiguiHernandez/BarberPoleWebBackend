from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from core.database import get_db
from core.config import settings
from services.conversacion_service import ConversacionService
from services.whatsapp_service import WhatsAppService
from repositories.Carlos_repository import CarlosIndicacionRepository
from repositories.negocio_repository import NegocioRepository
from schemas.all_schemas import WebhookMensajeEntrante

router = APIRouter()


def get_conv_service(db: Session = Depends(get_db)) -> ConversacionService:
    return ConversacionService(db)


@router.post("/whatsapp/{negocio_slug}")
async def webhook_whatsapp(
    negocio_slug: str,
    payload: WebhookMensajeEntrante,
    service: ConversacionService = Depends(get_conv_service),
    db: Session = Depends(get_db),
):
    result = service.procesar_webhook(
        negocio_slug=negocio_slug,
        telefono=payload.telefono,
        nombre=payload.nombre,
        mensaje_texto=payload.mensaje,
    )

    negocio = result["negocio"]
    if negocio.Carlos_activa:
        Carlos_repo = CarlosIndicacionRepository(db)
        indicaciones = Carlos_repo.get_activas(negocio.id)

        contexto = {
            "data": {
                "key": {
                    "remoteJid": f"{payload.telefono}@s.whatsapp.net",
                    "fromMe": False,
                    "id": f"barberpole_{result['conversacion_id']}",
                },
                "message": {"conversation": payload.mensaje},
                "pushName": payload.nombre or payload.telefono,
                "instance": settings.EVOLUTION_INSTANCE,
            },
            "barberpole": {
                "negocio": negocio.nombre,
                "negocio_slug": negocio_slug,
                "conversacion_id": result["conversacion_id"],
                "indicaciones": [i.texto for i in indicaciones],
            },
        }

        import httpx
        try:
            async with httpx.AsyncClient() as client:
                await client.post(settings.N8N_WEBHOOK_URL, json=contexto, timeout=5)
        except Exception:
            pass

    return {"ok": True, "conversacion_id": result["conversacion_id"]}


@router.post("/Carlos-respuesta")
async def webhook_Carlos_respuesta(
    request: Request,
    service: ConversacionService = Depends(get_conv_service),
):
    data = await request.json()
    conversacion_id = data.get("conversacion_id")
    respuesta = data.get("respuesta")
    telefono = data.get("telefono")

    if not conversacion_id or not respuesta:
        raise HTTPException(status_code=400, detail="Faltan campos")

    conv = service.guardar_respuesta_Carlos(conversacion_id, respuesta, telefono)

    whatsapp = WhatsAppService()
    try:
        await whatsapp.enviar_mensaje(telefono or conv.telefono, respuesta)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Error enviando WhatsApp: {str(e)}")

    return {"ok": True}
