from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from core.database import get_db
from services.carlos_service import CarlosService
from services.ai_engine import CarlosEngine
from services.whatsapp_service import WhatsAppService
from services.conversacion_service import ConversacionService
from schemas.all_schemas import WebhookMensajeEntrante

router = APIRouter()

# Función que procesa la IA en segundo plano
async def flujo_Carlos_completo(negocio_id: int, conversacion_id: int, telefono: str, mensaje: str, db: Session):
    carlos_service = CarlosService(db)
    ai_engine = CarlosEngine()
    ws_service = WhatsAppService()

    # 1. Obtener contexto (Las reglas del Dashboard)
    contexto = carlos_service.obtener_contexto_Carlos(negocio_id)
    
    # 2. Obtener historial (Contexto de la charla)
    historial = carlos_service.obtener_historial_reciente(conversacion_id)

    # 3. La IA genera la respuesta
    respuesta_texto = await ai_engine.pedir_respuesta(contexto, historial, mensaje)

    # 4. Guardar respuesta en el SaaS
    carlos_service.msg_repo.save_message(conversacion_id, respuesta_texto, "Carlos")

    # 5. Enviar a WhatsApp real vía Evolution API
    await ws_service.enviar_mensaje(telefono, respuesta_texto)

@router.post("/whatsapp/{negocio_slug}")
async def webhook_whatsapp(
    negocio_slug: str, 
    payload: WebhookMensajeEntrante, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db)
):
    conv_service = ConversacionService(db)
    
    # Procesa el mensaje entrante (Guarda en DB y asocia al negocio)
    res = conv_service.procesar_webhook(
        negocio_slug=negocio_slug, 
        telefono=payload.telefono, 
        nombre=payload.nombre, 
        mensaje_texto=payload.mensaje
    )

    negocio = res["negocio"]

    # Si el negocio tiene a carlos encendida, disparamos la IA en Background
    if negocio.carlos_activa:
        background_tasks.add_task(
            flujo_Carlos_completo,
            negocio_id=negocio.id,
            conversacion_id=res["conversacion_id"],
            telefono=payload.telefono,
            mensaje=payload.mensaje,
            db=db
        )

    return {"ok": True, "conversacion_id": res["conversacion_id"]}