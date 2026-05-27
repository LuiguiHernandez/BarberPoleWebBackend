"""
KommoService — Integración con Kommo CRM
Maneja: OAuth2, envío de mensajes, recepción de webhooks
Plan Base soportado (webhooks + API REST)
"""
import httpx
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException
from models.all_models import Negocio, Conversacion, Mensaje, Cliente
from repositories.negocio_repository import NegocioRepository

logger = logging.getLogger(__name__)


class KommoService:
    def __init__(self, db: Session):
        self.db = db
        self.negocio_repo = NegocioRepository(db)

    # ── Helpers ──────────────────────────────────────────────────
    def _get_negocio(self, negocio_id: int) -> Negocio:
        n = self.db.query(Negocio).filter(Negocio.id == negocio_id).first()
        if not n:
            raise HTTPException(status_code=404, detail="Negocio no encontrado")
        return n

    def _get_negocio_by_slug(self, slug: str) -> Negocio:
        n = self.db.query(Negocio).filter(Negocio.slug == slug).first()
        if not n:
            raise HTTPException(status_code=404, detail=f"Negocio '{slug}' no encontrado")
        return n

    def _headers(self, negocio: Negocio) -> dict:
        return {
            "Authorization": f"Bearer {negocio.kommo_access_token}",
            "Content-Type": "application/json",
        }

    # ── Estado de conexión ────────────────────────────────────────
    def estado(self, usuario_id: int) -> dict:
        negocio = self.negocio_repo.get_by_usuario_id(usuario_id)
        if not negocio:
            raise HTTPException(status_code=404, detail="Negocio no encontrado")
        return {
            "conectado": negocio.kommo_connected or False,
            "account_id": negocio.kommo_account_id,
            "base_url": negocio.kommo_base_url,
        }

    # ── Conectar con token manual (Plan Base — no OAuth web) ──────
    def conectar_manual(self, usuario_id: int, access_token: str, base_url: str) -> dict:
        """
        Plan Base de Kommo no permite OAuth web desde apps externas fácilmente.
        El usuario obtiene su long-lived token desde Kommo → Ajustes → API
        y lo pega en GestorPro.
        """
        negocio = self.negocio_repo.get_by_usuario_id(usuario_id)
        if not negocio:
            raise HTTPException(status_code=404, detail="Negocio no encontrado")

        # Verificar que el token funciona
        base = base_url.rstrip("/")
        try:
            r = httpx.get(
                f"{base}/api/v4/account",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10,
            )
            if r.status_code != 200:
                raise HTTPException(status_code=400, detail=f"Token inválido. Kommo respondió: {r.status_code}")
            account_data = r.json()
            account_id = str(account_data.get("id", ""))
        except httpx.TimeoutException:
            raise HTTPException(status_code=408, detail="Timeout al conectar con Kommo")

        negocio.kommo_access_token = access_token
        negocio.kommo_base_url     = base
        negocio.kommo_account_id   = account_id
        negocio.kommo_connected    = True
        self.db.commit()

        return {
            "ok": True,
            "conectado": True,
            "account_id": account_id,
            "mensaje": f"Kommo conectado correctamente — cuenta {account_id}",
        }

    def desconectar(self, usuario_id: int) -> dict:
        negocio = self.negocio_repo.get_by_usuario_id(usuario_id)
        if not negocio:
            raise HTTPException(status_code=404, detail="Negocio no encontrado")
        negocio.kommo_access_token  = None
        negocio.kommo_refresh_token = None
        negocio.kommo_base_url      = None
        negocio.kommo_account_id    = None
        negocio.kommo_connected     = False
        self.db.commit()
        return {"ok": True, "conectado": False}

    # ── Enviar mensaje vía Kommo ──────────────────────────────────
    async def enviar_mensaje(self, negocio_id: int, telefono: str, texto: str) -> dict:
        """
        Envía un mensaje de WhatsApp a través de Kommo.
        Busca o crea el contacto en Kommo y envía el mensaje.
        """
        negocio = self._get_negocio(negocio_id)
        if not negocio.kommo_connected or not negocio.kommo_access_token:
            raise HTTPException(status_code=400, detail="Kommo no está conectado en este negocio")

        base = negocio.kommo_base_url
        headers = self._headers(negocio)

        # 1. Buscar contacto por teléfono
        tel_limpio = telefono.replace("+", "").replace(" ", "").replace("-", "")
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                f"{base}/api/v4/contacts",
                headers=headers,
                params={"query": tel_limpio},
            )
            contacts = r.json().get("_embedded", {}).get("contacts", []) if r.status_code == 200 else []

            contact_id = None
            if contacts:
                contact_id = contacts[0]["id"]
            else:
                # Crear contacto nuevo
                rc = await client.post(
                    f"{base}/api/v4/contacts",
                    headers=headers,
                    json=[{"name": telefono, "custom_fields_values": [
                        {"field_code": "PHONE", "values": [{"value": telefono, "enum_code": "WORK"}]}
                    ]}],
                )
                if rc.status_code in (200, 201):
                    created = rc.json().get("_embedded", {}).get("contacts", [])
                    contact_id = created[0]["id"] if created else None

            if not contact_id:
                raise HTTPException(status_code=500, detail="No se pudo encontrar o crear el contacto en Kommo")

            # 2. Enviar mensaje vía Talk (mensajería de Kommo)
            rm = await client.post(
                f"{base}/api/v4/talks",
                headers=headers,
                json={
                    "entity_type": "contacts",
                    "entity_id": contact_id,
                    "message": {"text": texto},
                },
            )

            if rm.status_code not in (200, 201):
                # Fallback: crear nota en el contacto
                await client.post(
                    f"{base}/api/v4/contacts/{contact_id}/notes",
                    headers=headers,
                    json=[{"note_type": "COMMON", "params": {"text": f"[GestorPro] {texto}"}}],
                )

        return {"ok": True, "contact_id": contact_id}

    # ── Procesar webhook entrante de Kommo ────────────────────────
    def procesar_webhook(self, slug: str, payload: dict) -> dict:
        """
        Recibe el webhook de Kommo cuando llega un mensaje de WhatsApp.
        Payload varía según tipo de evento — manejamos 'message' principalmente.
        """
        negocio = self._get_negocio_by_slug(slug)

        # Kommo puede enviar diferentes estructuras
        # Intentamos extraer el mensaje de las estructuras más comunes
        telefono = None
        texto    = None
        nombre   = None

        # Estructura 1: mensaje directo de Talk/WhatsApp
        if "message" in payload:
            msg = payload["message"]
            telefono = (msg.get("from") or msg.get("phone") or "").replace(" ", "")
            texto    = msg.get("text") or msg.get("body") or ""
            nombre   = msg.get("name") or msg.get("contact_name") or telefono

        # Estructura 2: evento de conversación
        elif "add" in payload and isinstance(payload["add"], list):
            for item in payload["add"]:
                if item.get("type") == "inbound_call" or "phone" in item:
                    telefono = item.get("phone", "")
                    texto    = item.get("text", item.get("note", ""))
                    nombre   = item.get("name", telefono)
                    break

        # Estructura 3: Evolution API re-enviando a Kommo
        elif "data" in payload:
            data = payload["data"]
            key  = data.get("key", {})
            telefono = key.get("remoteJid", "").replace("@s.whatsapp.net", "").replace("@g.us", "")
            msg_data = data.get("message", {})
            texto    = (msg_data.get("conversation") or
                        msg_data.get("extendedTextMessage", {}).get("text") or "")
            pushname = data.get("pushName", "")
            nombre   = pushname or telefono

        if not telefono or not texto:
            logger.warning(f"[KOMMO] Webhook recibido pero sin teléfono/texto extraíble: {list(payload.keys())}")
            return {"ok": True, "procesado": False, "motivo": "sin datos extraíbles"}

        # Normalizar teléfono
        if not telefono.startswith("+"):
            telefono = f"+{telefono}"

        return self._guardar_mensaje_entrante(negocio, telefono, texto, nombre)

    def _guardar_mensaje_entrante(self, negocio: Negocio, telefono: str, texto: str, nombre: str) -> dict:
        """Guarda el mensaje entrante en la BD y crea/actualiza la conversación."""
        # Buscar o crear cliente
        cliente = self.db.query(Cliente).filter(
            Cliente.negocio_id == negocio.id,
            Cliente.telefono == telefono
        ).first()
        if not cliente:
            cliente = Cliente(negocio_id=negocio.id, nombre=nombre or telefono, telefono=telefono)
            self.db.add(cliente)
            self.db.flush()

        # Buscar o crear conversación
        conv = self.db.query(Conversacion).filter(
            Conversacion.negocio_id == negocio.id,
            Conversacion.telefono == telefono,
        ).first()
        if not conv:
            conv = Conversacion(
                negocio_id=negocio.id,
                cliente_id=cliente.id,
                telefono=telefono,
                nombre_contacto=nombre or telefono,
                no_leidos=0,
                manejada_por_Carlos=False,
            )
            self.db.add(conv)
            self.db.flush()
        else:
            conv.no_leidos = (conv.no_leidos or 0) + 1
            if nombre and nombre != telefono:
                conv.nombre_contacto = nombre

        # Guardar mensaje
        msg = Mensaje(
            conversacion_id=conv.id,
            contenido=texto,
            enviado_por="cliente",
            leido=False,
        )
        self.db.add(msg)
        conv.ultimo_mensaje    = texto
        conv.ultimo_mensaje_en = datetime.utcnow()
        self.db.commit()

        logger.info(f"[KOMMO] Mensaje guardado — tel={telefono} conv_id={conv.id}")
        return {"ok": True, "procesado": True, "conversacion_id": conv.id}

    async def enviar_por_negocio_id(self, negocio_id: int, telefono: str, texto: str) -> dict:
        return await self.enviar_mensaje(negocio_id, telefono, texto)
