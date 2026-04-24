from sqlalchemy import (
    Column, Integer, String, Boolean, Float, DateTime,
    ForeignKey, Text, Enum, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.database import Base
import enum


# ─── ENUMS ────────────────────────────────────────────────────────────────────

class EstadoCita(str, enum.Enum):
    pendiente = "pendiente"
    confirmada = "confirmada"
    completada = "completada"
    cancelada = "cancelada"
    no_asistio = "no_asistio"


class DiaSemana(str, enum.Enum):
    lunes = "lunes"
    martes = "martes"
    miercoles = "miercoles"
    jueves = "jueves"
    viernes = "viernes"
    sabado = "sabado"
    domingo = "domingo"


# ─── USUARIO (dueño de la barbería) ───────────────────────────────────────────

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())

    negocio = relationship("Negocio", back_populates="usuario", uselist=False)


# ─── NEGOCIO ──────────────────────────────────────────────────────────────────

class Negocio(Base):
    __tablename__ = "negocios"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), unique=True)
    nombre = Column(String(100), nullable=False, default="Mi Barbería")
    slug = Column(String(100), unique=True, index=True)
    telefono = Column(String(20))
    whatsapp = Column(String(20))
    direccion = Column(String(200))
    descripcion = Column(Text)
    logo_url = Column(String(500))
    # Configuración de lealtad
    lealtad_activa = Column(Boolean, default=False)
    lealtad_sellos_requeridos = Column(Integer, default=10)
    lealtad_recompensa = Column(String(200), default="Corte gratis")
    # Configuración de reservas
    reservas_activas = Column(Boolean, default=True)
    reservas_anticipacion_max_dias = Column(Integer, default=30)
    reservas_cancelacion_horas = Column(Integer, default=2)
    # Configuración de pagos
    acepta_efectivo = Column(Boolean, default=True)
    acepta_transferencia = Column(Boolean, default=False)
    acepta_tarjeta = Column(Boolean, default=False)
    # Notificaciones WhatsApp
    notif_nueva_cita = Column(Boolean, default=True)
    notif_recordatorio = Column(Boolean, default=True)
    notif_cancelacion = Column(Boolean, default=True)
    # Luna IA
    luna_activa = Column(Boolean, default=False)
    luna_recordatorios_activos = Column(Boolean, default=True)

    creado_en = Column(DateTime(timezone=True), server_default=func.now())
    actualizado_en = Column(DateTime(timezone=True), onupdate=func.now())

    usuario = relationship("Usuario", back_populates="negocio")
    barberos = relationship("Barbero", back_populates="negocio", cascade="all, delete")
    servicios = relationship("Servicio", back_populates="negocio", cascade="all, delete")
    clientes = relationship("Cliente", back_populates="negocio", cascade="all, delete")
    citas = relationship("Cita", back_populates="negocio", cascade="all, delete")
    horarios = relationship("Horario", back_populates="negocio", cascade="all, delete")
    luna_indicaciones = relationship("LunaIndicacion", back_populates="negocio", cascade="all, delete")


# ─── SERVICIO ─────────────────────────────────────────────────────────────────

class Servicio(Base):
    __tablename__ = "servicios"

    id = Column(Integer, primary_key=True, index=True)
    negocio_id = Column(Integer, ForeignKey("negocios.id"), nullable=False)
    nombre = Column(String(100), nullable=False)
    descripcion = Column(Text)
    duracion_minutos = Column(Integer, nullable=False, default=30)
    precio = Column(Float, nullable=False)
    activo = Column(Boolean, default=True)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())

    negocio = relationship("Negocio", back_populates="servicios")
    citas = relationship("Cita", back_populates="servicio")


# ─── BARBERO ──────────────────────────────────────────────────────────────────

class Barbero(Base):
    __tablename__ = "barberos"

    id = Column(Integer, primary_key=True, index=True)
    negocio_id = Column(Integer, ForeignKey("negocios.id"), nullable=False)
    nombre = Column(String(100), nullable=False)
    telefono = Column(String(20))
    email = Column(String(150))
    foto_url = Column(String(500))
    activo = Column(Boolean, default=True)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())

    negocio = relationship("Negocio", back_populates="barberos")
    citas = relationship("Cita", back_populates="barbero")
    horarios = relationship("Horario", back_populates="barbero")


# ─── HORARIO ──────────────────────────────────────────────────────────────────

class Horario(Base):
    __tablename__ = "horarios"

    id = Column(Integer, primary_key=True, index=True)
    negocio_id = Column(Integer, ForeignKey("negocios.id"), nullable=False)
    barbero_id = Column(Integer, ForeignKey("barberos.id"), nullable=True)
    dia = Column(Enum(DiaSemana), nullable=False)
    abierto = Column(Boolean, default=True)
    hora_inicio = Column(String(5), default="09:00")   # "09:00"
    hora_fin = Column(String(5), default="18:00")       # "18:00"

    negocio = relationship("Negocio", back_populates="horarios")
    barbero = relationship("Barbero", back_populates="horarios")


# ─── CLIENTE ──────────────────────────────────────────────────────────────────

class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    negocio_id = Column(Integer, ForeignKey("negocios.id"), nullable=False)
    nombre = Column(String(100), nullable=False)
    telefono = Column(String(20), index=True)
    email = Column(String(150))
    # Lealtad
    sellos = Column(Integer, default=0)
    sellos_totales = Column(Integer, default=0)   # histórico
    recompensas_canjeadas = Column(Integer, default=0)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())

    negocio = relationship("Negocio", back_populates="clientes")
    citas = relationship("Cita", back_populates="cliente")
    conversaciones = relationship("Conversacion", back_populates="cliente")


# ─── CITA ─────────────────────────────────────────────────────────────────────

class Cita(Base):
    __tablename__ = "citas"

    id = Column(Integer, primary_key=True, index=True)
    negocio_id = Column(Integer, ForeignKey("negocios.id"), nullable=False)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=True)
    barbero_id = Column(Integer, ForeignKey("barberos.id"), nullable=True)
    servicio_id = Column(Integer, ForeignKey("servicios.id"), nullable=True)

    # Datos de la cita
    fecha_hora = Column(DateTime(timezone=True), nullable=False)
    duracion_minutos = Column(Integer, default=30)
    precio = Column(Float, default=0)
    estado = Column(Enum(EstadoCita), default=EstadoCita.pendiente)
    notas = Column(Text)

    # Origen de la cita
    creada_por_luna = Column(Boolean, default=False)
    creada_manualmente = Column(Boolean, default=False)

    creado_en = Column(DateTime(timezone=True), server_default=func.now())
    actualizado_en = Column(DateTime(timezone=True), onupdate=func.now())

    negocio = relationship("Negocio", back_populates="citas")
    cliente = relationship("Cliente", back_populates="citas")
    barbero = relationship("Barbero", back_populates="citas")
    servicio = relationship("Servicio", back_populates="citas")


# ─── CONVERSACIÓN (WhatsApp) ──────────────────────────────────────────────────

class Conversacion(Base):
    __tablename__ = "conversaciones"

    id = Column(Integer, primary_key=True, index=True)
    negocio_id = Column(Integer, ForeignKey("negocios.id"), nullable=False)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=True)
    telefono = Column(String(30), nullable=False, index=True)
    nombre_contacto = Column(String(100))
    ultimo_mensaje = Column(Text)
    ultimo_mensaje_en = Column(DateTime(timezone=True))
    no_leidos = Column(Integer, default=0)
    manejada_por_luna = Column(Boolean, default=True)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())

    cliente = relationship("Cliente", back_populates="conversaciones")
    mensajes = relationship("Mensaje", back_populates="conversacion", cascade="all, delete")


class Mensaje(Base):
    __tablename__ = "mensajes"

    id = Column(Integer, primary_key=True, index=True)
    conversacion_id = Column(Integer, ForeignKey("conversaciones.id"), nullable=False)
    contenido = Column(Text, nullable=False)
    enviado_por = Column(String(20), default="cliente")  # "cliente" | "luna" | "barberia"
    enviado_en = Column(DateTime(timezone=True), server_default=func.now())
    leido = Column(Boolean, default=False)

    conversacion = relationship("Conversacion", back_populates="mensajes")


# ─── LUNA IA - INDICACIONES ───────────────────────────────────────────────────

class LunaIndicacion(Base):
    __tablename__ = "luna_indicaciones"

    id = Column(Integer, primary_key=True, index=True)
    negocio_id = Column(Integer, ForeignKey("negocios.id"), nullable=False)
    texto = Column(Text, nullable=False)
    activa = Column(Boolean, default=True)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())

    negocio = relationship("Negocio", back_populates="luna_indicaciones")
