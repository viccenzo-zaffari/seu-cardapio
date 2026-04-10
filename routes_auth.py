from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models, schemas, auth

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=schemas.Token)
def register(data: schemas.OwnerCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Owner).filter(models.Owner.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email já cadastrado")

    owner = models.Owner(
        name=data.name,
        email=data.email,
        password_hash=auth.hash_password(data.password),
    )
    db.add(owner)
    db.commit()
    db.refresh(owner)

    token = auth.create_access_token(str(owner.id))
    return {"access_token": token}


@router.post("/login", response_model=schemas.Token)
def login(data: schemas.OwnerLogin, db: Session = Depends(get_db)):
    owner = db.query(models.Owner).filter(models.Owner.email == data.email).first()
    if not owner or not auth.verify_password(data.password, owner.password_hash):
        raise HTTPException(status_code=401, detail="Email ou senha incorretos")

    token = auth.create_access_token(str(owner.id))
    return {"access_token": token}


@router.get("/me", response_model=schemas.OwnerOut)
def me(current_owner: models.Owner = Depends(auth.get_current_owner)):
    return current_owner