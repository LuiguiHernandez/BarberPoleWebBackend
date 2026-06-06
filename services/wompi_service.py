"""
services/wompi_service.py
─────────────────────────
Integración con Wompi — pasarela de pagos de Bancolombia.

Flujo de suscripción:
  1. Frontend carga el widget de Wompi con los datos del pago
  2. Cliente paga (PSE, tarjeta, Nequi, Daviplata)
  3. Wompi envía evento a POST /api/wompi/webhook
  4. Backend verifica la firma del evento
  5. Si el pago fue aprobado → activa el plan del negocio

Configuración requerida en .env:
  WOMPI_PUBLIC_KEY        → llave pública (pub_prod_xxx o pub_stagtest_xxx)
  WOMPI_PRIVATE_KEY       → llave privada (prv_prod_xxx o prv_stagtest_xxx)
  WOMPI_EVENTS_SECRET     → secret para verificar firma del webhook
  WOMPI_INTEGRITY_SECRET  → secret para generar hash del widget
  WOMPI_PRECIO_CENTS      → precio en centavos ($250.000 COP = 25000000)

Ambiente sandbox para pruebas:
  Registrar en comercios.wompi.co → Sandbox → obtener llaves de prueba
  Tarjeta de prueba: 4242 4242 4242 4242, CVC: 123, cualquier fecha futura
"""

import hashlib
import hmac
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def generar_referencia(negocio_id: int) -> str:
    """
    Genera una referencia única para la transacción.
    Formato: GESTORPRO-{negocio_id}-{timestamp}
    Esta referencia identifica el pago y se guarda en la BD.
    """
    ts = int(datetime.now(timezone.utc).timestamp())
    return f"GESTORPRO-{negocio_id}-{ts}"


def generar_hash_integridad(referencia: str) -> str:
    """
    Genera el hash de integridad requerido por el widget de Wompi.

    Wompi requiere un SHA-256 de: referencia + monto + moneda + integrity_secret
    Esto previene que alguien manipule el monto en el frontend.

    Docs: https://docs.wompi.co/docs/colombia/widget-de-pagos/#integridad
    """
    from core.config import settings

    if not settings.WOMPI_INTEGRITY_SECRET:
        logger.warning("[WOMPI] WOMPI_INTEGRITY_SECRET no configurado — hash vacío (solo para dev)")
        return ""

    cadena = (
        f"{referencia}"
        f"{settings.WOMPI_PRECIO_CENTS}"
        f"COP"
        f"{settings.WOMPI_INTEGRITY_SECRET}"
    )
    return hashlib.sha256(cadena.encode()).hexdigest()


def verificar_firma_webhook(payload_str: str, firma_recibida: str) -> bool:
    """
    Verifica que el webhook realmente viene de Wompi.

    Wompi firma cada evento con HMAC-SHA256 usando el events_secret.
    Si la firma no coincide, el evento es inválido (posible ataque).

    Args:
        payload_str: El body del webhook como string
        firma_recibida: El valor del header 'x-event-checksum'

    Returns:
        True si la firma es válida, False si no.
    """
    from core.config import settings

    if not settings.WOMPI_EVENTS_SECRET:
        logger.warning("[WOMPI] WOMPI_EVENTS_SECRET no configurado — omitiendo verificación")
        return True  # En dev sin secret configurado, aceptar todo

    firma_esperada = hmac.new(
        settings.WOMPI_EVENTS_SECRET.encode(),
        payload_str.encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(firma_esperada, firma_recibida)


def procesar_evento_pago(evento: dict, db) -> dict:
    """
    Procesa un evento de webhook de Wompi.

    Eventos que manejamos:
      - transaction.updated: una transacción cambió de estado
        * status APPROVED  → activar plan del negocio
        * status DECLINED  → registrar fallo
        * status VOIDED    → transacción anulada

    La referencia del pago tiene el formato GESTORPRO-{negocio_id}-{ts}
    Con eso sabemos a qué negocio pertenece el pago.
    """
    evento_tipo = evento.get("event", "")
    data = evento.get("data", {})

    if evento_tipo != "transaction.updated":
        return {"ok": True, "ignorado": True, "evento": evento_tipo}

    transaccion = data.get("transaction", {})
    status       = transaccion.get("status", "")
    referencia   = transaccion.get("reference", "")
    monto        = transaccion.get("amountInCents", 0)
    metodo_pago  = transaccion.get("paymentMethodType", "")

    logger.info(f"[WOMPI] Evento: {evento_tipo} | Status: {status} | Ref: {referencia}")

    # Extraer negocio_id de la referencia (formato: GESTORPRO-{id}-{ts})
    partes = referencia.split("-")
    if len(partes) < 2 or partes[0] != "GESTORPRO":
        logger.warning(f"[WOMPI] Referencia no reconocida: {referencia}")
        return {"ok": False, "error": "Referencia no reconocida"}

    try:
        negocio_id = int(partes[1])
    except (ValueError, IndexError):
        logger.error(f"[WOMPI] No se pudo extraer negocio_id de: {referencia}")
        return {"ok": False, "error": "negocio_id inválido en referencia"}

    from models.all_models import Negocio
    negocio = db.query(Negocio).filter(Negocio.id == negocio_id).first()
    if not negocio:
        logger.error(f"[WOMPI] Negocio {negocio_id} no encontrado")
        return {"ok": False, "error": "Negocio no encontrado"}

    if status == "APPROVED":
        # Pago aprobado → activar el plan por 32 días (margen de gracia)
        from services.plan_service import activar_plan
        activar_plan(negocio, db)
        logger.info(f"[WOMPI] ✅ Plan activado para negocio {negocio_id} ({negocio.nombre})")
        logger.info(f"[WOMPI]    Monto: ${monto/100:,.0f} COP | Método: {metodo_pago}")
        return {"ok": True, "accion": "plan_activado", "negocio_id": negocio_id}

    elif status in ("DECLINED", "ERROR"):
        logger.warning(f"[WOMPI] ❌ Pago rechazado para negocio {negocio_id}: {status}")
        return {"ok": True, "accion": "pago_rechazado", "negocio_id": negocio_id}

    elif status == "VOIDED":
        logger.info(f"[WOMPI] Transacción anulada para negocio {negocio_id}")
        return {"ok": True, "accion": "anulado", "negocio_id": negocio_id}

    return {"ok": True, "accion": "ignorado", "status": status}
