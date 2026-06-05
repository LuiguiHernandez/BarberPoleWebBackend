# GestorPro — Backend API

Backend de GestorPro SaaS construido con **FastAPI + PostgreSQL + Python 3.12**.
Plataforma multi-tenant de gestión de citas para negocios de servicios
(barberías, spas, clínicas, veterinarias, etc.).

---

## Tabla de contenidos

1. [Stack tecnológico](#stack-tecnológico)
2. [Arquitectura](#arquitectura)
3. [Instalación local](#instalación-local)
4. [Variables de entorno](#variables-de-entorno)
5. [Estructura de carpetas](#estructura-de-carpetas)
6. [Módulos clave](#módulos-clave)
7. [Endpoints de la API](#endpoints-de-la-api)
8. [Base de datos](#base-de-datos)
9. [Integraciones](#integraciones)
10. [Seguridad](#seguridad)
11. [Deploy en producción](#deploy-en-producción)

---

## Stack tecnológico

| Tecnología | Versión | Uso |
|---|---|---|
| Python | 3.12+ | Lenguaje principal |
| FastAPI | 0.115 | Framework web / API REST |
| SQLAlchemy | 2.0 | ORM — acceso a la base de datos |
| PostgreSQL | 15+ | Base de datos principal |
| Pydantic | 2.9 | Validación y serialización de datos |
| Docker Compose | — | Orquestación local y producción |
| slowapi | 0.1.9 | Rate limiting en endpoints |
| cryptography | 42+ | Cifrado AES de tokens OAuth |
| resend | 2.0+ | Emails transaccionales |

---

## Arquitectura

El backend sigue una arquitectura en capas:

```
HTTP Request
    ↓
routers/        ← Recibe la petición, valida auth, llama al servicio
    ↓
services/       ← Lógica de negocio, orquesta repositorios e integraciones
    ↓
repositories/   ← Única capa que habla con la base de datos
    ↓
models/         ← Definición de tablas SQLAlchemy
```

### Multi-tenant

Cada negocio tiene sus datos completamente aislados.
La columna `negocio_id` en todas las tablas actúa como separador de tenant.
Un usuario solo puede ver y modificar los datos de su propio negocio.

---

## Instalación local

### Requisitos
- Python 3.12+
- WSL (Ubuntu) recomendado en Windows
- Acceso a PostgreSQL (local o remoto)

```bash
# 1. Clonar
git clone https://github.com/LuiguiHernandez/BarberPoleWebBackend.git
cd BarberPoleWebBackend

# 2. Entorno virtual
python3 -m venv venv
source venv/bin/activate

# 3. Dependencias
pip install -r requirements.txt

# 4. Variables de entorno
# Crear .env con los valores (ver sección siguiente)

# 5. Arrancar
uvicorn main:app --reload --port 8000
```

**Disponible en:**
- API: `http://localhost:8000`
- Docs interactivos: `http://localhost:8000/docs`

---

## Variables de entorno

Crear `.env` en la raíz (nunca subir al repo, está en `.gitignore`):

```env
# Base de datos PostgreSQL
DATABASE_URL=postgresql://usuario:password@host:5432/nombre_db

# JWT — tokens de sesión
SECRET_KEY=clave_larga_y_aleatoria_min_32_chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15

# CORS — URL del frontend
FRONTEND_URL=http://localhost:5173

# Cifrado de tokens OAuth en BD
# Generar con: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY=

# WhatsApp — Evolution API
EVOLUTION_API_URL=http://tu-servidor:8080
EVOLUTION_API_KEY=tu_api_key
EVOLUTION_INSTANCE=nombre_instancia

# Google Calendar
GCAL_CLIENT_ID=xxx.apps.googleusercontent.com
GCAL_CLIENT_SECRET=GOCSPX-xxx
GCAL_REDIRECT_URI=http://localhost:8000/api/gcal/callback

# Email — Resend
RESEND_API_KEY=re_xxxxxxxx
EMAIL_FROM=GestorPro <noreply@gestorpro.app>

# IA — Google Gemini (asistente Carlos)
GEMINI_API_KEY=AIza_xxx

# App
APP_NAME=GestorPro
DEBUG=true
```

---

## Estructura de carpetas

```
BarberPoleWebBackend/
│
├── main.py                    Punto de entrada — registro de todos los routers
│
├── core/
│   ├── config.py              Settings con Pydantic, helpers encrypt/decrypt
│   ├── database.py            Conexión PostgreSQL, función get_db()
│   ├── security.py            JWT access/refresh tokens, bcrypt, dependencias auth
│   └── temas.py               10 temas visuales predefinidos por tipo de negocio
│
├── models/
│   └── all_models.py          Todos los modelos SQLAlchemy (tablas de la BD)
│
├── schemas/
│   └── all_schemas.py         Todos los schemas Pydantic (validación de datos)
│
├── repositories/              Una clase por entidad — solo consultas SQL
│   ├── base_repository.py     CRUD genérico reutilizable
│   ├── cita_repository.py     Consultas especializadas con joins y filtros
│   ├── negocio_repository.py  Búsqueda por slug y por usuario_id
│   └── ...
│
├── services/                  Lógica de negocio — una clase por dominio
│   ├── auth_service.py        Registro, login, refresh token
│   ├── cita_service.py        Crear/editar/cancelar + trigger WA + GCal
│   ├── gcal_service.py        Crear/actualizar/eliminar eventos en Google Calendar
│   ├── whatsapp_service.py    Confirmación, recordatorio, resumen diario
│   ├── email_service.py       Emails con Resend API + templates HTML
│   ├── scheduler_service.py   Tareas automáticas en background
│   ├── kommo_service.py       Integración Kommo CRM
│   └── carlos_service.py      Asistente IA con Google Gemini
│
├── routers/                   Un archivo por dominio — define los endpoints HTTP
│   ├── auth.py                POST /login /register /refresh
│   ├── password_reset.py      POST /forgot-password /reset-password
│   ├── citas.py               CRUD de citas autenticado
│   ├── public_booking.py      Booking público para widget (sin autenticación)
│   ├── admin.py               Panel superadmin — gestión global
│   ├── gcal.py                OAuth Google Calendar
│   ├── kommo.py               Webhook y sincronización Kommo
│   └── ...
│
├── static/
│   ├── gestorpro-widget.iife.js   Widget de reservas embebible en WordPress
│   └── demo.html                  Página de demo del widget
│
├── requirements.txt           Dependencias Python
├── Dockerfile                 Imagen Docker para producción
├── docker-compose.yml         Orquestación de contenedores
└── seed.py                    Script para poblar la BD con datos de ejemplo
```

---

## Módulos clave

### `core/security.py`

Maneja toda la autenticación:

```python
# Crear tokens
create_access_token({"sub": str(user_id)})   # Expira en 15 min
create_refresh_token({"sub": str(user_id)})  # Expira en 7 días

# Dependencias FastAPI — se usan en los routers
get_current_user()     # Cualquier usuario autenticado
require_superadmin()   # Solo rol='superadmin'

# Contraseñas
hash_password("texto")         # → hash bcrypt
verify_password("texto", hash) # → True/False
```

### `core/config.py`

```python
# Acceder a variables de entorno
from core.config import settings
settings.DATABASE_URL
settings.SECRET_KEY

# Cifrado de tokens OAuth (se almacenan cifrados en BD)
from core.config import encrypt_token, decrypt_token
token_cifrado = encrypt_token("ya29.google_token_real")
token_real    = decrypt_token(token_cifrado)
```

### `services/cita_service.py`

Al **crear** una cita dispara automáticamente (sin bloquear la respuesta):
1. Crea el evento en **Google Calendar** si está conectado
2. Envía **WhatsApp** de confirmación al cliente

Al **cancelar** una cita:
1. Elimina el evento de Google Calendar
2. Envía **WhatsApp** de notificación al cliente

### `services/scheduler_service.py`

Loop en background que inicia con la app (via `lifespan` en `main.py`):

| Tarea | Frecuencia | Descripción |
|---|---|---|
| `job_recordatorios()` | Cada 15 min | Busca citas que empiecen en ~2h y envía WhatsApp |
| `job_resumen_diario()` | 7:30am COL | Envía lista de citas del día al dueño del negocio |

### `routers/public_booking.py`

Endpoints **sin autenticación** para el widget de WordPress y reservas externas:

```
GET  /api/public/{slug}/info         Info del negocio, servicios y profesionales
GET  /api/public/{slug}/slots        Disponibilidad real (considera citas existentes)
GET  /api/public/{slug}/sugerencias  Servicios complementarios recomendados
POST /api/public/{slug}/reservar     Crear una cita sin tener cuenta
```

### `routers/admin.py`

Solo accesible con `rol = 'superadmin'`:

```
GET  /api/admin/negocios             Lista todos los negocios + stats
POST /api/admin/negocios             Crear negocio + usuario propietario
PUT  /api/admin/negocios/{id}        Editar tipo, colores, URL
POST /api/admin/negocios/{id}/toggle Activar o suspender negocio
GET  /api/admin/stats                Métricas globales del SaaS
```

---

## Endpoints de la API

La documentación interactiva completa está en `/docs` cuando el servidor está corriendo.

### Autenticación
```
POST /api/auth/login              Login → access_token + refresh_token
POST /api/auth/register           Registro nuevo negocio
POST /api/auth/refresh            Renovar sesión con refresh_token
POST /api/auth/forgot-password    Solicitar reset de contraseña
POST /api/auth/reset-password     Cambiar contraseña con token del email
GET  /api/auth/me                 Perfil del usuario autenticado
```

### Citas
```
GET    /api/citas/              Lista citas (filtros: fecha, barbero, estado)
POST   /api/citas/              Crear cita
PUT    /api/citas/{id}          Editar cita
PATCH  /api/citas/{id}/estado   Cambiar estado
DELETE /api/citas/{id}          Cancelar cita
```

### Configuración del negocio
```
GET /api/negocio/       Datos del negocio
PUT /api/negocio/       Actualizar datos generales
```

### Google Calendar
```
GET  /api/gcal/auth-url      URL para iniciar OAuth con Google
GET  /api/gcal/callback      Callback (Google redirige aquí tras autorizar)
GET  /api/gcal/estado        Estado de conexión y calendar_id
POST /api/gcal/desconectar   Eliminar tokens y desconectar
```

### Kommo CRM
```
GET  /api/kommo/estado          Conexión activa o no
POST /api/kommo/conectar        Conectar con token manual
POST /api/kommo/desconectar     Desconectar
POST /api/kommo/webhook/{slug}  Recibe eventos de Kommo (leads, mensajes)
POST /api/kommo/sincronizar     Importar contactos de Kommo como clientes
GET  /api/kommo/stats           Métricas para el panel de informes
```

---

## Base de datos

### Diagrama simplificado

```
usuarios
    └─(1:1)─ negocios
                ├─(1:N)─ categorias
                ├─(1:N)─ servicios ──────── (pertenece a una categoria)
                ├─(1:N)─ profesionales
                ├─(1:7)─ horarios ────────── (lunes a domingo)
                ├─(1:N)─ clientes
                │            └─(1:N)─ citas ─── (servicio, profesional, estado)
                └─(1:N)─ conversaciones
                             └─(1:N)─ mensajes
```

### Tabla `citas` — campos importantes

| Campo | Tipo | Descripción |
|---|---|---|
| `estado` | enum | pendiente / confirmada / completada / cancelada / no_asistio |
| `servicios_adicionales` | TEXT | JSON con servicios extra del carrito |
| `gcal_event_id` | VARCHAR | ID del evento en Google Calendar |
| `fuente` | VARCHAR | admin / whatsapp / web / wordpress |
| `creada_manualmente` | BOOL | Si la creó el admin o un cliente |

---

## Integraciones

### WhatsApp — Evolution API
El servidor de Evolution API debe estar corriendo en `EVOLUTION_API_URL`.
Se envían 4 tipos de mensajes automáticos:
1. **Confirmación** al crear la cita
2. **Recordatorio** 2 horas antes
3. **Cancelación** al cancelar
4. **Resumen diario** al dueño a las 7:30am

### Google Calendar
- OAuth2 con tokens cifrados en BD con Fernet (AES-128)
- Si el token expira (`invalid_grant`), el negocio se desconecta automáticamente
- Reconectar desde Config → Negocio → Google Calendar

### Kommo CRM
- Plan Basic requerido para acceso API ($15/usuario/mes)
- Con plan de prueba solo funcionan los webhooks entrantes
- Webhook URL: `http://servidor:8000/api/kommo/webhook/{slug}`

### Resend — Emails
- Sin `RESEND_API_KEY`: los emails se imprimen en los logs (modo desarrollo)
- Con `RESEND_API_KEY`: emails reales con templates HTML
- Plan gratuito: 3.000 emails/mes

---

## Seguridad

| Capa | Implementación |
|---|---|
| Rate limiting | 5 req/min en `/login`, 10/min en `/register` (slowapi) |
| Tokens JWT | access_token 15min + refresh_token 7 días |
| Contraseñas | bcrypt con salt automático |
| Tokens OAuth | Cifrado Fernet AES-128 antes de guardar en BD |
| Inyección SQL | Prevenida por SQLAlchemy ORM |
| Multi-tenant | Filtro por `negocio_id` en todas las consultas |

---

## Deploy en producción

### Servidor actual
- **Proveedor:** DigitalOcean
- **IP:** `167.172.145.102`
- **Contenedores activos:**
  ```
  servorax-api    → FastAPI en puerto 8000
  servorax-db     → PostgreSQL en puerto 5432
  servorax-web    → Frontend React en puerto 80
  evolution-api   → WhatsApp API en puerto 8080
  ```

### Actualizar producción

```bash
cd /var/www/ServoraX
git -C BarberPoleWebBackend pull
docker compose up -d --build api
```

### Aplicar migraciones de BD

```bash
docker exec -it servorax-db psql -U luigui -d servorax_db -c "
ALTER TABLE nombre_tabla ADD COLUMN IF NOT EXISTS nueva_columna TIPO;
"
```

---

## Cuenta de desarrollo

```
Email:    demo.barberia@gestorpro.com
Password: Demo2026
Rol:      superadmin → redirige a /admin
Slug:     barberia-corte-fino
```

---

*GestorPro SaaS — Backend v2.0 — Junio 2026*
