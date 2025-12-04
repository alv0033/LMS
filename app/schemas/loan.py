from datetime import datetime, date
from typing import Optional, List
from enum import Enum

from pydantic import BaseModel


class LoanStatus(str, Enum):
    REQUESTED = "REQUESTED"
    CANCELED = "CANCELED"
    APPROVED = "APPROVED"
    BORROWED = "BORROWED"
    OVERDUE = "OVERDUE"
    RETURNED = "RETURNED"
    LOST = "LOST"


class LoanBase(BaseModel):
    book_id: int
    branch_id: int


class LoanCreate(BaseModel):
    book_id: int
    branch_id: int


class LoanStatusChange(BaseModel):
    new_status: LoanStatus
    note: Optional[str] = None


class LoanRead(BaseModel):
    id: int
    member_id: int
    book_id: int
    branch_id: int
    borrow_date: datetime
    due_date: datetime
    return_date: Optional[datetime]
    status: LoanStatus
    late_fee_amount: Optional[float]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LoanStatusHistoryRead(BaseModel):
    id: int
    loan_id: int
    old_status: Optional[LoanStatus]
    new_status: LoanStatus
    changed_by_user_id: Optional[int]
    changed_at: datetime
    note: Optional[str]

    class Config:
        from_attributes = True


class LoanWithHistoryRead(LoanRead):
    status_history: List[LoanStatusHistoryRead] = []
