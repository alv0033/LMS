# app/schemas/admin.py

from datetime import datetime
from typing import List

from pydantic import BaseModel


class LoanStatusCount(BaseModel):
    status: str
    count: int


class AdminStats(BaseModel):
    total_users: int
    total_members: int
    total_librarians: int
    total_admins: int

    total_branches: int
    total_books: int

    total_loans: int
    active_loans: int
    overdue_loans: int

    loans_by_status: List[LoanStatusCount]

    generated_at: datetime
