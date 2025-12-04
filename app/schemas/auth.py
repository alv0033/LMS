from pydantic import BaseModel, EmailStr
from uuid import UUID
from enum import Enum


class UserRole(str, Enum):
    MEMBER = "MEMBER"
    LIBRARIAN = "LIBRARIAN"
    ADMIN = "ADMIN"


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: int | None = None
    role: UserRole | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    