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
    # Evolution API manda la info dentro de 'data'
    data = payload.get("data", {})
    message = data.get("message", {})

    # Extraemos los datos reales
    # El teléfono viene en 'key.remoteJid' (ej: 573001234567@s.whatsapp.net)
    remote_jid = data.get("key", {}).get("remoteJid", "")
    telefono = remote_jid.split("@")[0]

    nombre = data.get("pushName", "Cliente")

    # El mensaje puede venir en 'conversation' o 'extendedTextMessage'
    mensaje_texto = message.get("conversation") or \
                    message.get("extendedTextMessage", {}).get("text", "")
    
    if not mensaje_texto:
        return {"status": "ignored", "reason": "no_text_message"}

    conv_service = ConversacionService(db)

    # Aquí usamos las variables que acabamos de extraer
    res = await conv_service.procesar_webhook(
        negocio_slug=negocio_slug,
        telefono=telefono,
        nombre=nombre,
        mensaje_texto=mensaje_texto
    )
    return {"status": "success", "data": res}