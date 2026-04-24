import httpx
from core.config import settings


class WhatsAppService:
    def __init__(self):
        self.base_url = settings.EVOLUTION_API_URL
        self.instance = settings.EVOLUTION_INSTANCE
        self.api_key = settings.EVOLUTION_API_KEY

    async def enviar_mensaje(self, telefono: str, mensaje: str) -> bool:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/message/sendText/{self.instance}",
                headers={"apikey": self.api_key},
                json={"number": telefono, "text": mensaje},
                timeout=10,
            )
            return resp.status_code == 200

    async def notificar_nueva_cita(
        self, telefono: str, nombre: str, servicio: str, fecha: str
    ) -> bool:
        mensaje = (
            f"✅ Hola {nombre}, tu cita está confirmada!\n"
            f"📋 Servicio: {servicio}\n"
            f"📅 Fecha: {fecha}\n"
            f"📍 {settings.APP_NAME}"
        )
        return await self.enviar_mensaje(telefono, mensaje)

    async def enviar_recordatorio(
        self, telefono: str, nombre: str, servicio: str, hora: str
    ) -> bool:
        mensaje = (
            f"⏰ Recordatorio: Hola {nombre}!\n"
            f"Tu cita de {servicio} es mañana a las {hora}.\n"
            f"¿Confirmas tu asistencia? Responde SÍ o NO."
        )
        return await self.enviar_mensaje(telefono, mensaje)

    async def notificar_cancelacion(
        self, telefono: str, nombre: str, servicio: str
    ) -> bool:
        mensaje = (
            f"❌ Hola {nombre}, tu cita de {servicio} ha sido cancelada.\n"
            f"Contáctanos para reprogramar."
        )
        return await self.enviar_mensaje(telefono, mensaje)
