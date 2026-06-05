"""
EmailService — Envío de emails transaccionales via Resend
Requiere RESEND_API_KEY en .env
"""
import logging
import httpx
from core.config import settings

logger = logging.getLogger(__name__)


async def send_email(to: str, subject: str, html: str) -> bool:
    """Envía un email usando Resend API."""
    api_key = getattr(settings, "RESEND_API_KEY", "")
    if not api_key:
        # En desarrollo sin API key, solo loguear
        logger.info(f"[EMAIL] (dev) Para: {to} | Asunto: {subject}")
        return True

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "from": getattr(settings, "EMAIL_FROM", "GestorPro <noreply@gestorpro.app>"),
                    "to": [to],
                    "subject": subject,
                    "html": html,
                },
            )
            ok = r.status_code in (200, 201)
            if not ok:
                logger.error(f"[EMAIL] Error {r.status_code}: {r.text[:200]}")
            return ok
    except Exception as e:
        logger.error(f"[EMAIL] Excepción: {e}")
        return False


def html_recuperar_password(nombre: str, link: str) -> str:
    return f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:40px 20px;">
        <div style="text-align:center;margin-bottom:32px;">
            <h1 style="color:#1A7C4F;font-size:28px;margin:0;">GestorPro</h1>
        </div>
        <h2 style="color:#1C2833;font-size:22px;">Recuperar contraseña</h2>
        <p style="color:#555;font-size:16px;">Hola <strong>{nombre}</strong>,</p>
        <p style="color:#555;font-size:16px;">
            Recibimos una solicitud para restablecer la contraseña de tu cuenta.
            Haz clic en el botón para crear una nueva contraseña:
        </p>
        <div style="text-align:center;margin:32px 0;">
            <a href="{link}" style="background:#1A7C4F;color:#fff;padding:14px 32px;
               border-radius:8px;text-decoration:none;font-size:16px;font-weight:bold;">
                Restablecer contraseña
            </a>
        </div>
        <p style="color:#999;font-size:14px;">
            Este enlace expira en <strong>1 hora</strong>. Si no solicitaste este cambio, ignora este mensaje.
        </p>
        <hr style="border:none;border-top:1px solid #eee;margin:32px 0;">
        <p style="color:#ccc;font-size:12px;text-align:center;">GestorPro SaaS — Plataforma de gestión de citas</p>
    </div>
    """


def html_bienvenida(nombre: str, negocio: str, link_verificar: str) -> str:
    return f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:40px 20px;">
        <div style="text-align:center;margin-bottom:32px;">
            <h1 style="color:#1A7C4F;font-size:28px;margin:0;">GestorPro</h1>
        </div>
        <h2 style="color:#1C2833;">¡Bienvenido, {nombre}! 🎉</h2>
        <p style="color:#555;font-size:16px;">
            Tu negocio <strong>{negocio}</strong> fue creado exitosamente.
            Confirma tu email para activar todas las funcionalidades:
        </p>
        <div style="text-align:center;margin:32px 0;">
            <a href="{link_verificar}" style="background:#1A7C4F;color:#fff;padding:14px 32px;
               border-radius:8px;text-decoration:none;font-size:16px;font-weight:bold;">
                Verificar email
            </a>
        </div>
        <p style="color:#999;font-size:14px;">
            Este enlace expira en <strong>24 horas</strong>.
        </p>
    </div>
    """
