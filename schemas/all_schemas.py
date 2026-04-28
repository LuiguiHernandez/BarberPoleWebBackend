from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List
from datetime import datetime
from models.all_models import EstadoCita, DiaSemana

# ─── AUTH ─────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario_nombre: str
    negocio_nombre: Optional[str] = None
    negocio_slug: Optional[str] = None

class RegisterRequest(BaseModel):
    nombre: str
    email: str
    password: str
    nombre_negocio: str

# ─── NEGOCIO ──────────────────────────────────────────────────────────────────

class NegocioUpdate(BaseModel):
    nombre: Optional[str] = None
    slug: Optional[str] = None
    telefono: Optional[str] = None
    whatsapp: Optional[str] = None
    direccion: Optional[str] = None
    descripcion: Optional[str] = None
    lealtad_activa: Optional[bool] = None
    lealtad_sellos_requeridos: Optional[int] = None
    lealtad_recompensa: Optional[str] = None
    reservas_activas: Optional[bool] = None
    reservas_anticipacion_max_dias: Optional[int] = None
    reservas_cancelacion_horas: Optional[int] = None
    acepta_efectivo: Optional[bool] = None
    acepta_transferencia: Optional[bool] = None
    acepta_tarjeta: Optional[bool] = None
    notif_nueva_cita: Optional[bool] = None
    notif_recordatorio: Optional[bool] = None
    notif_cancelacion: Optional[bool] = None
    carlos_activa: Optional[bool] = None
    carlos_recordatorios_activos: Optional[bool] = None

class NegocioResponse(BaseModel):
    id: int
    nombre: str
    slug: Optional[str]
    telefono: Optional[str]
    whatsapp: Optional[str]
    direccion: Optional[str]
    descripcion: Optional[str]
    logo_url: Optional[str]
    lealtad_activa: bool
    lealtad_sellos_requeridos: int
    lealtad_recompensa: str
    reservas_activas: bool
    reservas_anticipacion_max_dias: int
    reservas_cancelacion_horas: int
    acepta_efectivo: bool
    acepta_transferencia: bool
    acepta_tarjeta: bool
    notif_nueva_cita: bool
    notif_recordatorio: bool
    notif_cancelacion: bool
    carlos_activa: bool
    carlos_recordatorios_activos: bool

    class Config:
        from_attributes = True

# ─── SERVICIO ─────────────────────────────────────────────────────────────────

class ServicioCreate(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    duracion_minutos: int = 30
    precio: float
    activo: bool = True

class ServicioUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    duracion_minutos: Optional[int] = None
    precio: Optional[float] = None
    activo: Optional[bool] = None

class ServicioResponse(BaseModel):
    id: int
    nombre: str
    descripcion: Optional[str]
    duracion_minutos: int
    precio: float
    activo: bool

    class Config:
        from_attributes = True

# ─── BARBERO ──────────────────────────────────────────────────────────────────

class BarberoCreate(BaseModel):
    nombre: str
    telefono: Optional[str] = None
    email: Optional[str] = None
    activo: bool = True

class BarberoUpdate(BaseModel):
    nombre: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    activo: Optional[bool] = None

class BarberoResponse(BaseModel):
    id: int
    nombre: str
    telefono: Optional[str]
    email: Optional[str]
    foto_url: Optional[str]
    activo: bool

    class Config:
        from_attributes = True

# ─── HORARIO ──────────────────────────────────────────────────────────────────

class HorarioUpdate(BaseModel):
    dia: DiaSemana
    abierto: bool
    hora_inicio: Optional[str] = "09:00"
    hora_fin: Optional[str] = "18:00"
    barbero_id: Optional[int] = None

class HorarioResponse(BaseModel):
    id: int
    dia: DiaSemana
    abierto: bool
    hora_inicio: str
    hora_fin: str
    barbero_id: Optional[int]

    class Config:
        from_attributes = True

# ─── CLIENTE ──────────────────────────────────────────────────────────────────

class ClienteCreate(BaseModel):
    nombre: str
    telefono: Optional[str] = None
    email: Optional[str] = None

class ClienteResponse(BaseModel):
    id: int
    nombre: str
    telefono: Optional[str]
    email: Optional[str]
    sellos: int
    sellos_totales: int
    recompensas_canjeadas: int
    creado_en: datetime

    class Config:
        from_attributes = True

# ─── CITA ─────────────────────────────────────────────────────────────────────

class CitaCreate(BaseModel):
    cliente_id: Optional[int] = None
    barbero_id: Optional[int] = None
    servicio_id: Optional[int] = None
    fecha_hora: datetime
    notas: Optional[str] = None
    cliente_nombre: Optional[str] = None
    cliente_telefono: Optional[str] = None

class CitaUpdate(BaseModel):
    barbero_id: Optional[int] = None
    servicio_id: Optional[int] = None
    fecha_hora: Optional[datetime] = None
    estado: Optional[EstadoCita] = None
    notas: Optional[str] = None

class CitaClienteResponse(BaseModel):
    id: int
    nombre: str
    telefono: Optional[str]

    class Config:
        from_attributes = True

class CitaResponse(BaseModel):
    id: int
    fecha_hora: datetime
    duracion_minutos: int
    precio: float
    estado: EstadoCita
    notas: Optional[str]
    creada_por_Carlos: bool # Coincide con tu modelo (C mayúscula)
    cliente: Optional[CitaClienteResponse]
    barbero: Optional[BarberoResponse]
    servicio: Optional[ServicioResponse]

    class Config:
        from_attributes = True

# ─── DASHBOARD STATS ──────────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    citas_hoy: int
    ingresos_hoy: float
    citas_semana: int
    confirmadas_hoy: int

# ─── INFORMES ─────────────────────────────────────────────────────────────────

class InformesStats(BaseModel):
    total_citas: int
    completadas: int
    ingresos_totales: float
    tasa_completadas: float
    citas_por_estado: dict
    ingresos_por_barbero: List[dict]

# ─── LEALTAD ──────────────────────────────────────────────────────────────────

class DarSelloRequest(BaseModel):
    telefono: str

class LealtadResumen(BaseModel):
    total_clientes: int
    sellos_dados_hoy: int
    recompensas_canjeadas_total: int

# ─── CONVERSACIONES ───────────────────────────────────────────────────────────

class ConversacionResponse(BaseModel):
    id: int
    telefono: str
    nombre_contacto: Optional[str]
    ultimo_mensaje: Optional[str]
    ultimo_mensaje_en: Optional[datetime]
    no_leidos: int
    manejada_por_Carlos: bool # Coincide con tu modelo (C mayúscula)

    class Config:
        from_attributes = True

class MensajeResponse(BaseModel):
    id: int
    contenido: str
    enviado_por: str
    enviado_en: datetime
    leido: bool

    class Config:
        from_attributes = True

class EnviarMensajeRequest(BaseModel):
    contenido: str

# ─── Carlos IA ──────────────────────────────────────────────────────────────────

class CarlosStats(BaseModel):
    mensajes_respondidos: int
    citas_creadas_por_Carlos: int
    tasa_respuesta: float

class CarlosIndicacionCreate(BaseModel):
    texto: str

class CarlosIndicacionResponse(BaseModel):
    id: int
    texto: str
    activa: bool
    creado_en: datetime

    class Config:
        from_attributes = True

class CarlosIndicacionUpdate(BaseModel):
    activa: bool

# ─── WEBHOOK WhatsApp (desde n8n/Evolution API) ───────────────────────────────

class WebhookMensajeEntrante(BaseModel):
    telefono: str
    nombre: Optional[str] = None
    mensaje: str
    timestamp: Optional[str] = None
    instance: Optional[str] = None