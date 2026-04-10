from pydantic import BaseModel, EmailStr
from typing import Optional, List
from decimal import Decimal
from datetime import datetime
import uuid


# ── Auth ──────────────────────────────────────────────

class OwnerCreate(BaseModel):
    name: str
    email: EmailStr
    password: str

class OwnerLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class OwnerOut(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    created_at: datetime
    class Config:
        from_attributes = True


# ── Restaurant ────────────────────────────────────────

class RestaurantCreate(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    address: Optional[str] = None
    whatsapp: Optional[str] = None
    primary_color: Optional[str] = "#D4460A"

class RestaurantUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    address: Optional[str] = None
    whatsapp: Optional[str] = None
    primary_color: Optional[str] = None

class RestaurantOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    description: Optional[str]
    logo_url: Optional[str]
    primary_color: str
    address: Optional[str]
    whatsapp: Optional[str]
    plan: str
    status: str
    created_at: datetime
    class Config:
        from_attributes = True


# ── Category ──────────────────────────────────────────

class CategoryCreate(BaseModel):
    name: str
    emoji: Optional[str] = None
    sort_order: Optional[int] = 0

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    emoji: Optional[str] = None
    sort_order: Optional[int] = None

class CategoryOut(BaseModel):
    id: uuid.UUID
    name: str
    emoji: Optional[str]
    sort_order: int
    class Config:
        from_attributes = True


# ── MenuItem ──────────────────────────────────────────

class MenuItemCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price: Decimal
    available: Optional[bool] = True
    featured: Optional[bool] = False
    sort_order: Optional[int] = 0

class MenuItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    available: Optional[bool] = None
    featured: Optional[bool] = None
    sort_order: Optional[int] = None

class MenuItemOut(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    price: Decimal
    image_url: Optional[str]
    available: bool
    featured: bool
    sort_order: int
    class Config:
        from_attributes = True


# ── Menu público (sem auth) ───────────────────────────

class PublicMenuItemOut(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    price: Decimal
    image_url: Optional[str]
    available: bool
    featured: bool
    class Config:
        from_attributes = True

class PublicCategoryOut(BaseModel):
    id: uuid.UUID
    name: str
    emoji: Optional[str]
    items: List[PublicMenuItemOut]
    class Config:
        from_attributes = True

class PublicMenuOut(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    logo_url: Optional[str]
    primary_color: str
    address: Optional[str]
    whatsapp: Optional[str]
    categories: List[PublicCategoryOut]
    class Config:
        from_attributes = True