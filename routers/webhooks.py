from datetime import datetime
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from core.config import settings
from core.database import get_db, SessionLocal
from services.carlos_service import CarlosService
from services.ai_engine import CarlosEngine
from services.whatsapp_service import WhatsAppService
from services.conversacion_service import ConversacionService
from models.all_models import Conversacion
from schemas.all_schemas import WebhookMensajeEntrante

router = APIRouter()

# Función que procesa la IA en segundo plano
async def flujo_Carlos_completo(negocio_id: int, conversacion_id: int, telefono: str, mensaje: str):
    # Usa una sesión propia para el background task
    db = SessionLocal()
    try:
        if not settings.GEMINI_API_KEY:
            return

        carlos_service = CarlosService(db)
        ai_engine = CarlosEngine()
        ws_service = WhatsAppService()

        # 1. Obtener contexto (Las reglas del Dashboard)
        contexto = carlos_service.obtener_contexto_Carlos(negocio_id)

        # 2. Obtener historial (Contexto de la charla)
        historial = carlos_service.obtener_historial_reciente(conversacion_id)

        # 3. La IA genera la respuesta
        respuesta_texto = await ai_engine.pedir_respuesta(contexto, historial, mensaje)

        # 4. Guardar respuesta y actualizar conversación
        carlos_service.msg_repo.save_message(conversacion_id, respuesta_texto, "carlos")
        conv = db.query(Conversacion).filter(Conversacion.id == conversacion_id).first()
        if conv:
            conv.ultimo_mensaje = respuesta_texto
            conv.ultimo_mensaje_en = datetime.utcnow()
            db.commit()

        # 5. Enviar a WhatsApp real vía Evolution API
        await ws_service.enviar_mensaje(telefono, respuesta_texto)
    except Exception as e:
        print(f"Error en flujo_Carlos_completo: {e}")
    finally:
        db.close()

@router.post("/whatsapp/{negocio_slug}")
async def webhook_whatsapp(negocio_slug: str, payload: dict, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # Extraer capas de la Evolution API
    data = payload.get("data", {})
    key = data.get("key", {})
    message = data.get("message", {})

    # DETECCIÓN DE REMITENTE (Crucial para la alineación)
    # Buscamos 'fromMe' tanto en la raíz como dentro de 'key'
    enviado_por_mi = data.get("fromMe") if data.get("fromMe") is not None else key.get("fromMe", False)

    # EXTRACCIÓN DE IDENTIDAD
    remote_jid = key.get("remoteJid", "")
    telefono = remote_jid.split("@")[0]
    
    # Solo actualizamos el nombre si el mensaje NO es nuestro
    # Así evitamos que tu nombre de dueño pise el del cliente
    nombre_cliente = data.get("pushName") if not enviado_por_mi else None

    mensaje_texto = message.get("conversation") or \
                    message.get("extendedTextMessage", {}).get("text", "")
    
    if not mensaje_texto:
        return {"status": "ignored", "reason": "no_text_payload"}

    conv_service = ConversacionService(db)
    res = conv_service.procesar_webhook(
        negocio_slug=negocio_slug,
        telefono=telefono,
        nombre=nombre_cliente,
        mensaje_texto=mensaje_texto,
        enviado_por_mi=enviado_por_mi # <--- Pasamos el flag real
    )

    # Solo la IA responde si es un mensaje que ENTRA (no uno que tú envías)
    negocio = res.get("negocio")
    if not enviado_por_mi and negocio and negocio.carlos_activa:
        background_tasks.add_task(
            flujo_Carlos_completo,
            negocio.id,
            res.get("conversacion_id"),
            telefono,
            mensaje_texto,
        )

    return {"status": "success"}