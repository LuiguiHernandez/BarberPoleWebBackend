"""
WhatsAppService — Envío de mensajes vía Evolution API
Incluye: confirmación de cita, recordatorio 2h antes, resumen diario al dueño
"""
import httpx
import logging
from datetime import datetime
from core.config import settings

logger = logging.getLogger(__name__)

COLOMBIA_TZ = "America/Bogota"

class WhatsAppService:
    def __init__(self):
        self.base_url = settings.EVOLUTION_API_URL
        self.instance  = settings.EVOLUTION_INSTANCE
        self.api_key   = settings.EVOLUTION_API_KEY

    async def enviar_mensaje(self, telefono: str, mensaje: str) -> bool:
        """Envía un mensaje de texto vía Evolution API."""
        tel = telefono.replace("+", "").replace(" ", "").replace("-", "")
        if not tel.startswith("57"):
            tel = f"57{tel}"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{self.base_url}/message/sendText/{self.instance}",
                    headers={"apikey": self.api_key},
                    json={"number": tel, "text": mensaje},
                )
                ok = resp.status_code in (200, 201)
                if not ok:
                    logger.warning(f"[WA] Error {resp.status_code} enviando a {tel}: {resp.text[:200]}")
                return ok
        except Exception as e:
            logger.error(f"[WA] Excepción enviando a {tel}: {e}")
            return False

    # ── Confirmación de cita ─────────────────────────────────────
    async def confirmar_cita(
        self,
        telefono: str,
        nombre_cliente: str,
        nombre_negocio: str,
        servicio: str,
        fecha_hora: datetime,
        profesional: str = "",
        extras: list = None,
    ) -> bool:
        fecha_str = fecha_hora.strftime("%-d de %B de %Y")
        hora_str  = fecha_hora.strftime("%I:%M %p").replace("AM","a.m.").replace("PM","p.m.")

        servicios_txt = f"📋 *Servicio:* {servicio}"
        if extras:
            nombres_extra = ", ".join([e.get("nombre","") for e in extras if e.get("nombre")])
            if nombres_extra:
                servicios_txt += f"\n   + {nombres_extra}"

        prof_txt = f"\n👤 *Profesional:* {profesional}" if profesional else ""

        mensaje = (
            f"✅ *¡Cita confirmada!*\n\n"
            f"Hola *{nombre_cliente}*, tu reserva en *{nombre_negocio}* está lista 🎉\n\n"
            f"📅 *Fecha:* {fecha_str}\n"
            f"⏰ *Hora:* {hora_str}\n"
            f"{servicios_txt}{prof_txt}\n\n"
            f"Si necesitas cancelar o cambiar tu cita, contáctanos con tiempo 🙏"
        )
        logger.info(f"[WA] Enviando confirmación a {telefono}")
        return await self.enviar_mensaje(telefono, mensaje)

    # ── Recordatorio 2h antes ─────────────────────────────────────
    async def recordatorio_2h(
        self,
        telefono: str,
        nombre_cliente: str,
        nombre_negocio: str,
        servicio: str,
        hora: str,
        profesional: str = "",
        direccion: str = "",
    ) -> bool:
        prof_txt = f"\n👤 *Profesional:* {profesional}" if profesional else ""
        dir_txt  = f"\n📍 *Dirección:* {direccion}" if direccion else ""

        mensaje = (
            f"⏰ *Recordatorio de tu cita*\n\n"
            f"Hola *{nombre_cliente}*! Tu cita en *{nombre_negocio}* es en 2 horas 📍\n\n"
            f"🕐 *Hora:* {hora}\n"
            f"💆 *Servicio:* {servicio}"
            f"{prof_txt}{dir_txt}\n\n"
            f"¡Te esperamos! Si no puedes asistir, avísanos. 😊"
        )
        logger.info(f"[WA] Enviando recordatorio 2h a {telefono}")
        return await self.enviar_mensaje(telefono, mensaje)

    # ── Resumen diario al dueño ───────────────────────────────────
    async def resumen_diario(
        self,
        telefono_dueno: str,
        nombre_negocio: str,
        fecha_str: str,
        citas: list,  # [{nombre, hora, servicio, profesional}]
        total_estimado: float,
    ) -> bool:
        if not citas:
            mensaje = (
                f"☀️ *Buenos días, {nombre_negocio}!*\n\n"
                f"📅 Hoy *{fecha_str}* no tienes citas agendadas.\n\n"
                f"¡Buen día! 🌟"
            )
        else:
            lista = ""
            for c in citas:
                lista += f"\n• {c['hora']} — *{c['nombre']}* ({c['servicio']})"
                if c.get('profesional'):
                    lista += f" con {c['profesional']}"

            mensaje = (
                f"☀️ *Buenos días, {nombre_negocio}!*\n\n"
                f"📅 Hoy *{fecha_str}* tienes *{len(citas)} cita{'s' if len(citas)>1 else ''}*:{lista}\n\n"
                f"💰 *Ingresos estimados del día:* ${total_estimado:,.0f}\n\n"
                f"¡Que tengas un excelente día! 💪"
            )
        logger.info(f"[WA] Enviando resumen diario a {telefono_dueno}")
        return await self.enviar_mensaje(telefono_dueno, mensaje)

    # ── Cancelación ──────────────────────────────────────────────
    async def notificar_cancelacion(
        self, telefono: str, nombre: str, servicio: str, negocio: str = ""
    ) -> bool:
        neg = f" de *{negocio}*" if negocio else ""
        mensaje = (
            f"❌ *Cita cancelada*\n\n"
            f"Hola *{nombre}*, tu cita de *{servicio}*{neg} ha sido cancelada.\n\n"
            f"Si deseas reprogramar, con gusto te atendemos. 🙏"
        )
        return await self.enviar_mensaje(telefono, mensaje)
