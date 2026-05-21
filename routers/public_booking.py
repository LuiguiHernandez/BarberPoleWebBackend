"""
Router público de reservas — sin autenticación.
Usado por el widget embebible en WordPress/cualquier web.
Base URL: /api/public
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import Optional, List
from datetime import date, datetime, timedelta, time
from pydantic import BaseModel, EmailStr
from core.database import get_db
from models.all_models import (
    Negocio, Servicio, Barbero, Horario, Cita, Cliente,
    DiaSemana, EstadoCita
)

router = APIRouter()

# ── CORS headers en cada respuesta pública ────────────────────────────
from fastapi.responses import JSONResponse
from fastapi import Response

def public_headers(response: Response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response

# ── Helpers ──────────────────────────────────────────────────────────
DIA_MAP = {
    0: DiaSemana.lunes, 1: DiaSemana.martes, 2: DiaSemana.miercoles,
    3: DiaSemana.jueves, 4: DiaSemana.viernes, 5: DiaSemana.sabado,
    6: DiaSemana.domingo,
}

def get_negocio_by_slug(slug: str, db: Session) -> Negocio:
    negocio = db.query(Negocio).filter(Negocio.slug == slug).first()
    if not negocio:
        raise HTTPException(status_code=404, detail=f"Negocio '{slug}' no encontrado")
    return negocio

def fmt_precio(precio: float) -> str:
    return f"${int(precio):,}".replace(",", ".")

# ─────────────────────────────────────────────────────────────────────
# GET /api/public/{slug}/info
# Info básica del negocio para el header del widget
# ─────────────────────────────────────────────────────────────────────
@router.get("/{slug}/info")
def info_negocio(slug: str, db: Session = Depends(get_db)):
    n = get_negocio_by_slug(slug, db)
    return {
        "nombre": n.nombre,
        "slug": n.slug,
        "telefono": n.telefono,
        "direccion": n.direccion,
        "descripcion": n.descripcion,
        "logo_url": n.logo_url if hasattr(n, 'logo_url') else None,
        "color_marca": "#00A86B",
    }

# ─────────────────────────────────────────────────────────────────────
# GET /api/public/{slug}/categorias
# Lista de categorías con conteo de servicios
# ─────────────────────────────────────────────────────────────────────
@router.get("/{slug}/categorias")
def listar_categorias(slug: str, db: Session = Depends(get_db)):
    n = get_negocio_by_slug(slug, db)
    from models.all_models import Categoria
    from sqlalchemy import func as sqlfunc

    # Intentar usar tabla categorias normalizada
    cats = db.query(Categoria).filter(
        Categoria.negocio_id == n.id,
        Categoria.activa == True
    ).order_by(Categoria.orden, Categoria.nombre).all()

    if cats:
        result = []
        for c in cats:
            total = db.query(sqlfunc.count(Servicio.id)).filter(
                Servicio.categoria_id == c.id,
                Servicio.activo == True
            ).scalar() or 0
            precio_desde = db.query(sqlfunc.min(Servicio.precio)).filter(
                Servicio.categoria_id == c.id,
                Servicio.activo == True
            ).scalar()
            result.append({
                "id": c.id,
                "nombre": c.nombre,
                "descripcion": c.descripcion,
                "imagen_url": c.imagen_url,
                "orden": c.orden,
                "total_servicios": total,
                "precio_desde": precio_desde,
                "precio_desde_fmt": fmt_precio(precio_desde) if precio_desde else None,
            })
        return result

    # Fallback: agrupar por campo texto si no hay categorías en tabla
    servicios = db.query(Servicio).filter(
        Servicio.negocio_id == n.id,
        Servicio.activo == True
    ).all()
    cats_dict: dict = {}
    for s in servicios:
        cat = s.categoria or "General"
        if cat not in cats_dict:
            cats_dict[cat] = {"nombre": cat, "total": 0, "precio_desde": None}
        cats_dict[cat]["total"] += 1
        if cats_dict[cat]["precio_desde"] is None or s.precio < cats_dict[cat]["precio_desde"]:
            cats_dict[cat]["precio_desde"] = s.precio

    return [
        {"id": i, "nombre": v["nombre"], "descripcion": None, "imagen_url": None,
         "orden": i, "total_servicios": v["total"],
         "precio_desde": v["precio_desde"],
         "precio_desde_fmt": fmt_precio(v["precio_desde"]) if v["precio_desde"] else None}
        for i, (_, v) in enumerate(cats_dict.items())
    ]

# ─────────────────────────────────────────────────────────────────────
# GET /api/public/{slug}/servicios?categoria=X
# Lista de servicios con precio y duración
# ─────────────────────────────────────────────────────────────────────
@router.get("/{slug}/servicios")
def listar_servicios(
    slug: str,
    categoria: Optional[str] = None,
    db: Session = Depends(get_db)
):
    n = get_negocio_by_slug(slug, db)
    q = db.query(Servicio).filter(
        Servicio.negocio_id == n.id,
        Servicio.activo == True
    )
    if categoria and categoria.lower() != "todos":
        q = q.filter(func.lower(Servicio.categoria) == categoria.lower()) if hasattr(Servicio, 'categoria') else q

    servicios = q.order_by(Servicio.nombre).all()
    return [
        {
            "id": s.id,
            "nombre": s.nombre,
            "descripcion": s.descripcion,
            "precio": s.precio,
            "precio_fmt": fmt_precio(s.precio),
            "duracion_minutos": s.duracion_minutos,
            "duracion_fmt": f"{s.duracion_minutos // 60}h {s.duracion_minutos % 60}min".replace("0min", "").strip(),
            "categoria": getattr(s, 'categoria', 'General') or "General",
            "imagen_url": None,
        }
        for s in servicios
    ]

# ─────────────────────────────────────────────────────────────────────
# GET /api/public/{slug}/profesionales?servicio_id=X
# Lista de profesionales que pueden hacer el servicio
# ─────────────────────────────────────────────────────────────────────
@router.get("/{slug}/profesionales")
def listar_profesionales(
    slug: str,
    servicio_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    n = get_negocio_by_slug(slug, db)
    barberos = db.query(Barbero).filter(
        Barbero.negocio_id == n.id,
        Barbero.activo == True
    ).all()
    return [
        {
            "id": b.id,
            "nombre": b.nombre,
            "especialidad": b.especialidad if hasattr(b, 'especialidad') else None,
            "foto_url": None,
        }
        for b in barberos
    ]

# ─────────────────────────────────────────────────────────────────────
# GET /api/public/{slug}/slots?servicio_id=X&fecha=2026-05-22&barbero_id=Y
# Slots disponibles en una fecha (lógica pesada)
# ─────────────────────────────────────────────────────────────────────
@router.get("/{slug}/slots")
def slots_disponibles(
    slug: str,
    servicio_id: int,
    fecha: str,
    barbero_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    n = get_negocio_by_slug(slug, db)
    try:
        fecha_dt = datetime.strptime(fecha, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido. Use YYYY-MM-DD")

    if fecha_dt < date.today():
        raise HTTPException(status_code=400, detail="No se pueden consultar fechas pasadas")

    # Obtener servicio y duración
    servicio = db.query(Servicio).filter(
        Servicio.id == servicio_id,
        Servicio.negocio_id == n.id
    ).first()
    if not servicio:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    duracion = servicio.duracion_minutos

    # Verificar horario del negocio ese día
    dia_semana = DIA_MAP[fecha_dt.weekday()]
    horario = db.query(Horario).filter(
        Horario.negocio_id == n.id,
        Horario.dia == dia_semana,
        Horario.barbero_id == None
    ).first()

    if not horario or not horario.abierto:
        return {"fecha": fecha, "disponible": False, "motivo": "El negocio no atiende este día", "slots": []}

    inicio_str = horario.hora_inicio   # "09:00"
    fin_str = horario.hora_fin         # "18:00"
    h_i, m_i = map(int, inicio_str.split(":"))
    h_f, m_f = map(int, fin_str.split(":"))
    inicio_mins = h_i * 60 + m_i
    fin_mins = h_f * 60 + m_f

    # Obtener barberos disponibles ese día
    barberos_query = db.query(Barbero).filter(
        Barbero.negocio_id == n.id,
        Barbero.activo == True
    )
    if barbero_id:
        barberos_query = barberos_query.filter(Barbero.id == barbero_id)
    barberos = barberos_query.all()

    if not barberos:
        return {"fecha": fecha, "disponible": False, "motivo": "No hay profesionales disponibles", "slots": []}

    # Citas existentes ese día
    citas_dia = db.query(Cita).filter(
        Cita.negocio_id == n.id,
        func.date(Cita.fecha_hora) == fecha_dt,
        Cita.estado.in_([EstadoCita.pendiente, EstadoCita.confirmada])
    ).all()

    # Generar slots cada 30 min y verificar disponibilidad
    slots = []
    cur = inicio_mins
    now_mins = None
    if fecha_dt == date.today():
        now = datetime.now()
        now_mins = now.hour * 60 + now.minute + 30  # buffer 30min

    while cur + duracion <= fin_mins:
        slot_hora = f"{cur//60:02d}:{cur%60:02d}"
        slot_fin = cur + duracion

        # Si es hoy, no mostrar slots pasados
        if now_mins and cur < now_mins:
            cur += 30
            continue

        # Verificar si hay al menos un barbero libre en este slot
        libre = False
        for b in barberos:
            ocupado = False
            for c in citas_dia:
                if c.barbero_id != b.id:
                    continue
                c_inicio = c.fecha_hora.hour * 60 + c.fecha_hora.minute
                c_fin = c_inicio + c.duracion_minutos
                # Solapamiento
                if not (slot_fin <= c_inicio or cur >= c_fin):
                    ocupado = True
                    break
            if not ocupado:
                libre = True
                break

        slots.append({
            "hora": slot_hora,
            "hora_fin": f"{slot_fin//60:02d}:{slot_fin%60:02d}",
            "disponible": libre,
            "barbero_libre_id": next((b.id for b in barberos if not any(
                c.barbero_id == b.id and not (
                    (c.fecha_hora.hour*60+c.fecha_hora.minute + c.duracion_minutos) <= cur or
                    c.fecha_hora.hour*60+c.fecha_hora.minute >= slot_fin
                ) for c in citas_dia
            )), None) if libre else None,
        })
        cur += 30

    slots_disponibles_count = sum(1 for s in slots if s["disponible"])
    return {
        "fecha": fecha,
        "dia_nombre": dia_semana.value.capitalize(),
        "disponible": slots_disponibles_count > 0,
        "total_slots": len(slots),
        "slots_disponibles": slots_disponibles_count,
        "horario": f"{inicio_str} - {fin_str}",
        "slots": slots,
    }

# ─────────────────────────────────────────────────────────────────────
# GET /api/public/{slug}/disponibilidad-mes?year=2026&month=5&servicio_id=X
# Qué días del mes tienen disponibilidad (para colorear el calendario)
# ─────────────────────────────────────────────────────────────────────
@router.get("/{slug}/disponibilidad-mes")
def disponibilidad_mes(
    slug: str,
    year: int,
    month: int,
    servicio_id: int,
    db: Session = Depends(get_db)
):
    n = get_negocio_by_slug(slug, db)
    import calendar
    num_dias = calendar.monthrange(year, month)[1]
    hoy = date.today()
    resultado = []
    for dia in range(1, num_dias + 1):
        fecha = date(year, month, dia)
        if fecha < hoy:
            resultado.append({"fecha": str(fecha), "disponible": False, "pasado": True})
            continue
        dia_semana = DIA_MAP[fecha.weekday()]
        horario = db.query(Horario).filter(
            Horario.negocio_id == n.id,
            Horario.dia == dia_semana,
            Horario.barbero_id == None
        ).first()
        abierto = horario and horario.abierto
        resultado.append({"fecha": str(fecha), "disponible": abierto, "pasado": False})
    return resultado

# ─────────────────────────────────────────────────────────────────────
# POST /api/public/{slug}/booking
# Crear reserva pública — sin autenticación
# ─────────────────────────────────────────────────────────────────────
class BookingRequest(BaseModel):
    servicio_id: int
    barbero_id: Optional[int] = None
    fecha: str           # "2026-05-22"
    hora: str            # "10:30"
    cliente_nombre: str
    cliente_telefono: str
    cliente_email: Optional[str] = None
    notas: Optional[str] = None
    fuente: Optional[str] = "web"  # "web", "wordpress", "instagram"

@router.post("/{slug}/booking")
def crear_booking(slug: str, data: BookingRequest, db: Session = Depends(get_db)):
    n = get_negocio_by_slug(slug, db)

    # Validar servicio
    servicio = db.query(Servicio).filter(
        Servicio.id == data.servicio_id,
        Servicio.negocio_id == n.id,
        Servicio.activo == True
    ).first()
    if not servicio:
        raise HTTPException(status_code=404, detail="Servicio no encontrado o no disponible")

    # Parsear fecha y hora
    try:
        fecha_hora = datetime.strptime(f"{data.fecha} {data.hora}", "%Y-%m-%d %H:%M")
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha/hora inválido")

    if fecha_hora < datetime.now():
        raise HTTPException(status_code=400, detail="No se pueden crear citas en el pasado")

    # Validar horario
    dia_semana = DIA_MAP[fecha_hora.weekday()]
    horario = db.query(Horario).filter(
        Horario.negocio_id == n.id,
        Horario.dia == dia_semana,
        Horario.barbero_id == None
    ).first()
    if not horario or not horario.abierto:
        raise HTTPException(status_code=400, detail=f"El negocio no atiende los {dia_semana.value}s")

    hora_str = data.hora
    if hora_str < horario.hora_inicio or hora_str >= horario.hora_fin:
        raise HTTPException(
            status_code=400,
            detail=f"El horario de atención es de {horario.hora_inicio} a {horario.hora_fin}"
        )

    # Asignar barbero — si no viene, buscar el más libre
    barbero_id = data.barbero_id
    if not barbero_id:
        barberos = db.query(Barbero).filter(
            Barbero.negocio_id == n.id, Barbero.activo == True
        ).all()
        slot_inicio = fecha_hora.hour * 60 + fecha_hora.minute
        slot_fin = slot_inicio + servicio.duracion_minutos
        for b in barberos:
            citas_conflicto = db.query(Cita).filter(
                Cita.negocio_id == n.id,
                Cita.barbero_id == b.id,
                func.date(Cita.fecha_hora) == fecha_hora.date(),
                Cita.estado.in_([EstadoCita.pendiente, EstadoCita.confirmada])
            ).all()
            conflicto = False
            for c in citas_conflicto:
                ci = c.fecha_hora.hour * 60 + c.fecha_hora.minute
                cf = ci + c.duracion_minutos
                if not (slot_fin <= ci or slot_inicio >= cf):
                    conflicto = True
                    break
            if not conflicto:
                barbero_id = b.id
                break
        if not barbero_id:
            raise HTTPException(status_code=409, detail="No hay profesionales disponibles en ese horario")

    # Verificar disponibilidad del barbero seleccionado
    slot_inicio = fecha_hora.hour * 60 + fecha_hora.minute
    slot_fin = slot_inicio + servicio.duracion_minutos
    citas_conflicto = db.query(Cita).filter(
        Cita.negocio_id == n.id,
        Cita.barbero_id == barbero_id,
        func.date(Cita.fecha_hora) == fecha_hora.date(),
        Cita.estado.in_([EstadoCita.pendiente, EstadoCita.confirmada])
    ).all()
    for c in citas_conflicto:
        ci = c.fecha_hora.hour * 60 + c.fecha_hora.minute
        cf = ci + c.duracion_minutos
        if not (slot_fin <= ci or slot_inicio >= cf):
            raise HTTPException(status_code=409, detail="Ese horario ya no está disponible. Por favor selecciona otro.")

    # Buscar o crear cliente
    cliente = db.query(Cliente).filter(
        Cliente.negocio_id == n.id,
        Cliente.telefono == data.cliente_telefono
    ).first()
    if not cliente:
        cliente = Cliente(
            negocio_id=n.id,
            nombre=data.cliente_nombre,
            telefono=data.cliente_telefono,
            email=data.cliente_email,
        )
        db.add(cliente)
        db.flush()
    else:
        if data.cliente_nombre and not cliente.nombre:
            cliente.nombre = data.cliente_nombre

    # Crear cita
    nueva_cita = Cita(
        negocio_id=n.id,
        cliente_id=cliente.id,
        barbero_id=barbero_id,
        servicio_id=data.servicio_id,
        fecha_hora=fecha_hora,
        duracion_minutos=servicio.duracion_minutos,
        precio=servicio.precio,
        estado=EstadoCita.pendiente,
        fuente=data.fuente or "web",
        creada_manualmente=False,
        notas=data.notas,
    )
    db.add(nueva_cita)
    db.commit()
    db.refresh(nueva_cita)

    # Disparar Google Calendar si está conectado
    try:
        from services.gcal_service import GCalService
        gcal = GCalService(db)
        gcal.crear_evento(nueva_cita.id)
    except Exception:
        pass  # GCal es opcional — no bloquear la reserva

    barbero = db.query(Barbero).filter(Barbero.id == barbero_id).first()

    return {
        "ok": True,
        "cita_id": nueva_cita.id,
        "mensaje": f"¡Reserva confirmada! Te esperamos el {data.fecha} a las {data.hora}",
        "detalle": {
            "servicio": servicio.nombre,
            "profesional": barbero.nombre if barbero else "Por asignar",
            "fecha": data.fecha,
            "hora": data.hora,
            "duracion": f"{servicio.duracion_minutos} min",
            "precio": fmt_precio(servicio.precio),
            "cliente": data.cliente_nombre,
            "telefono": data.cliente_telefono,
        }
    }

# ─────────────────────────────────────────────────────────────────────
# GET /api/public/{slug}/reserva/{cita_id}
# Consultar estado de una reserva (para confirmación post-booking)
# ─────────────────────────────────────────────────────────────────────
@router.get("/{slug}/reserva/{cita_id}")
def estado_reserva(slug: str, cita_id: int, db: Session = Depends(get_db)):
    n = get_negocio_by_slug(slug, db)
    cita = db.query(Cita).filter(
        Cita.id == cita_id,
        Cita.negocio_id == n.id
    ).first()
    if not cita:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    cliente = db.query(Cliente).filter(Cliente.id == cita.cliente_id).first()
    servicio = db.query(Servicio).filter(Servicio.id == cita.servicio_id).first()
    barbero = db.query(Barbero).filter(Barbero.id == cita.barbero_id).first()
    return {
        "id": cita.id,
        "estado": cita.estado.value,
        "fecha": cita.fecha_hora.strftime("%Y-%m-%d"),
        "hora": cita.fecha_hora.strftime("%H:%M"),
        "servicio": servicio.nombre if servicio else "—",
        "profesional": barbero.nombre if barbero else "—",
        "precio": fmt_precio(cita.precio),
        "cliente": cliente.nombre if cliente else "—",
    }
