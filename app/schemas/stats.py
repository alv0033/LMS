from pydantic import BaseModel


class SystemStats(BaseModel):
    # Usuarios
    total_users: int
    total_members: int
    total_librarians: int
    total_admins: int

    # Sucursales
    total_branches: int
    active_branches: int

    # Libros / inventario
    total_books: int
    total_book_copies: int
    total_available_copies: int

    # Préstamos
    total_loans: int
    active_loans: int
    overdue_loans: int
    loans_last_30_days: int

    class Config:
        orm_mode = True
