"""
Script para insertar datos de prueba en la base de datos.
Ejecutar con: python seed.py
"""
from core.database import SessionLocal, engine, Base
import models.all_models  # noqa - registrar todos los modelos
from models.all_models import (
    Usuario, Negocio, Servicio, Barbero, Horario, DiaSemana
)
from core.security import hash_password

Base.metadata.create_all(bind=engine)

db = SessionLocal()

# Verificar si ya existe el usuario
existing = db.query(Usuario).filter(Usuario.email == "luiguid@optusbarber.com").first()
if existing:
    print("OK  Ya existen datos de prueba. Nada que hacer.")
    db.close()
    exit()

# ─── Usuario ───────────────────────────────────────────────────────────────────
usuario = Usuario(
    nombre="LuiguidBarber",
    email="luiguid@optusbarber.com",
    password_hash=hash_password("barber123"),
)
db.add(usuario)
db.flush()

# ─── Negocio ───────────────────────────────────────────────────────────────────
negocio = Negocio(
    usuario_id=usuario.id,
    nombre="Optus Barber",
    slug="optus-barber",
    telefono="+57 300 123 4567",
    whatsapp="+573001234567",
    direccion="Calle 85 #15-30, Bogotá",
    descripcion="Barbería premium con los mejores profesionales de la ciudad. Cortes modernos y clásicos.",
    lealtad_activa=False,
    lealtad_sellos_requeridos=10,
    lealtad_recompensa="Corte gratis",
)
db.add(negocio)
db.flush()

# ─── Barberos ──────────────────────────────────────────────────────────────────
b1 = Barbero(negocio_id=negocio.id, nombre="Carlos Rodríguez", telefono="+573101234567", activo=True)
b2 = Barbero(negocio_id=negocio.id, nombre="Miguel Torres", telefono="+573209876543", activo=True)
db.add_all([b1, b2])
db.flush()

# ─── Servicios ─────────────────────────────────────────────────────────────────
servicios_data = [
    {"nombre": "Corte clásico", "duracion_minutos": 30, "precio": 25000, "activo": True},
    {"nombre": "Corte + Barba", "duracion_minutos": 45, "precio": 40000, "activo": True},
    {"nombre": "Barba", "duracion_minutos": 20, "precio": 18000, "activo": True},
    {"nombre": "Corte infantil", "duracion_minutos": 25, "precio": 20000, "activo": True},
    {"nombre": "Tinte cabello", "duracion_minutos": 60, "precio": 55000, "activo": False},
    {"nombre": "Cejas", "duracion_minutos": 10, "precio": 10000, "activo": True},
]
for s in servicios_data:
    db.add(Servicio(negocio_id=negocio.id, **s))

# ─── Horarios ──────────────────────────────────────────────────────────────────
dias_config = {
    DiaSemana.lunes: (True, "09:00", "19:00"),
    DiaSemana.martes: (True, "09:00", "19:00"),
    DiaSemana.miercoles: (True, "09:00", "19:00"),
    DiaSemana.jueves: (True, "09:00", "19:00"),
    DiaSemana.viernes: (True, "09:00", "19:00"),
    DiaSemana.sabado: (True, "09:00", "17:00"),
    DiaSemana.domingo: (False, "09:00", "14:00"),
}
for dia, (abierto, hi, hf) in dias_config.items():
    db.add(Horario(
        negocio_id=negocio.id,
        dia=dia, abierto=abierto, hora_inicio=hi, hora_fin=hf
    ))

db.commit()
db.close()

print("OK  Datos de prueba insertados correctamente!")
print("    Email:    luiguid@optusbarber.com")
print("    Password: barber123")
print("    Docs:     http://localhost:8000/docs")
