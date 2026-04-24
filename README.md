# BarberPole — Backend API

Backend completo en **Python + FastAPI + SQLite** para el sistema de gestión de barberías BarberPole.

## 🚀 Instalación rápida

```bash
# 1. Entrar a la carpeta
cd barberpole-backend

# 2. Crear entorno virtual
python -m venv venv

# Windows:
venv\Scripts\activate

# Mac/Linux:
source venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables (editar con tus datos reales)
# Abre el archivo .env y pon tus URLs de Evolution API y n8n

# 5. Insertar datos de prueba
python seed.py

# 6. Iniciar el servidor
uvicorn main:app --reload --port 8000
```

El API estará disponible en: **http://localhost:8000**
Documentación interactiva: **http://localhost:8000/docs**

---

## 📁 Estructura del proyecto

```
barberpole-backend/
├── main.py                  # App principal FastAPI
├── seed.py                  # Datos de prueba
├── requirements.txt
├── .env                     # Variables de entorno
├── core/
│   ├── config.py            # Settings (lee el .env)
│   ├── database.py          # Conexión SQLite/SQLAlchemy
│   └── security.py          # JWT + hashing
├── models/
│   └── all_models.py        # Tablas de la base de datos
├── schemas/
│   └── all_schemas.py       # Validación de datos (Pydantic)
└── routers/
    ├── auth.py              # Login / Register
    ├── citas.py             # Citas + Dashboard stats
    ├── config.py            # Negocio, Servicios, Barberos, Horarios
    └── otros.py             # Informes, Lealtad, Conversaciones, Luna IA, Webhooks
```

---

## 🔌 Endpoints disponibles

### Auth
| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/auth/register` | Registrar usuario + barbería |
| POST | `/api/auth/login` | Login → obtiene token JWT |
| GET | `/api/auth/me` | Info del usuario actual |

### Dashboard
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/citas/dashboard` | Stats: citas hoy, ingresos, etc. |

### Citas
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/citas/` | Listar citas (filtro por fecha/vista/barbero) |
| POST | `/api/citas/` | Crear cita manual |
| PUT | `/api/citas/{id}` | Actualizar cita |
| DELETE | `/api/citas/{id}` | Cancelar cita |

### Configuración
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET/PUT | `/api/negocio/` | Info del negocio |
| POST | `/api/negocio/logo` | Subir logo |
| GET/POST | `/api/servicios/` | Listar/crear servicios |
| PUT/DELETE | `/api/servicios/{id}` | Editar/eliminar servicio |
| GET/POST | `/api/barberos/` | Listar/crear barberos |
| PUT/DELETE | `/api/barberos/{id}` | Editar/eliminar barbero |
| GET/PUT | `/api/horarios/` | Ver/actualizar horarios |

### Informes
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/informes/?periodo=30d` | Stats completos con filtros |

### Lealtad
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/lealtad/clientes` | Clientes con sellos |
| POST | `/api/lealtad/sello` | Dar sello manual |
| GET | `/api/lealtad/resumen` | Stats de lealtad |

### Conversaciones (WhatsApp)
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/conversaciones/` | Listar chats |
| GET | `/api/conversaciones/{id}/mensajes` | Mensajes de un chat |
| POST | `/api/conversaciones/{id}/responder` | Responder por WhatsApp |

### Luna IA
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/luna/stats` | Estadísticas de Luna |
| GET/POST | `/api/luna/indicaciones` | Ver/agregar indicaciones |
| PUT/DELETE | `/api/luna/indicaciones/{id}` | Activar/desactivar/eliminar |

### Webhooks (n8n ↔ Evolution API)
| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/webhooks/whatsapp/{slug}` | Recibe mensajes de n8n |
| POST | `/api/webhooks/luna-respuesta` | Recibe respuesta IA de n8n |

---

## 🔗 Integración n8n + Evolution API

### Flujo completo:

```
Cliente → WhatsApp
    ↓
Evolution API (webhook)
    ↓
n8n (recibe el mensaje)
    ↓
POST /api/webhooks/whatsapp/optus-barber
    ↓
Backend guarda mensaje + envía contexto a n8n
    ↓
n8n llama a Claude/OpenAI con el contexto
    ↓
POST /api/webhooks/luna-respuesta
    ↓
Backend guarda respuesta + envía por Evolution API
    ↓
Cliente recibe respuesta de Luna IA por WhatsApp
```

### Configurar en n8n:

1. **Webhook node** que reciba de Evolution API
2. **HTTP Request node** → `POST http://localhost:8000/api/webhooks/whatsapp/optus-barber`
3. **AI node** (Claude/OpenAI) con el contexto del negocio
4. **HTTP Request node** → `POST http://localhost:8000/api/webhooks/luna-respuesta`

---

## 🔑 Autenticación

Todos los endpoints (excepto webhooks y auth) requieren token JWT.

```bash
# 1. Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "luiguid@optusbarber.com", "password": "barber123"}'

# Respuesta:
# {"access_token": "eyJ...", "token_type": "bearer", ...}

# 2. Usar el token
curl http://localhost:8000/api/citas/dashboard \
  -H "Authorization: Bearer eyJ..."
```

---

## 🛠️ Variables de entorno (.env)

```env
DATABASE_URL=sqlite:///./barberpole.db
SECRET_KEY=una-clave-secreta-larga-aqui
FRONTEND_URL=http://localhost:5173
EVOLUTION_API_URL=http://tu-evolution-api:8080
EVOLUTION_API_KEY=tu-api-key
EVOLUTION_INSTANCE=tu-instancia
N8N_URL=http://tu-n8n:5678
```

---

## 📦 Migrar a PostgreSQL (cuando quieras)

Solo cambia en `.env`:
```env
DATABASE_URL=postgresql://usuario:password@localhost:5432/barberpole
```

E instala: `pip install psycopg2-binary`
