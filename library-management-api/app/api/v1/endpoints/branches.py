from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.dependencies import get_db
from app.api.v1.dependencies_auth import get_current_user, require_role
from app.db.models import LibraryBranch, UserRole, User
from app.schemas.branch import BranchCreate, BranchUpdate, BranchRead

router = APIRouter(
    prefix="/api/v1/branches",
    tags=["branches"],
)

@router.get(
    "/",
    response_model=List[BranchRead]
)
def list_branches(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(LibraryBranch).all()


@router.post(
    "/",
    response_model=BranchRead,
    status_code=status.HTTP_201_CREATED,
)
def create_branch(
    payload: BranchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # 👈 Swagger detecta seguridad aquí
):

    # Verificar rol manualmente
    if current_user.role not in [UserRole.LIBRARIAN, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    branch = LibraryBranch(**payload.model_dump())
    db.add(branch)
    db.commit()
    db.refresh(branch)
    return branch


@router.get(
    "/{branch_id}",
    response_model=BranchRead
)
def get_branch(
    branch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    branch = db.query(LibraryBranch).filter(LibraryBranch.id == branch_id).first()

    if not branch:
        raise HTTPException(404, "Branch not found")

    return branch


@router.put(
    "/{branch_id}",
    response_model=BranchRead,
)
def update_branch(
    branch_id: int,
    payload: BranchUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # 👈 seguridad real
):

    if current_user.role not in [UserRole.LIBRARIAN, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    branch = db.query(LibraryBranch).filter(LibraryBranch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(branch, field, value)

    db.commit()
    db.refresh(branch)
    return branch



@router.delete(
    "/{branch_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_branch(
    branch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admins only")

    branch = db.query(LibraryBranch).filter(LibraryBranch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")

    db.delete(branch)
    db.commit()
    return None


