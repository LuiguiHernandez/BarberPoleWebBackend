"""
routers/wompi.py
─────────────────
Endpoints para la integración con Wompi.

GET  /api/wompi/link-pago   → Genera los datos para el widget de Wompi
POST /api/wompi/webhook     → Recibe eventos de Wompi (pago aprobado/rechazado)
GET  /api/wompi/estado      → Verifica si Wompi está configurado
"""

import logging
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from core.security import get_current_user
from core.config import settings

router = APIRouter(prefix="/api/wompi", tags=["Wompi"])
logger = logging.getLogger(__name__)


@router.get("/link-pago")
def generar_link_pago(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Genera los datos necesarios para renderizar el widget de Wompi en el frontend.

    El frontend necesita:
      - public_key: llave pública de Wompi
      - referencia: ID único de esta transacción
      - monto_centavos: precio en centavos ($250.000 = 25.000.000)
      - hash_integridad: SHA-256 para evitar manipulación del monto
      - redirect_url: a dónde redirigir tras el pago

    El widget de Wompi se embebe en el HTML con estos datos como atributos.
    """
    from repositories.negocio_repository import NegocioRepository
    from services.wompi_service import generar_referencia, generar_hash_integridad

    negocio = NegocioRepository(db).get_by_usuario_id(current_user.id)
    if not negocio:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")

    if not settings.WOMPI_PUBLIC_KEY:
        raise HTTPException(
            status_code=503,
            detail="Pasarela de pagos no configurada. Contacta con soporte."
        )

    referencia = generar_referencia(negocio.id)
    hash_integridad = generar_hash_integridad(referencia)
    frontend_url = settings.FRONTEND_URL.rstrip("/")

    return {
        "public_key":       settings.WOMPI_PUBLIC_KEY,
        "referencia":       referencia,
        "monto_centavos":   settings.WOMPI_PRECIO_CENTS,
        "moneda":           "COP",
        "hash_integridad":  hash_integridad,
        "descripcion":      f"GestorPro — Plan mensual {negocio.nombre}",
        "negocio_nombre":   negocio.nombre,
        "redirect_url":     f"{frontend_url}/dashboard/planes?pago=exitoso",
        "configurado":      True,
    }


@router.post("/webhook")
async def recibir_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Webhook que Wompi llama cuando ocurre un evento (pago aprobado, rechazado, etc.).

    Wompi envía un POST con:
      - Body JSON: el evento
      - Header x-event-checksum: firma HMAC-SHA256

    IMPORTANTE: Esta URL debe ser pública (no requiere autenticación).
    Configurar en el dashboard de Wompi: Ajustes → Webhooks → Agregar URL

    URL de producción: http://167.172.145.102:8000/api/wompi/webhook
    """
    try:
        body_bytes = await request.body()
        body_str   = body_bytes.decode("utf-8")
        evento     = await request.json()

        # Verificar firma del webhook
        firma = request.headers.get("x-event-checksum", "")
        from services.wompi_service import verificar_firma_webhook
        if firma and not verificar_firma_webhook(body_str, firma):
            logger.warning("[WOMPI] Firma de webhook inválida — posible ataque")
            raise HTTPException(status_code=401, detail="Firma inválida")

        # Procesar el evento
        from services.wompi_service import procesar_evento_pago
        resultado = procesar_evento_pago(evento, db)
        return {"ok": True, "resultado": resultado}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[WOMPI] Error procesando webhook: {e}")
        # Siempre responder 200 a Wompi aunque haya error interno
        # (si respondemos 5xx, Wompi reintenta múltiples veces)
        return {"ok": False, "error": str(e)}


@router.get("/estado")
def estado_wompi(current_user = Depends(get_current_user)):
    """
    Verifica si Wompi está configurado y retorna el ambiente activo.

    Útil para mostrar en la UI si los pagos están habilitados.
    """
    configurado = bool(settings.WOMPI_PUBLIC_KEY and settings.WOMPI_PRIVATE_KEY)
    sandbox = "stagtest" in settings.WOMPI_PUBLIC_KEY if settings.WOMPI_PUBLIC_KEY else True

    return {
        "configurado": configurado,
        "sandbox": sandbox,
        "precio_cop": settings.WOMPI_PRECIO_CENTS / 100,
        "ambiente": "sandbox" if sandbox else "produccion",
    }
