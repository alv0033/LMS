from typing import List, Optional
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.v1.dependencies import get_db
from app.api.v1.dependencies_auth import get_current_user, require_role
from app.db.models import Loan, Book, LibraryBranch, User, UserRole
from app.schemas.loan import (
    LoanCreate,
    LoanRead,
    LoanWithHistoryRead,
    LoanStatusChange,
    LoanStatus,
)
from app.services.loan_service import (
    change_loan_status,
    calculate_late_fee,
    mark_overdue_loans,  # <- NUEVO IMPORT
)

import logging

logger = logging.getLogger("api.loans")


router = APIRouter(
    prefix="/api/v1/loans",
    tags=["loans"],
)


# ---- Crear préstamo (Member) ----
@router.post(
    "/",
    response_model=LoanRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.MEMBER))],
)
def create_loan_request(
    payload: LoanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Validar book
    book = db.query(Book).filter(Book.id == payload.book_id).first()
    if not book:
        raise HTTPException(status_code=400, detail="Book not found")

    # validar branch
    branch = db.query(LibraryBranch).filter(LibraryBranch.id == payload.branch_id).first()
    if not branch:
        raise HTTPException(status_code=400, detail="Branch not found")

    # Regla: no más de 5 préstamos activos
    active_statuses = [
        LoanStatus.REQUESTED,
        LoanStatus.APPROVED,
        LoanStatus.BORROWED,
        LoanStatus.OVERDUE,
    ]
    active_loans_count = (
        db.query(Loan)
        .filter(Loan.member_id == current_user.id, Loan.status.in_(active_statuses))
        .count()
    )
    if active_loans_count >= 5:
        raise HTTPException(
            status_code=400,
            detail="You already have the maximum number of active loans",
        )

    # Verificar copias disponibles
    if book.available_copies < 1:
        # ESTA ES LA VALIDACIÓN QUE PREGUNTAS
        raise HTTPException(status_code=400, detail="No available copies for this book")

    # Crear el préstamo en estado REQUESTED
    now = datetime.now(timezone.utc)
    due = now + timedelta(days=14)

    loan = Loan(
        member_id=current_user.id,
        book_id=payload.book_id,
        branch_id=payload.branch_id,
        borrow_date=now,
        due_date=due,
        status=LoanStatus.REQUESTED,
        late_fee_amount=0,
    )
    db.add(loan)
    db.commit()
    db.refresh(loan)

    # LOG: creación del préstamo
    logger.info(
        "Loan requested",
        extra={
            "operation": "loan_create",
            "resource": "loan",
            "loan_id": loan.id,
            "book_id": loan.book_id,
            "branch_id": loan.branch_id,
            "status_code": 201,
            "old_status": None,                
            "new_status": loan.status.value,
        },
    )

    return loan


# ---- Listar préstamos (según rol) ----
@router.get("/", response_model=List[LoanRead])
def list_loans(
    status_filter: Optional[LoanStatus] = Query(None, alias="status"),
    member_id: Optional[int] = None,
    branch_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Loan)

    # --- Filtro por rol ---
    if current_user.role == UserRole.MEMBER:
        # El member solo ve SUS préstamos
        query = query.filter(Loan.member_id == current_user.id)

    elif current_user.role == UserRole.LIBRARIAN:
        # El librarian ve TODOS los préstamos,
        # pero si se manda branch_id, filtra por sucursal
        if branch_id is not None:
            query = query.filter(Loan.branch_id == branch_id)

    elif current_user.role == UserRole.ADMIN:
        # Admin ve todos; puede filtrar opcionalmente
        if member_id is not None:
            query = query.filter(Loan.member_id == member_id)
        if branch_id is not None:
            query = query.filter(Loan.branch_id == branch_id)

    # --- Filtro por status (opcional) ---
    if status_filter is not None:
        from app.db.models import LoanStatus as LoanStatusDB

        query = query.filter(Loan.status == LoanStatusDB(status_filter.value))

    loans = query.offset(skip).limit(limit).all()
    return loans


# ---- Historial del usuario actual ---- (importante debe ir antes de loan_id)
@router.get("/my-history", response_model=List[LoanRead])
def my_loan_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    loans = (
        db.query(Loan)
        .filter(Loan.member_id == current_user.id)
        .order_by(Loan.created_at.desc())
        .all()
    )
    return loans


# ---- Detalle de un préstamo ----
@router.get("/{loan_id}", response_model=LoanWithHistoryRead)
def get_loan(
    loan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    loan = db.query(Loan).filter(Loan.id == loan_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")

    if current_user.role == UserRole.MEMBER and loan.member_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    return loan


# ---- Cambio de estado ----
@router.patch("/{loan_id}/status", response_model=LoanRead)
def update_loan_status(
    loan_id: int,
    payload: LoanStatusChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    loan = db.query(Loan).filter(Loan.id == loan_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")

    # Validar permisos según rol y transición
    new_status = payload.new_status
    old_status = loan.status

    # Validar permisos según rol
    if current_user.role == UserRole.MEMBER:
        # Solo puede CANCELAR mientras está REQUESTED y sea suyo
        if loan.member_id != current_user.id:
            raise HTTPException(status_code=403, detail="Forbidden")
        if not (old_status == LoanStatus.REQUESTED and new_status == LoanStatus.CANCELED):
            raise HTTPException(
                status_code=403,
                detail="Members can only cancel requested loans",
            )

    elif current_user.role == UserRole.LIBRARIAN:
        # Librarian puede: APPROVED, BORROWED, RETURNED, LOST
        if new_status not in {
            LoanStatus.APPROVED,
            LoanStatus.BORROWED,
            LoanStatus.RETURNED,
            LoanStatus.LOST,
        }:
            raise HTTPException(
                status_code=403,
                detail="Invalid status for librarian",
            )

    elif current_user.role == UserRole.ADMIN:
        # Admin puede todo, dejamos pasar
        pass

    # Aplicar cambio de estado (esto también afecta copias disponibles, multas, etc.)
    updated_loan = change_loan_status(
        db=db,
        loan=loan,
        new_status=new_status,
        actor=current_user,
        note=payload.note,
    )

    # LOG: cambio de estado
    logger.info(
         "Loan status changed (operation=loan_status_change)",
        extra={
            "operation": "loan_status_change",
            "resource": "loan",
            "loan_id": updated_loan.id,
            "book_id": updated_loan.book_id,
            "branch_id": updated_loan.branch_id,
            "status_code": 200,
            "old_status": old_status.value,
            "new_status": new_status.value,
            "user_id": current_user.id,
        },
    )

    return updated_loan


# ---- Job manual para marcar OVERDUE (solo ADMIN) ----
@router.post(
    "/run-overdue-job",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
def run_overdue_job(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Ejecuta el job que:
    - Busca todos los préstamos BORROWED cuya due_date ya pasó.
    - Los marca como OVERDUE.
    - Calcula y asigna la multa correspondiente.
    """
    updated_count = mark_overdue_loans(db)

    logger.info(
        "Overdue job executed",
        extra={
            "operation": "loan_overdue_job",
            "resource": "loan",
            "updated_count": updated_count,
            "status_code": 200,
            "run_by_user_id": current_user.id,
        },
    )

    return {"updated_overdue_loans": updated_count}
