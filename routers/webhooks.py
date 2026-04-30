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
    payload: dict, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db)
):
    data = payload.get("data", {})
    message = data.get("message", {})
    key = data.get("key", {})

    # Detectar si el mensaje fue enviado desde el celular del negocio
    enviado_por_mi = key.get("fromMe", False)

    remote_jid = key.get("remoteJid", "")
    telefono = remote_jid.split("@")[0]
    nombre = data.get("pushName") # El nombre que configuró el cliente en su WhatsApp

    mensaje_texto = message.get("conversation") or \
                    message.get("extendedTextMessage", {}).get("text", "")
    
    if not mensaje_texto:
        return {"status": "ignored", "reason": "no_text_message"}

    conv_service = ConversacionService(db)
    res = conv_service.procesar_webhook(
        negocio_slug=negocio_slug,
        telefono=telefono,
        nombre=nombre,
        mensaje_texto=mensaje_texto,
        enviado_por_mi=enviado_por_mi
    )

    # Disparar a Carlos solo si el mensaje es del cliente
    negocio = res.get("negocio")
    if not enviado_por_mi and negocio and negocio.carlos_activa:
        background_tasks.add_task(
            flujo_Carlos_completo,
            negocio.id,
            res.get("conversacion_id"),
            telefono,
            mensaje_texto,
            db
        )

    return {"status": "success", "data": res}