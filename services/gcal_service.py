"""
GestorPro — Google Calendar Service
Maneja OAuth2 y operaciones de calendario por negocio.
"""
import logging
import urllib.parse
from datetime import datetime, timedelta
from typing import Optional, List
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from sqlalchemy.orm import Session

from core.config import settings
from models.all_models import Negocio, Cita

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar"]


class GoogleCalendarService:

    def __init__(self, db: Session):
        self.db = db

    # ─── OAuth2 ────────────────────────────────────────────────────────────────

    def generar_url_auth(self, negocio_id: int) -> str:
        """Genera la URL de autorización de Google para el dueño del negocio."""
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.GCAL_CLIENT_ID,
                    "client_secret": settings.GCAL_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [settings.GCAL_REDIRECT_URI],
                }
            },
            scopes=SCOPES,
        )
        flow.redirect_uri = settings.GCAL_REDIRECT_URI

        auth_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
            state=str(negocio_id),
        )
        return auth_url

    def guardar_tokens_desde_callback(self, code: str, negocio_id: int) -> bool:
        """Intercambia el código de autorización por tokens y los guarda en BD."""
        try:
            import urllib.request
            import json as json_lib

            # Intercambio manual del code por tokens (evita problemas con PKCE)
            token_url = "https://oauth2.googleapis.com/token"
            data = urllib.parse.urlencode({
                "code": code,
                "client_id": settings.GCAL_CLIENT_ID,
                "client_secret": settings.GCAL_CLIENT_SECRET,
                "redirect_uri": settings.GCAL_REDIRECT_URI,
                "grant_type": "authorization_code",
            }).encode()

            req = urllib.request.Request(token_url, data=data, method="POST")
            req.add_header("Content-Type", "application/x-www-form-urlencoded")

            with urllib.request.urlopen(req) as resp:
                tokens = json_lib.loads(resp.read())

            negocio = self.db.query(Negocio).filter(Negocio.id == negocio_id).first()
            if not negocio:
                return False

            negocio.gcal_access_token  = tokens.get("access_token")
            negocio.gcal_refresh_token = tokens.get("refresh_token")
            negocio.gcal_connected     = True
            self.db.commit()
            logger.info(f"[GCAL] Tokens guardados para negocio_id={negocio_id}")
            return True

        except Exception as e:
            logger.error(f"[GCAL] Error guardando tokens: {e}")
            return False

    def desconectar(self, negocio_id: int) -> bool:
        """Desconecta Google Calendar del negocio."""
        negocio = self.db.query(Negocio).filter(Negocio.id == negocio_id).first()
        if not negocio:
            return False
        negocio.gcal_access_token = None
        negocio.gcal_refresh_token = None
        negocio.gcal_connected = False
        self.db.commit()
        return True

    # ─── Cliente autenticado ────────────────────────────────────────────────────

    def _get_service(self, negocio: Negocio):
        """Devuelve el cliente de Google Calendar autenticado para un negocio."""
        if not negocio.gcal_access_token:
            raise ValueError("Negocio no tiene Google Calendar conectado")

        creds = Credentials(
            token=negocio.gcal_access_token,
            refresh_token=negocio.gcal_refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GCAL_CLIENT_ID,
            client_secret=settings.GCAL_CLIENT_SECRET,
            scopes=SCOPES,
        )

        # Auto-refresh si el token venció
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            negocio.gcal_access_token = creds.token
            self.db.commit()
            logger.info(f"[GCAL] Token refrescado para negocio_id={negocio.id}")

        return build("calendar", "v3", credentials=creds, cache_discovery=False)

    # ─── Operaciones de calendario ─────────────────────────────────────────────

    def crear_evento(self, negocio_id: int, cita: Cita) -> Optional[str]:
        """
        Crea un evento en Google Calendar para una cita.
        Retorna el gcal_event_id o None si falla.
        """
        negocio = self.db.query(Negocio).filter(Negocio.id == negocio_id).first()
        if not negocio or not negocio.gcal_connected:
            logger.info(f"[GCAL] Negocio {negocio_id} no tiene GCal conectado — skip")
            return None

        try:
            service = self._get_service(negocio)
            cal_id = negocio.gcal_calendar_id or "primary"

            inicio = cita.fecha_hora
            fin = inicio + timedelta(minutes=cita.duracion_minutos or 30)

            # Construir descripción del evento
            partes = [f"Servicio: {cita.servicio.nombre}" if cita.servicio else ""]
            if cita.cliente:
                partes.append(f"Cliente: {cita.cliente.nombre}")
                if cita.cliente.telefono:
                    partes.append(f"Teléfono: {cita.cliente.telefono}")
            if cita.barbero:
                partes.append(f"Profesional: {cita.barbero.nombre}")
            if cita.notas:
                partes.append(f"Notas: {cita.notas}")
            partes.append(f"Fuente: {cita.fuente or 'admin'}")
            partes.append("Creado por GestorPro")

            nombre_cliente = cita.cliente.nombre if cita.cliente else "Cliente"
            nombre_servicio = cita.servicio.nombre if cita.servicio else "Cita"

            evento = {
                "summary": f"{nombre_cliente} — {nombre_servicio}",
                "description": "\n".join(filter(None, partes)),
                "start": {
                    "dateTime": inicio.isoformat(),
                    "timeZone": "America/Bogota",
                },
                "end": {
                    "dateTime": fin.isoformat(),
                    "timeZone": "America/Bogota",
                },
                "reminders": {
                    "useDefault": False,
                    "overrides": [
                        {"method": "email", "minutes": 1440},  # 24h antes
                        {"method": "popup", "minutes": 60},    # 1h antes
                    ],
                },
                "colorId": "2",  # verde
            }

            # Agregar asistente si tiene email
            if cita.cliente and cita.cliente.email:
                evento["attendees"] = [{"email": cita.cliente.email}]

            result = service.events().insert(
                calendarId=cal_id,
                body=evento,
                sendUpdates="all",
            ).execute()

            event_id = result.get("id")
            logger.info(f"[GCAL] Evento creado: {event_id} para cita_id={cita.id}")
            return event_id

        except HttpError as e:
            logger.error(f"[GCAL] HttpError creando evento: {e}")
            return None
        except Exception as e:
            logger.error(f"[GCAL] Error creando evento: {e}")
            return None

    def eliminar_evento(self, negocio_id: int, gcal_event_id: str) -> bool:
        """Elimina un evento de Google Calendar (para cancelaciones)."""
        negocio = self.db.query(Negocio).filter(Negocio.id == negocio_id).first()
        if not negocio or not negocio.gcal_connected or not gcal_event_id:
            return False

        try:
            service = self._get_service(negocio)
            cal_id = negocio.gcal_calendar_id or "primary"
            service.events().delete(
                calendarId=cal_id,
                eventId=gcal_event_id,
                sendUpdates="all",
            ).execute()
            logger.info(f"[GCAL] Evento {gcal_event_id} eliminado")
            return True
        except Exception as e:
            logger.warning(f"[GCAL] No se pudo eliminar evento {gcal_event_id}: {e}")
            return False

    def obtener_slots_ocupados(
        self, negocio_id: int, fecha: str, barbero_nombre: Optional[str] = None
    ) -> List[dict]:
        """
        Retorna los slots ocupados en Google Calendar para una fecha.
        fecha: 'YYYY-MM-DD'
        """
        negocio = self.db.query(Negocio).filter(Negocio.id == negocio_id).first()
        if not negocio or not negocio.gcal_connected:
            return []

        try:
            service = self._get_service(negocio)
            cal_id = negocio.gcal_calendar_id or "primary"

            time_min = f"{fecha}T00:00:00-05:00"
            time_max = f"{fecha}T23:59:59-05:00"

            events = service.events().list(
                calendarId=cal_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy="startTime",
            ).execute()

            slots = []
            for e in events.get("items", []):
                start = e.get("start", {}).get("dateTime", "")
                end = e.get("end", {}).get("dateTime", "")
                if start and end:
                    slots.append({"start": start, "end": end, "summary": e.get("summary", "")})

            return slots

        except Exception as e:
            logger.error(f"[GCAL] Error obteniendo slots: {e}")
            return []

    def estado_conexion(self, negocio_id: int) -> dict:
        """Retorna el estado de la conexión de Google Calendar del negocio."""
        negocio = self.db.query(Negocio).filter(Negocio.id == negocio_id).first()
        if not negocio:
            return {"conectado": False, "error": "Negocio no encontrado"}

        return {
            "conectado": negocio.gcal_connected or False,
            "calendar_id": negocio.gcal_calendar_id or "primary",
            "tiene_refresh_token": bool(negocio.gcal_refresh_token),
        }
