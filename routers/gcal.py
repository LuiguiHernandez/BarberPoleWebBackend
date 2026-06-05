"""
GestorPro — Google Calendar Router
Endpoints para conectar/desconectar GCal y consultar disponibilidad.
"""
import logging
from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from core.config import settings
from core.database import get_db
from core.security import get_current_user, require_plan_activo
from services.gcal_service import GoogleCalendarService
from repositories.negocio_repository import NegocioRepository

logger = logging.getLogger(__name__)
router = APIRouter()


def get_gcal_service(db: Session = Depends(get_db)) -> GoogleCalendarService:
    return GoogleCalendarService(db)


# ─── ESTADO DE CONEXIÓN ────────────────────────────────────────────────────────

@router.get("/estado")
def estado_gcal(
    service: GoogleCalendarService = Depends(get_gcal_service),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retorna si el negocio tiene Google Calendar conectado."""
    negocio_repo = NegocioRepository(db)
    negocio = negocio_repo.get_by_usuario_id(current_user.id)
    if not negocio:
        return {"conectado": False, "error": "Negocio no encontrado"}
    return service.estado_conexion(negocio.id)


# ─── INICIAR OAUTH ─────────────────────────────────────────────────────────────

@router.get("/conectar")
def conectar_gcal(
    service: GoogleCalendarService = Depends(get_gcal_service),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Redirige al dueño del negocio al flujo de autorización de Google.
    El frontend llama este endpoint y redirige al usuario.
    """
    if not settings.GCAL_CLIENT_ID or not settings.GCAL_CLIENT_SECRET:
        return {
            "error": "Google Calendar no está configurado en el servidor. "
                     "Agrega GCAL_CLIENT_ID y GCAL_CLIENT_SECRET al .env"
        }

    negocio_repo = NegocioRepository(db)
    negocio = negocio_repo.get_by_usuario_id(current_user.id)
    if not negocio:
        return {"error": "Negocio no encontrado"}

    auth_url = service.generar_url_auth(negocio.id)
    return {"auth_url": auth_url}


# ─── CALLBACK DE GOOGLE ────────────────────────────────────────────────────────

@router.get("/callback")
def callback_gcal(
    code: str = Query(...),
    state: str = Query(...),  # negocio_id
    service: GoogleCalendarService = Depends(get_gcal_service),
):
    """
    Google redirige aquí después de que el usuario autoriza.
    Guarda los tokens y redirige al dashboard con el resultado.
    """
    try:
        negocio_id = int(state)
        ok = service.guardar_tokens_desde_callback(code, negocio_id)
        if ok:
            return RedirectResponse(
                url=f"http://167.172.145.102/dashboard/negocio?gcal=connected"
            )
        else:
            return RedirectResponse(
                url=f"http://167.172.145.102/dashboard/negocio?gcal=error"
            )
    except Exception as e:
        logger.error(f"[GCAL] Error en callback: {e}")
        return RedirectResponse(
            url=f"http://167.172.145.102/dashboard/negocio?gcal=error"
        )


# ─── DESCONECTAR ───────────────────────────────────────────────────────────────

@router.delete("/desconectar")
def desconectar_gcal(
    service: GoogleCalendarService = Depends(get_gcal_service),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Desconecta Google Calendar del negocio."""
    negocio_repo = NegocioRepository(db)
    negocio = negocio_repo.get_by_usuario_id(current_user.id)
    if not negocio:
        return {"error": "Negocio no encontrado"}
    ok = service.desconectar(negocio.id)
    return {"desconectado": ok}


@router.post("/desconectar")
def desconectar_gcal_post(
    service: GoogleCalendarService = Depends(get_gcal_service),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Desconecta Google Calendar (versión POST para compatibilidad)."""
    negocio_repo = NegocioRepository(db)
    negocio = negocio_repo.get_by_usuario_id(current_user.id)
    if not negocio:
        return {"error": "Negocio no encontrado"}
    ok = service.desconectar(negocio.id)
    return {"ok": ok, "desconectado": ok}


# ─── DISPONIBILIDAD ────────────────────────────────────────────────────────────

@router.get("/disponibilidad")
def disponibilidad(
    fecha: str = Query(..., description="YYYY-MM-DD"),
    service: GoogleCalendarService = Depends(get_gcal_service),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retorna los slots ocupados en Google Calendar para una fecha.
    Usado por el widget de booking embebible en WordPress.
    """
    negocio_repo = NegocioRepository(db)
    negocio = negocio_repo.get_by_usuario_id(current_user.id)
    if not negocio:
        return {"slots_ocupados": [], "error": "Negocio no encontrado"}

    slots = service.obtener_slots_ocupados(negocio.id, fecha)
    return {"fecha": fecha, "slots_ocupados": slots}


# ─── DISPONIBILIDAD PÚBLICA (para el widget de WordPress) ─────────────────────

@router.get("/disponibilidad/{negocio_slug}")
def disponibilidad_publica(
    negocio_slug: str,
    fecha: str = Query(..., description="YYYY-MM-DD"),
    servicio_id: int = Query(None),
    db: Session = Depends(get_db),
):
    """
    Endpoint PÚBLICO para el widget embebible de WordPress.
    No requiere autenticación — usa el slug del negocio.
    Retorna slots disponibles para mostrarle al cliente final.
    """
    from models.all_models import Negocio, Horario, Cita, Servicio
    from datetime import datetime, timedelta

    negocio = db.query(Negocio).filter(Negocio.slug == negocio_slug).first()
    if not negocio:
        return {"error": "Negocio no encontrado", "slots": []}

    # Duración del servicio
    duracion = 60
    if servicio_id:
        servicio = db.query(Servicio).filter(
            Servicio.id == servicio_id,
            Servicio.negocio_id == negocio.id,
            Servicio.activo == True
        ).first()
        if servicio:
            duracion = servicio.duracion_minutos

    # Horario del día
    try:
        fecha_dt = datetime.strptime(fecha, "%Y-%m-%d")
    except ValueError:
        return {"error": "Formato de fecha inválido. Usa YYYY-MM-DD", "slots": []}

    dias_map = {0: "lunes", 1: "martes", 2: "miercoles", 3: "jueves",
                4: "viernes", 5: "sabado", 6: "domingo"}
    dia_nombre = dias_map[fecha_dt.weekday()]

    horario = db.query(Horario).filter(
        Horario.negocio_id == negocio.id,
        Horario.dia == dia_nombre,
        Horario.barbero_id == None,
    ).first()

    if not horario or not horario.abierto:
        return {"fecha": fecha, "slots": [], "mensaje": "El negocio no atiende este día"}

    # Generar todos los slots del día
    inicio_h, inicio_m = map(int, horario.hora_inicio.split(":"))
    fin_h, fin_m = map(int, horario.hora_fin.split(":"))
    inicio_dt = fecha_dt.replace(hour=inicio_h, minute=inicio_m)
    fin_dt = fecha_dt.replace(hour=fin_h, minute=fin_m)

    todos_slots = []
    cursor = inicio_dt
    while cursor + timedelta(minutes=duracion) <= fin_dt:
        todos_slots.append(cursor)
        cursor += timedelta(minutes=30)  # intervalo de 30 min

    # Citas ya reservadas en BD
    citas_dia = db.query(Cita).filter(
        Cita.negocio_id == negocio.id,
        Cita.fecha_hora >= fecha_dt,
        Cita.fecha_hora < fecha_dt + timedelta(days=1),
        Cita.estado.in_(["pendiente", "confirmada"]),
    ).all()

    ocupados_bd = [(c.fecha_hora, c.fecha_hora + timedelta(minutes=c.duracion_minutos or 30))
                   for c in citas_dia]

    # Slots ocupados en GCal
    gcal_service = GoogleCalendarService(db)
    slots_gcal = gcal_service.obtener_slots_ocupados(negocio.id, fecha)
    ocupados_gcal = []
    for s in slots_gcal:
        try:
            s_start = datetime.fromisoformat(s["start"].replace("Z", "+00:00")).replace(tzinfo=None)
            s_end = datetime.fromisoformat(s["end"].replace("Z", "+00:00")).replace(tzinfo=None)
            ocupados_gcal.append((s_start, s_end))
        except Exception:
            pass

    todos_ocupados = ocupados_bd + ocupados_gcal

    # Marcar disponibilidad
    slots_result = []
    for slot_inicio in todos_slots:
        slot_fin = slot_inicio + timedelta(minutes=duracion)
        ocupado = any(
            slot_inicio < o_fin and slot_fin > o_inicio
            for o_inicio, o_fin in todos_ocupados
        )
        slots_result.append({
            "time": slot_inicio.strftime("%H:%M"),
            "time_end": slot_fin.strftime("%H:%M"),
            "available": not ocupado,
        })

    return {
        "fecha": fecha,
        "negocio": negocio.nombre,
        "duracion_minutos": duracion,
        "slots": slots_result,
    }
