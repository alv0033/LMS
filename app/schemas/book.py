from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class BookBase(BaseModel):
    title: str
    author: Optional[str] = None
    isbn: str
    description: Optional[str] = None
    genre: Optional[str] = None
    publication_year: Optional[int] = None
    total_copies: int
    available_copies: int
    branch_id: int


class BookCreate(BaseModel):
    title: str
    author: Optional[str] = None
    isbn: str
    description: Optional[str] = None
    genre: Optional[str] = None
    publication_year: Optional[int] = None
    total_copies: int
    branch_id: int  # sucursal


class BookUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    isbn: Optional[str] = None
    description: Optional[str] = None
    genre: Optional[str] = None
    publication_year: Optional[int] = None
    total_copies: Optional[int] = None
    available_copies: Optional[int] = None
    branch_id: Optional[int] = None


class BookRead(BaseModel):
    id: int
    title: str
    author: Optional[str] = None
    isbn: str
    description: Optional[str] = None
    genre: Optional[str] = None
    publication_year: Optional[int] = None
    total_copies: int
    available_copies: int
    branch_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
