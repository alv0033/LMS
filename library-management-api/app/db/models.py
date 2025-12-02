from datetime import datetime, timedelta
from enum import Enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Numeric,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.db.session import Base
from sqlalchemy.sql import func


# ======================
# Enums
# ======================

class UserRole(str, Enum):
    MEMBER = "member"
    LIBRARIAN = "librarian"
    ADMIN = "admin"


class LoanStatus(str, Enum):
    REQUESTED = "requested"
    CANCELED = "canceled"
    APPROVED = "approved"
    BORROWED = "borrowed"
    OVERDUE = "overdue"
    RETURNED = "returned"
    LOST = "lost"


# ======================
# User
# ======================

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    role: Mapped[UserRole] = mapped_column(SqlEnum(UserRole), nullable=False, default=UserRole.MEMBER)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    loans: Mapped[list["Loan"]] = relationship("Loan", back_populates="member")


# ======================
# LibraryBranch
# ======================

class LibraryBranch(Base):
    __tablename__ = "library_branches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    books: Mapped[list["Book"]] = relationship("Book", back_populates="branch")
    loans: Mapped[list["Loan"]] = relationship("Loan", back_populates="branch")


# ======================
# Book
# ======================

class Book(Base):
    __tablename__ = "books"
    __table_args__ = (
        UniqueConstraint("isbn", name="uq_books_isbn"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    isbn: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    genre: Mapped[str | None] = mapped_column(String(100), nullable=True)
    publication_year: Mapped[int | None] = mapped_column(Integer, nullable=True)

    total_copies: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    available_copies: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    branch_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("library_branches.id", ondelete="RESTRICT"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    branch: Mapped["LibraryBranch"] = relationship("LibraryBranch", back_populates="books")
    loans: Mapped[list["Loan"]] = relationship("Loan", back_populates="book")


# ======================
# Loan
# ======================

class Loan(Base):
    __tablename__ = "loans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    member_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    book_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("books.id", ondelete="RESTRICT"),
        nullable=False,
    )

    branch_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("library_branches.id", ondelete="RESTRICT"),
        nullable=False,
    )

    borrow_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    due_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    return_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    status: Mapped[LoanStatus] = mapped_column(
        SqlEnum(LoanStatus),
        nullable=False,
        default=LoanStatus.REQUESTED,
    )

    late_fee_amount: Mapped[Numeric | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        default=0,
    )

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    member: Mapped["User"] = relationship("User", back_populates="loans")
    book: Mapped["Book"] = relationship("Book", back_populates="loans")
    branch: Mapped["LibraryBranch"] = relationship("LibraryBranch", back_populates="loans")
    history: Mapped[list["LoanStatusHistory"]] = relationship(
        "LoanStatusHistory",
        back_populates="loan",
        cascade="all, delete-orphan",
    )


# ======================
# LoanStatusHistory
# ======================

class LoanStatusHistory(Base):
    __tablename__ = "loan_status_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    loan_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("loans.id", ondelete="CASCADE"),
        nullable=False,
    )

    old_status: Mapped[LoanStatus | None] = mapped_column(
        SqlEnum(LoanStatus),
        nullable=True,
    )
    new_status: Mapped[LoanStatus] = mapped_column(
        SqlEnum(LoanStatus),
        nullable=False,
    )

    changed_by_user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    loan: Mapped["Loan"] = relationship("Loan", back_populates="history")
