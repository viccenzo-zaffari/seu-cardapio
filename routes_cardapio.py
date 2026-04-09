from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from auth import get_current_owner
import models, schemas
import cloudinary
import cloudinary.uploader
import os
import re

router = APIRouter(tags=["cardapio"])

# ── Cloudinary config ─────────────────────────────────
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
)


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[àáâãäå]', 'a', text)
    text = re.sub(r'[èéêë]', 'e', text)
    text = re.sub(r'[ìíîï]', 'i', text)
    text = re.sub(r'[òóôõö]', 'o', text)
    text = re.sub(r'[ùúûü]', 'u', text)
    text = re.sub(r'[ç]', 'c', text)
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s]+', '-', text)
    return text


# ── Restaurante ───────────────────────────────────────

@router.post("/restaurants", response_model=schemas.RestaurantOut)
def create_restaurant(
    data: schemas.RestaurantCreate,
    db: Session = Depends(get_db),
    owner: models.Owner = Depends(get_current_owner),
):
    slug = slugify(data.slug or data.name)
    existing = db.query(models.Restaurant).filter(models.Restaurant.slug == slug).first()
    if existing:
        raise HTTPException(status_code=400, detail="Este slug já está em uso. Escolha outro nome.")

    from datetime import datetime, timedelta
    restaurant = models.Restaurant(
        owner_id=owner.id,
        name=data.name,
        slug=slug,
        description=data.description,
        address=data.address,
        whatsapp=data.whatsapp,
        primary_color=data.primary_color or "#D4460A",
        plan="trial",
        status="active",
        trial_ends_at=datetime.utcnow() + timedelta(days=14),
    )
    db.add(restaurant)
    db.commit()
    db.refresh(restaurant)
    return restaurant


@router.get("/restaurants", response_model=List[schemas.RestaurantOut])
def list_restaurants(
    db: Session = Depends(get_db),
    owner: models.Owner = Depends(get_current_owner),
):
    return db.query(models.Restaurant).filter(models.Restaurant.owner_id == owner.id).all()


@router.get("/restaurants/{restaurant_id}", response_model=schemas.RestaurantOut)
def get_restaurant(
    restaurant_id: str,
    db: Session = Depends(get_db),
    owner: models.Owner = Depends(get_current_owner),
):
    r = db.query(models.Restaurant).filter(
        models.Restaurant.id == restaurant_id,
        models.Restaurant.owner_id == owner.id,
    ).first()
    if not r:
        raise HTTPException(status_code=404, detail="Restaurante não encontrado")
    return r


@router.put("/restaurants/{restaurant_id}", response_model=schemas.RestaurantOut)
def update_restaurant(
    restaurant_id: str,
    data: schemas.RestaurantUpdate,
    db: Session = Depends(get_db),
    owner: models.Owner = Depends(get_current_owner),
):
    r = db.query(models.Restaurant).filter(
        models.Restaurant.id == restaurant_id,
        models.Restaurant.owner_id == owner.id,
    ).first()
    if not r:
        raise HTTPException(status_code=404, detail="Restaurante não encontrado")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(r, field, value)
    db.commit()
    db.refresh(r)
    return r


@router.post("/restaurants/{restaurant_id}/logo")
def upload_logo(
    restaurant_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    owner: models.Owner = Depends(get_current_owner),
):
    r = db.query(models.Restaurant).filter(
        models.Restaurant.id == restaurant_id,
        models.Restaurant.owner_id == owner.id,
    ).first()
    if not r:
        raise HTTPException(status_code=404, detail="Restaurante não encontrado")

    result = cloudinary.uploader.upload(
        file.file,
        folder=f"cardapio/{restaurant_id}/logo",
        transformation=[{"width": 400, "height": 400, "crop": "fill"}],
    )
    r.logo_url = result["secure_url"]
    db.commit()
    return {"logo_url": r.logo_url}


# ── Categorias ────────────────────────────────────────

@router.post("/restaurants/{restaurant_id}/categories", response_model=schemas.CategoryOut)
def create_category(
    restaurant_id: str,
    data: schemas.CategoryCreate,
    db: Session = Depends(get_db),
    owner: models.Owner = Depends(get_current_owner),
):
    r = db.query(models.Restaurant).filter(
        models.Restaurant.id == restaurant_id,
        models.Restaurant.owner_id == owner.id,
    ).first()
    if not r:
        raise HTTPException(status_code=404, detail="Restaurante não encontrado")

    cat = models.Category(
        restaurant_id=restaurant_id,
        name=data.name,
        emoji=data.emoji,
        sort_order=data.sort_order,
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


@router.get("/restaurants/{restaurant_id}/categories", response_model=List[schemas.CategoryOut])
def list_categories(
    restaurant_id: str,
    db: Session = Depends(get_db),
    owner: models.Owner = Depends(get_current_owner),
):
    return db.query(models.Category).filter(
        models.Category.restaurant_id == restaurant_id
    ).order_by(models.Category.sort_order).all()


@router.put("/categories/{category_id}", response_model=schemas.CategoryOut)
def update_category(
    category_id: str,
    data: schemas.CategoryUpdate,
    db: Session = Depends(get_db),
    owner: models.Owner = Depends(get_current_owner),
):
    cat = db.query(models.Category).join(models.Restaurant).filter(
        models.Category.id == category_id,
        models.Restaurant.owner_id == owner.id,
    ).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(cat, field, value)
    db.commit()
    db.refresh(cat)
    return cat


@router.delete("/categories/{category_id}")
def delete_category(
    category_id: str,
    db: Session = Depends(get_db),
    owner: models.Owner = Depends(get_current_owner),
):
    cat = db.query(models.Category).join(models.Restaurant).filter(
        models.Category.id == category_id,
        models.Restaurant.owner_id == owner.id,
    ).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    db.delete(cat)
    db.commit()
    return {"ok": True}


# ── Itens do cardápio ─────────────────────────────────

@router.post("/categories/{category_id}/items", response_model=schemas.MenuItemOut)
def create_item(
    category_id: str,
    data: schemas.MenuItemCreate,
    db: Session = Depends(get_db),
    owner: models.Owner = Depends(get_current_owner),
):
    cat = db.query(models.Category).join(models.Restaurant).filter(
        models.Category.id == category_id,
        models.Restaurant.owner_id == owner.id,
    ).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")

    item = models.MenuItem(
        category_id=category_id,
        name=data.name,
        description=data.description,
        price=data.price,
        available=data.available,
        featured=data.featured,
        sort_order=data.sort_order,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/items/{item_id}", response_model=schemas.MenuItemOut)
def update_item(
    item_id: str,
    data: schemas.MenuItemUpdate,
    db: Session = Depends(get_db),
    owner: models.Owner = Depends(get_current_owner),
):
    item = db.query(models.MenuItem).join(models.Category).join(models.Restaurant).filter(
        models.MenuItem.id == item_id,
        models.Restaurant.owner_id == owner.id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/items/{item_id}/toggle", response_model=schemas.MenuItemOut)
def toggle_available(
    item_id: str,
    db: Session = Depends(get_db),
    owner: models.Owner = Depends(get_current_owner),
):
    item = db.query(models.MenuItem).join(models.Category).join(models.Restaurant).filter(
        models.MenuItem.id == item_id,
        models.Restaurant.owner_id == owner.id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado")

    item.available = not item.available
    db.commit()
    db.refresh(item)
    return item


@router.post("/items/{item_id}/image")
def upload_item_image(
    item_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    owner: models.Owner = Depends(get_current_owner),
):
    item = db.query(models.MenuItem).join(models.Category).join(models.Restaurant).filter(
        models.MenuItem.id == item_id,
        models.Restaurant.owner_id == owner.id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado")

    result = cloudinary.uploader.upload(
        file.file,
        folder=f"cardapio/items",
        transformation=[{"width": 600, "height": 600, "crop": "fill"}],
    )
    item.image_url = result["secure_url"]
    db.commit()
    return {"image_url": item.image_url}


@router.delete("/items/{item_id}")
def delete_item(
    item_id: str,
    db: Session = Depends(get_db),
    owner: models.Owner = Depends(get_current_owner),
):
    item = db.query(models.MenuItem).join(models.Category).join(models.Restaurant).filter(
        models.MenuItem.id == item_id,
        models.Restaurant.owner_id == owner.id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    db.delete(item)
    db.commit()
    return {"ok": True}


# ── Rota pública (sem auth) ───────────────────────────

@router.get("/menu/{slug}", response_model=schemas.PublicMenuOut)
def public_menu(slug: str, db: Session = Depends(get_db)):
    r = db.query(models.Restaurant).filter(
        models.Restaurant.slug == slug,
        models.Restaurant.status == "active",
    ).first()
    if not r:
        raise HTTPException(status_code=404, detail="Cardápio não encontrado")
    return r


# ── QR Code ───────────────────────────────────────────

@router.get("/restaurants/{restaurant_id}/qrcode")
def generate_qr(
    restaurant_id: str,
    db: Session = Depends(get_db),
    owner: models.Owner = Depends(get_current_owner),
):
    from fastapi.responses import StreamingResponse
    import qrcode
    import io

    r = db.query(models.Restaurant).filter(
        models.Restaurant.id == restaurant_id,
        models.Restaurant.owner_id == owner.id,
    ).first()
    if not r:
        raise HTTPException(status_code=404, detail="Restaurante não encontrado")

    base_url = os.getenv("FRONTEND_URL", "https://seucardapio.com.br")
    url = f"{base_url}/{r.slug}"

    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="image/png",
        headers={"Content-Disposition": f"attachment; filename=qrcode-{r.slug}.png"},
    )
