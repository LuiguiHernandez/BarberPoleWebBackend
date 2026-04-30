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
async def webhook_whatsapp(negocio_slug: str, payload: dict, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
   # Extraemos la data de Evolution API
    data = payload.get("data", {})
    message = data.get("message", {})
    key = data.get("key", {})

    # 1. DETECCIÓN ROBUSTA DE REMITENTE
    # Revisamos en la raíz de data o dentro de key
    enviado_por_mi = data.get("fromMe") if data.get("fromMe") is not None else key.get("fromMe", False)

    # 2. EXTRACCIÓN DE DATOS
    remote_jid = key.get("remoteJid", "")
    telefono = remote_jid.split("@")[0]
    
    # IMPORTANTE: Solo tomamos el nombre del cliente si NO es un mensaje enviado por nosotros
    # Así evitamos que tu nombre de dueño sobreescriba el del cliente
    nombre_remitente = data.get("pushName") if not enviado_por_mi else None

    mensaje_texto = message.get("conversation") or \
                    message.get("extendedTextMessage", {}).get("text", "") or \
                    message.get("imageMessage", {}).get("caption", "")
    
    if not mensaje_texto:
        return {"status": "ignored", "reason": "empty_payload"}

    conv_service = ConversacionService(db)
    res = conv_service.procesar_webhook(
        negocio_slug=negocio_slug,
        telefono=telefono,
        nombre=nombre_remitente,
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