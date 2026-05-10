import logging
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

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

router = APIRouter()

# Función que procesa la IA en segundo plano
async def flujo_Carlos_completo(negocio_id: int, conversacion_id: int, telefono: str, mensaje: str):
    db = SessionLocal()
    try:
        if not settings.GEMINI_API_KEY:
            logger.error("[CARLOS] GEMINI_API_KEY no configurada — abortando")
            return

        logger.info(f"[CARLOS] Iniciando flujo para conv_id={conversacion_id}, telefono={telefono}")

        carlos_service = CarlosService(db)
        ai_engine = CarlosEngine()
        ws_service = WhatsAppService()

        contexto = carlos_service.obtener_contexto_Carlos(negocio_id)
        historial = carlos_service.obtener_historial_reciente(conversacion_id)

        logger.info(f"[CARLOS] Contexto ({len(contexto)} chars), historial ({len(historial)} chars). Llamando Gemini...")

        respuesta_texto = await ai_engine.pedir_respuesta(contexto, historial, mensaje)

        logger.info(f"[CARLOS] Respuesta Gemini: '{respuesta_texto[:80]}...'")

        carlos_service.msg_repo.save_message(conversacion_id, respuesta_texto, "carlos")
        conv = db.query(Conversacion).filter(Conversacion.id == conversacion_id).first()
        if conv:
            conv.ultimo_mensaje = respuesta_texto
            conv.ultimo_mensaje_en = datetime.utcnow()
            db.commit()

        ok = await ws_service.enviar_mensaje(telefono, respuesta_texto)
        logger.info(f"[CARLOS] Mensaje enviado vía Evolution API: ok={ok}")
    except Exception as e:
        logger.error(f"[CARLOS] Error en flujo_Carlos_completo: {e}", exc_info=True)
    finally:
        db.close()

@router.post("/whatsapp/{negocio_slug}")
async def webhook_whatsapp(negocio_slug: str, payload: dict, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    event_type = payload.get("event", "unknown")
    logger.info(f"[WEBHOOK] Evento recibido: event='{event_type}', slug='{negocio_slug}'")

    # Extraer capas de la Evolution API
    data = payload.get("data", {})
    key = data.get("key", {})
    message = data.get("message", {})

    # DETECCIÓN DE REMITENTE
    enviado_por_mi = data.get("fromMe") if data.get("fromMe") is not None else key.get("fromMe", False)

    # EXTRACCIÓN DE IDENTIDAD
    remote_jid = key.get("remoteJid", "")
    telefono = remote_jid.split("@")[0]
    nombre_cliente = data.get("pushName") if not enviado_por_mi else None

    mensaje_texto = message.get("conversation") or \
                    message.get("extendedTextMessage", {}).get("text", "")

    logger.info(f"[WEBHOOK] telefono='{telefono}', fromMe={enviado_por_mi}, texto='{mensaje_texto[:60] if mensaje_texto else None}'")

    if not mensaje_texto:
        logger.info(f"[WEBHOOK] Ignorado — sin texto. message_keys={list(message.keys())}")
        return {"status": "ignored", "reason": "no_text_payload"}

    conv_service = ConversacionService(db)
    res = conv_service.procesar_webhook(
        negocio_slug=negocio_slug,
        telefono=telefono,
        nombre=nombre_cliente,
        mensaje_texto=mensaje_texto,
        enviado_por_mi=enviado_por_mi
    )

    negocio = res.get("negocio")

    logger.info(
        f"[WEBHOOK] negocio encontrado={negocio is not None}, "
        f"carlos_activa={getattr(negocio, 'carlos_activa', 'N/A')}, "
        f"gemini_key_set={bool(settings.GEMINI_API_KEY)}, "
        f"fromMe={enviado_por_mi}"
    )

    if not enviado_por_mi and negocio and negocio.carlos_activa:
        logger.info(f"[WEBHOOK] Activando Carlos para conv_id={res.get('conversacion_id')}")
        background_tasks.add_task(
            flujo_Carlos_completo,
            negocio.id,
            res.get("conversacion_id"),
            telefono,
            mensaje_texto,
        )
    else:
        reasons = []
        if enviado_por_mi:
            reasons.append("mensaje enviado por mí")
        if not negocio:
            reasons.append(f"negocio slug '{negocio_slug}' no encontrado en BD")
        if negocio and not negocio.carlos_activa:
            reasons.append("carlos_activa=False (actívalo en el Dashboard)")
        if not settings.GEMINI_API_KEY:
            reasons.append("GEMINI_API_KEY no configurada")
        logger.info(f"[WEBHOOK] Carlos NO activado. Razones: {', '.join(reasons) or 'ninguna'}")

    return {"status": "success"}


@router.get("/diagnostico/{negocio_slug}")
async def diagnostico_webhook(negocio_slug: str, db: Session = Depends(get_db)):
    """Endpoint de diagnóstico — verifica si el sistema está listo para activar Carlos."""
    from repositories.negocio_repository import NegocioRepository
    negocio_repo = NegocioRepository(db)
    negocio = negocio_repo.get_by_slug(negocio_slug)

    return {
        "slug_buscado": negocio_slug,
        "negocio_encontrado": negocio is not None,
        "negocio_nombre": negocio.nombre if negocio else None,
        "carlos_activa": negocio.carlos_activa if negocio else None,
        "gemini_api_key_configurada": bool(settings.GEMINI_API_KEY),
        "evolution_api_url": settings.EVOLUTION_API_URL,
        "evolution_instance": settings.EVOLUTION_INSTANCE,
        "webhook_url_esperada": f"{settings.EVOLUTION_API_URL.replace(':8080', ':8000')}/api/webhooks/whatsapp/{negocio_slug}",
        "problema_detectado": (
            "carlos_activa=False — actívalo en el Dashboard" if negocio and not negocio.carlos_activa
            else "GEMINI_API_KEY no configurada" if not settings.GEMINI_API_KEY
            else f"negocio slug '{negocio_slug}' no existe en BD" if not negocio
            else "Configuración correcta ✓"
        ),
    }