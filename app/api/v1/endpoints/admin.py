# app/api/v1/endpoints/admin.py
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func


from app.api.v1.dependencies import get_db
from app.api.v1.dependencies_auth import (get_current_user,require_role,)
from app.core.logging import get_logger, user_id_ctx
from app.db.models import User, LibraryBranch, Book, Loan, LoanStatus, UserRole
from app.schemas.admin import AdminStats, LoanStatusCount
from app.schemas.stats import SystemStats

import logging

logger = get_logger("api.admin")

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
)


def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user


@router.get("/stats", response_model=SystemStats, dependencies=[Depends(require_role(UserRole.ADMIN))])
def get_system_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Endpoint de estadísticas globales del sistema (solo ADMIN).
    """

    # === Usuarios ===
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_members = db.query(func.count(User.id)).filter(User.role == UserRole.MEMBER).scalar() or 0
    total_librarians = db.query(func.count(User.id)).filter(User.role == UserRole.LIBRARIAN).scalar() or 0
    total_admins = db.query(func.count(User.id)).filter(User.role == UserRole.ADMIN).scalar() or 0

    # === Sucursales ===
    total_branches = db.query(func.count(LibraryBranch.id)).scalar() or 0
    active_branches = db.query(func.count(LibraryBranch.id)).filter(LibraryBranch.is_active == True).scalar() or 0

    # === Libros / Inventario ===
    total_books = db.query(func.count(Book.id)).scalar() or 0
    total_book_copies = db.query(func.coalesce(func.sum(Book.total_copies), 0)).scalar() or 0
    total_available_copies = db.query(func.coalesce(func.sum(Book.available_copies), 0)).scalar() or 0

    # === Préstamos ===
    total_loans = db.query(func.count(Loan.id)).scalar() or 0

    active_statuses = [
        LoanStatus.REQUESTED,
        LoanStatus.APPROVED,
        LoanStatus.BORROWED,
        LoanStatus.OVERDUE,
    ]
    active_loans = (
        db.query(func.count(Loan.id))
        .filter(Loan.status.in_(active_statuses))
        .scalar()
        or 0
    )

    overdue_loans = (
        db.query(func.count(Loan.id))
        .filter(Loan.status == LoanStatus.OVERDUE)
        .scalar()
        or 0
    )

    now = datetime.now(timezone.utc)
    last_30_days = now - timedelta(days=30)
    loans_last_30_days = (
        db.query(func.count(Loan.id))
        .filter(Loan.created_at >= last_30_days)
        .scalar()
        or 0
    )

    stats = SystemStats(
        total_users=total_users,
        total_members=total_members,
        total_librarians=total_librarians,
        total_admins=total_admins,
        total_branches=total_branches,
        active_branches=active_branches,
        total_books=total_books,
        total_book_copies=total_book_copies,
        total_available_copies=total_available_copies,
        total_loans=total_loans,
        active_loans=active_loans,
        overdue_loans=overdue_loans,
        loans_last_30_days=loans_last_30_days,
    )

    # LOG: acción administrativa
    # (el middleware ya mete request_id y user_id_ctx, pero aquí reforzamos)
    logger.info(
        "Admin fetched system stats",
        extra={
            "operation": "admin_stats",
            "resource": "stats",
            "user_id": current_user.id,
        },
    )

    return stats
