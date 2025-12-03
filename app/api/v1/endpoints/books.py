from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.v1.dependencies import get_db
from app.api.v1.dependencies_auth import get_current_user, require_role
from app.db.models import Book, LibraryBranch, User, UserRole
from app.schemas.book import BookCreate, BookUpdate, BookRead

router = APIRouter(
    prefix="/api/v1/books",
    tags=["books"],
)


@router.get("/", response_model=List[BookRead])
def list_books(
    title: Optional[str] = Query(None),
    author: Optional[str] = Query(None),
    isbn: Optional[str] = Query(None),
    branch_id: Optional[int] = Query(None),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Book)

    if title:
        query = query.filter(Book.title.ilike(f"%{title}%"))
    if author:
        query = query.filter(Book.author.ilike(f"%{author}%"))
    if isbn:
        query = query.filter(Book.isbn == isbn)
    if branch_id:
        query = query.filter(Book.branch_id == branch_id)

    books = query.offset(skip).limit(limit).all()
    return books


@router.post(
    "/",
    response_model=BookRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.LIBRARIAN))],
)
def create_book(
    payload: BookCreate,
    db: Session = Depends(get_db),
):
    # Validar que la sucursal exista
    branch = db.query(LibraryBranch).filter(LibraryBranch.id == payload.branch_id).first()
    if not branch:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Branch not found",
        )

    book = Book(
        title=payload.title,
        author=payload.author,
        isbn=payload.isbn,
        description=payload.description,
        genre=payload.genre,
        publication_year=payload.publication_year,
        total_copies=payload.total_copies,
        available_copies=payload.total_copies,  # al inicio, todas disponibles
        branch_id=payload.branch_id,
    )

    db.add(book)
    db.commit()
    db.refresh(book)
    return book


@router.get("/{book_id}", response_model=BookRead)
def get_book(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found",
        )
    return book


@router.put(
    "/{book_id}",
    response_model=BookRead,
    dependencies=[Depends(require_role(UserRole.LIBRARIAN))],
)
def update_book(
    book_id: int,
    payload: BookUpdate,
    db: Session = Depends(get_db),
):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found",
        )

    update_data = payload.model_dump(exclude_unset=True)

    # si se actualiza total_copies y no se da available_copies, puedes decidir lógica aquí;
    # por ahora, solo asignamos lo que venga en el payload.
    for field, value in update_data.items():
        setattr(book, field, value)

    db.commit()
    db.refresh(book)
    return book


@router.delete(
    "/{book_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
def delete_book(
    book_id: int,
    db: Session = Depends(get_db),
):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found",
        )

    db.delete(book)
    db.commit()
    return None
