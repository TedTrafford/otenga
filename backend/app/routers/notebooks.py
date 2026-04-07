from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..auth import get_current_active_user, require_role
from ..models import User, Notebook, UserRole, NotebookStatus, AuditLog
from ..schemas import NotebookCreate, NotebookUpdate, NotebookOut

router = APIRouter()


@router.get("/", response_model=List[NotebookOut])
async def list_notebooks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role == UserRole.viewer:
        notebooks = db.query(Notebook).filter(Notebook.status == NotebookStatus.published).all()
    elif current_user.role == UserRole.creator:
        notebooks = db.query(Notebook).filter(Notebook.owner_id == current_user.id).all()
    else:
        notebooks = db.query(Notebook).all()
    return notebooks


@router.post("/", response_model=NotebookOut, status_code=status.HTTP_201_CREATED)
async def create_notebook(
    data: NotebookCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.creator, UserRole.superuser)),
):
    notebook = Notebook(
        name=data.name,
        description=data.description,
        owner_id=current_user.id,
        cells=[c.model_dump() for c in data.cells] if data.cells else [],
        tags=data.tags or [],
    )
    db.add(notebook)
    db.commit()
    db.refresh(notebook)

    log = AuditLog(user_id=current_user.id, action="create_notebook", resource_type="notebook", resource_id=notebook.id)
    db.add(log)
    db.commit()

    return notebook


@router.get("/{notebook_id}", response_model=NotebookOut)
async def get_notebook(
    notebook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    notebook = db.query(Notebook).filter(Notebook.id == notebook_id).first()
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")

    if current_user.role == UserRole.viewer and notebook.status != NotebookStatus.published:
        raise HTTPException(status_code=403, detail="Notebook not published")

    if current_user.role == UserRole.creator and notebook.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return notebook


@router.put("/{notebook_id}", response_model=NotebookOut)
async def update_notebook(
    notebook_id: int,
    data: NotebookUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.creator, UserRole.superuser)),
):
    notebook = db.query(Notebook).filter(Notebook.id == notebook_id).first()
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")

    if current_user.role == UserRole.creator and notebook.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(notebook, field, value)

    db.commit()
    db.refresh(notebook)

    log = AuditLog(user_id=current_user.id, action="update_notebook", resource_type="notebook", resource_id=notebook.id)
    db.add(log)
    db.commit()

    return notebook


@router.delete("/{notebook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notebook(
    notebook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.creator, UserRole.superuser)),
):
    notebook = db.query(Notebook).filter(Notebook.id == notebook_id).first()
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")

    if current_user.role == UserRole.creator and notebook.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    db.delete(notebook)
    db.commit()


@router.post("/{notebook_id}/publish")
async def publish_notebook(
    notebook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.creator, UserRole.superuser)),
):
    notebook = db.query(Notebook).filter(Notebook.id == notebook_id).first()
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")

    if current_user.role == UserRole.superuser:
        notebook.status = NotebookStatus.published
    else:
        notebook.status = NotebookStatus.pending_approval

    db.commit()

    log = AuditLog(
        user_id=current_user.id,
        action="publish_notebook",
        resource_type="notebook",
        resource_id=notebook.id,
        details={"new_status": notebook.status.value},
    )
    db.add(log)
    db.commit()

    return {"message": f"Notebook status updated to {notebook.status.value}", "status": notebook.status.value}


@router.post("/{notebook_id}/approve")
async def approve_notebook(
    notebook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.superuser)),
):
    notebook = db.query(Notebook).filter(Notebook.id == notebook_id).first()
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")

    notebook.status = NotebookStatus.published
    db.commit()

    log = AuditLog(user_id=current_user.id, action="approve_notebook", resource_type="notebook", resource_id=notebook.id)
    db.add(log)
    db.commit()

    return {"message": "Notebook approved and published"}
