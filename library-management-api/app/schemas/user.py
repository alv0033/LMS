from uuid import UUID
from enum import Enum
from pydantic import BaseModel, EmailStr


class UserRole(str, Enum):
    MEMBER = "member"
    LIBRARIAN = "librarian"
    ADMIN = "admin"


class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role: UserRole = UserRole.MEMBER
    is_active: bool = True


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None


class UserRead(UserBase):
    id: UUID

    class Config:
        from_attributes = True  # pydantic v2
