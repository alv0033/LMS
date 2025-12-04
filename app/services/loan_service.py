from datetime import datetime, timedelta, timezone, date
from sqlalchemy.orm import Session

from app.db.models import Loan, LoanStatus, LoanStatusHistory, Book, User

LATE_FEE_PER_DAY = 1.0  # Multa por retraso,


def calculate_late_fee(loan: Loan) -> float:
    """Calcula la multa basada en días de atraso."""
    if not loan.due_date:
        return 0.0

    # Normalizamos a tipo date
    if isinstance(loan.due_date, datetime):
        due_date = loan.due_date.date()
    elif isinstance(loan.due_date, date):
        due_date = loan.due_date
    else:
        return 0.0

    today = datetime.now(timezone.utc).date()

    if today <= due_date:
        return 0.0

    days_overdue = (today - due_date).days
    return float(days_overdue * LATE_FEE_PER_DAY)


def add_status_history(
    db: Session,
    loan: Loan,
    old_status: LoanStatus | None,
    new_status: LoanStatus,
    changed_by: User | None,
    note: str | None = None,
):
    history = LoanStatusHistory(
        loan_id=loan.id,
        old_status=old_status,
        new_status=new_status,
        changed_by_user_id=changed_by.id if changed_by else None,
        note=note,
    )
    db.add(history)


def change_loan_status(
    db: Session,
    loan: Loan,
    new_status: LoanStatus,
    actor: User | None,
    note: str | None = None,
):
    old_status = loan.status

    # Reglas del flujo de estados (simplificadas)
    allowed_transitions: dict[LoanStatus, set[LoanStatus]] = {
        LoanStatus.REQUESTED: {LoanStatus.CANCELED, LoanStatus.APPROVED},
        LoanStatus.APPROVED: {LoanStatus.BORROWED, LoanStatus.CANCELED},
        LoanStatus.BORROWED: {LoanStatus.RETURNED, LoanStatus.LOST, LoanStatus.OVERDUE},
        LoanStatus.OVERDUE: {LoanStatus.RETURNED, LoanStatus.LOST},
        LoanStatus.RETURNED: set(),
        LoanStatus.LOST: set(),
        LoanStatus.CANCELED: set(),
    }

    if new_status not in allowed_transitions[old_status]:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status transition from {old_status} to {new_status}",
        )

    # Efectos secundarios sobre copias
    book: Book = loan.book

    # BORROWED: restar una copia disponible
    if old_status in {LoanStatus.APPROVED, LoanStatus.REQUESTED} and new_status == LoanStatus.BORROWED:
        if book.available_copies <= 0:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No available copies for this book",
            )
        book.available_copies -= 1

    # RETURNED: sumar una copia disponible
    if new_status == LoanStatus.RETURNED and old_status in {LoanStatus.BORROWED, LoanStatus.OVERDUE}:
        book.available_copies += 1
        loan.return_date = datetime.now(timezone.utc)

    # OVERDUE: calcular multa
    if new_status == LoanStatus.OVERDUE:
        loan.late_fee_amount = calculate_late_fee(loan)

    loan.notes = note
    loan.status = new_status
    add_status_history(db, loan, old_status, new_status, actor, note)
    db.commit()
    db.refresh(loan)
    db.refresh(book)
    return loan


def mark_overdue_loans(db: Session) -> int:
    """
    Marca automáticamente como OVERDUE todos los préstamos BORROWED cuya due_date ya pasó.
    Devuelve el número de préstamos actualizados.
    Esta función está pensada para ser llamada por un job del sistema (cron, scheduler, endpoint admin, etc.).
    """
    today = datetime.now(timezone.utc).date()

    # Préstamos que deberían estar overdue
    loans_q = (
        db.query(Loan)
        .filter(Loan.status == LoanStatus.BORROWED)
        .filter(Loan.due_date < today)
    )

    updated_count = 0

    for loan in loans_q:
        # Calcula multa al momento de cambiar estado
        change_loan_status(
            db=db,
            loan=loan,
            new_status=LoanStatus.OVERDUE,
            actor=None,  # actor=None => cambio automático del sistema
            note="Automatic overdue job",
        )
        updated_count += 1

    return updated_count
