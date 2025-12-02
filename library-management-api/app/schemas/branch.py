from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class BranchBase(BaseModel):
    name: str
    address: Optional[str] = None
    description: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: bool = True


class BranchCreate(BranchBase):
    name: str  # obligatorio


class BranchUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    description: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None


class BranchRead(BranchBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # pydantic v2
