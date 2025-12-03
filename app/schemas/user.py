from pydantic import BaseModel, EmailStr
from enum import Enum
from typing import Optional


class UserRole(str, Enum):
    MEMBER = "member"
    LIBRARIAN = "librarian"
    ADMIN = "admin"


class UserBase(BaseModel):
    email: str
    full_name: str
    role: UserRole = UserRole.MEMBER
    is_active: bool = True
    is_blocked: bool = False


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    role: UserRole = UserRole.MEMBER
    is_active: bool = True
    is_blocked: bool = False


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None
    is_blocked: Optional[bool] = None
    new_password: Optional[str] = None


class UserRead(UserBase):
    id: int

    class Config:
        from_attributes = True  # pydantic v2
