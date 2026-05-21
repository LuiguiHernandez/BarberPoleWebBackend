from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from core.database import get_db
from core.security import get_current_user
from models.all_models import Categoria, Servicio, Negocio
from schemas.all_schemas import CategoriaCreate, CategoriaUpdate, CategoriaResponse

router = APIRouter()

def _negocio_id(usuario_id: int, db: Session) -> int:
    n = db.query(Negocio).filter(Negocio.usuario_id == usuario_id).first()
    if not n:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Negocio no encontrado")
    return n.id


@router.get("/", response_model=List[CategoriaResponse])
def listar(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    nid = _negocio_id(current_user.id, db)
    cats = db.query(Categoria).filter(
        Categoria.negocio_id == nid
    ).order_by(Categoria.orden, Categoria.nombre).all()

    result = []
    for c in cats:
        total = db.query(func.count(Servicio.id)).filter(
            Servicio.categoria_id == c.id,
            Servicio.activo == True
        ).scalar() or 0
        precio_desde = db.query(func.min(Servicio.precio)).filter(
            Servicio.categoria_id == c.id,
            Servicio.activo == True
        ).scalar()
        r = CategoriaResponse.model_validate(c)
        r.total_servicios = total
        r.precio_desde = precio_desde
        result.append(r)
    return result


@router.post("/", response_model=CategoriaResponse, status_code=201)
def crear(data: CategoriaCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    nid = _negocio_id(current_user.id, db)
    cat = Categoria(negocio_id=nid, **data.model_dump())
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


@router.put("/{categoria_id}", response_model=CategoriaResponse)
def actualizar(categoria_id: int, data: CategoriaUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    from fastapi import HTTPException
    nid = _negocio_id(current_user.id, db)
    cat = db.query(Categoria).filter(Categoria.id == categoria_id, Categoria.negocio_id == nid).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(cat, k, v)
    db.commit()
    db.refresh(cat)
    return cat


@router.delete("/{categoria_id}", status_code=204)
def eliminar(categoria_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    from fastapi import HTTPException
    nid = _negocio_id(current_user.id, db)
    cat = db.query(Categoria).filter(Categoria.id == categoria_id, Categoria.negocio_id == nid).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    # Desasociar servicios en vez de eliminarlos
    db.query(Servicio).filter(Servicio.categoria_id == categoria_id).update({"categoria_id": None})
    db.delete(cat)
    db.commit()


@router.post("/{categoria_id}/imagen")
async def upload_imagen(
    categoria_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from fastapi import HTTPException
    import os, shutil, uuid
    nid = _negocio_id(current_user.id, db)
    cat = db.query(Categoria).filter(Categoria.id == categoria_id, Categoria.negocio_id == nid).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")

    ext = os.path.splitext(file.filename or "")[1].lower() or ".jpg"
    fname = f"cat_{categoria_id}_{uuid.uuid4().hex[:8]}{ext}"
    path = f"uploads/{fname}"
    os.makedirs("uploads", exist_ok=True)
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    cat.imagen_url = f"/uploads/{fname}"
    db.commit()
    return {"imagen_url": cat.imagen_url}
