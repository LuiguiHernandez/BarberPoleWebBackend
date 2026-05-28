"""
Router Admin — solo accesible por superadmin
Gestión completa de todos los negocios de GestorPro
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from pydantic import BaseModel
from core.database import get_db
from core.security import require_superadmin
from core.temas import get_tema_negocio, get_tema, TEMAS
from models.all_models import Usuario, Negocio, Cita, Servicio, Barbero

router = APIRouter()


# ── Listar todos los negocios ─────────────────────────────────────
@router.get("/negocios")
def listar_negocios(
    db: Session = Depends(get_db),
    _=Depends(require_superadmin),
):
    negocios = db.query(Negocio).order_by(Negocio.id).all()
    result = []
    for n in negocios:
        usuario = db.query(Usuario).filter(Usuario.id == n.usuario_id).first()
        total_citas = db.query(func.count(Cita.id)).filter(Cita.negocio_id == n.id).scalar() or 0
        total_servicios = db.query(func.count(Servicio.id)).filter(Servicio.negocio_id == n.id).scalar() or 0
        result.append({
            "id": n.id,
            "nombre": n.nombre,
            "slug": n.slug,
            "tipo_negocio": getattr(n, 'tipo_negocio', 'general'),
            "tema": get_tema_negocio(n),
            "url_web": getattr(n, 'url_web', None),
            "activo": getattr(usuario, 'activo', True) if usuario else True,
            "plan": "pilot",
            "total_citas": total_citas,
            "total_servicios": total_servicios,
            "email_owner": usuario.email if usuario else None,
            "nombre_owner": usuario.nombre if usuario else None,
            "creado_en": n.creado_en.isoformat() if n.creado_en else None,
        })
    return result


# ── Ver un negocio específico ─────────────────────────────────────
@router.get("/negocios/{negocio_id}")
def get_negocio(
    negocio_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_superadmin),
):
    n = db.query(Negocio).filter(Negocio.id == negocio_id).first()
    if not n:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")
    usuario = db.query(Usuario).filter(Usuario.id == n.usuario_id).first()
    return {
        "id": n.id,
        "nombre": n.nombre,
        "slug": n.slug,
        "telefono": n.telefono,
        "direccion": n.direccion,
        "tipo_negocio": getattr(n, 'tipo_negocio', 'general'),
        "color_primario": getattr(n, 'color_primario', '#00A86B'),
        "color_secundario": getattr(n, 'color_secundario', '#E8F5EE'),
        "color_fondo": getattr(n, 'color_fondo', '#FFFFFF'),
        "url_web": getattr(n, 'url_web', None),
        "tema": get_tema_negocio(n),
        "email_owner": usuario.email if usuario else None,
        "activo": getattr(usuario, 'activo', True) if usuario else True,
    }


# ── Crear negocio ─────────────────────────────────────────────────
class NegocioAdminCreate(BaseModel):
    nombre: str
    slug: str
    email_owner: str
    password_owner: str
    tipo_negocio: str = "general"
    url_web: Optional[str] = None
    telefono: Optional[str] = None


@router.post("/negocios", status_code=201)
def crear_negocio(
    data: NegocioAdminCreate,
    db: Session = Depends(get_db),
    _=Depends(require_superadmin),
):
    from core.security import hash_password

    # Verificar slug único
    if db.query(Negocio).filter(Negocio.slug == data.slug).first():
        raise HTTPException(status_code=400, detail=f"El slug '{data.slug}' ya existe")
    if db.query(Usuario).filter(Usuario.email == data.email_owner).first():
        raise HTTPException(status_code=400, detail=f"El email '{data.email_owner}' ya está registrado")

    tema = get_tema(data.tipo_negocio)

    # Crear usuario
    usuario = Usuario(
        nombre=data.nombre,
        email=data.email_owner,
        password_hash=hash_password(data.password_owner),
        rol="cliente",
        activo=True,
    )
    db.add(usuario)
    db.flush()

    # Crear negocio
    negocio = Negocio(
        usuario_id=usuario.id,
        nombre=data.nombre,
        slug=data.slug,
        telefono=data.telefono,
        tipo_negocio=data.tipo_negocio,
        color_primario=tema["color_primario"],
        color_secundario=tema["color_secundario"],
        color_fondo=tema["color_fondo"],
        color_texto=tema["color_texto"],
        url_web=data.url_web,
    )
    db.add(negocio)
    db.commit()
    db.refresh(negocio)

    return {
        "ok": True,
        "negocio_id": negocio.id,
        "usuario_id": usuario.id,
        "slug": negocio.slug,
        "mensaje": f"Negocio '{data.nombre}' creado. Credenciales: {data.email_owner} / {data.password_owner}",
    }


# ── Actualizar negocio (admin puede cambiar todo) ─────────────────
class NegocioAdminUpdate(BaseModel):
    nombre: Optional[str] = None
    slug: Optional[str] = None          # solo admin puede cambiar el slug
    tipo_negocio: Optional[str] = None  # solo admin puede cambiar el tipo
    color_primario: Optional[str] = None
    color_secundario: Optional[str] = None
    color_fondo: Optional[str] = None
    url_web: Optional[str] = None
    telefono: Optional[str] = None


@router.put("/negocios/{negocio_id}")
def actualizar_negocio(
    negocio_id: int,
    data: NegocioAdminUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_superadmin),
):
    n = db.query(Negocio).filter(Negocio.id == negocio_id).first()
    if not n:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")

    # Si cambia el tipo, aplicar colores del tema como base
    if data.tipo_negocio and data.tipo_negocio != getattr(n, 'tipo_negocio', None):
        tema = get_tema(data.tipo_negocio)
        n.tipo_negocio    = data.tipo_negocio
        n.color_primario  = data.color_primario or tema["color_primario"]
        n.color_secundario= data.color_secundario or tema["color_secundario"]
        n.color_fondo     = data.color_fondo or tema["color_fondo"]
    else:
        for field in ['nombre', 'slug', 'color_primario', 'color_secundario', 'color_fondo', 'url_web', 'telefono']:
            val = getattr(data, field, None)
            if val is not None:
                setattr(n, field, val)

    db.commit()
    db.refresh(n)
    return {"ok": True, "tema": get_tema_negocio(n)}


# ── Activar / Suspender negocio ───────────────────────────────────
@router.patch("/negocios/{negocio_id}/activo")
def toggle_activo(
    negocio_id: int,
    activo: bool,
    db: Session = Depends(get_db),
    _=Depends(require_superadmin),
):
    n = db.query(Negocio).filter(Negocio.id == negocio_id).first()
    if not n:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")
    usuario = db.query(Usuario).filter(Usuario.id == n.usuario_id).first()
    if usuario:
        usuario.activo = activo
    db.commit()
    return {"ok": True, "activo": activo, "negocio": n.nombre}


# ── Métricas globales ─────────────────────────────────────────────
@router.get("/stats")
def stats_globales(
    db: Session = Depends(get_db),
    _=Depends(require_superadmin),
):
    total_negocios  = db.query(func.count(Negocio.id)).scalar() or 0
    total_citas     = db.query(func.count(Cita.id)).scalar() or 0
    total_usuarios  = db.query(func.count(Usuario.id)).scalar() or 0
    negocios_activos = db.query(func.count(Usuario.id)).filter(Usuario.activo == True, Usuario.rol == "cliente").scalar() or 0
    por_tipo = db.query(
        Negocio.tipo_negocio,
        func.count(Negocio.id).label("total")
    ).group_by(Negocio.tipo_negocio).all()
    return {
        "total_negocios": total_negocios,
        "negocios_activos": negocios_activos,
        "total_citas": total_citas,
        "total_usuarios": total_usuarios,
        "por_tipo": [{"tipo": t, "total": c} for t, c in por_tipo],
    }


# ── Mis datos como superadmin ─────────────────────────────────────
@router.get("/me")
def me(current_user=Depends(require_superadmin)):
    return {
        "id": current_user.id,
        "nombre": current_user.nombre,
        "email": current_user.email,
        "rol": current_user.rol,
    }
