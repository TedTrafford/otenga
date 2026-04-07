from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from typing import List
from ..database import get_db
from ..auth import get_current_active_user, require_role
from ..models import User, Dashboard, UserRole, NotebookStatus, AuditLog
from ..schemas import DashboardCreate, DashboardUpdate, DashboardOut

router = APIRouter()


@router.get("/", response_model=List[DashboardOut])
async def list_dashboards(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role == UserRole.viewer:
        # Viewers only see published dashboards
        return db.query(Dashboard).filter(Dashboard.status == NotebookStatus.published).all()
    return db.query(Dashboard).all()


@router.post("/", response_model=DashboardOut, status_code=status.HTTP_201_CREATED)
async def create_dashboard(
    data: DashboardCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.creator, UserRole.superuser)),
):
    dashboard = Dashboard(
        name=data.name,
        description=data.description,
        notebook_id=data.notebook_id,
        layout=data.layout or [],
        widgets=data.widgets or [],
        filters=data.filters or [],
        status=NotebookStatus.draft,
    )
    db.add(dashboard)
    db.commit()
    db.refresh(dashboard)

    log = AuditLog(
        user_id=current_user.id, action="create_dashboard",
        resource_type="dashboard", resource_id=dashboard.id,
    )
    db.add(log)
    db.commit()
    return dashboard


@router.get("/pending", response_model=List[DashboardOut])
async def list_pending_dashboards(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.superuser)),
):
    """Return dashboards awaiting superuser approval."""
    return (
        db.query(Dashboard)
        .filter(Dashboard.status == NotebookStatus.pending_approval)
        .all()
    )


@router.get("/{dashboard_id}", response_model=DashboardOut)
async def get_dashboard(
    dashboard_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    dashboard = db.query(Dashboard).filter(Dashboard.id == dashboard_id).first()
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    if current_user.role == UserRole.viewer and dashboard.status != NotebookStatus.published:
        raise HTTPException(status_code=403, detail="Dashboard not published")
    return dashboard


@router.put("/{dashboard_id}", response_model=DashboardOut)
async def update_dashboard(
    dashboard_id: int,
    data: DashboardUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.creator, UserRole.superuser)),
):
    dashboard = db.query(Dashboard).filter(Dashboard.id == dashboard_id).first()
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(dashboard, field, value)
        # JSON columns need explicit dirty-marking so SQLAlchemy doesn't skip the UPDATE
        if field in ("widgets", "layout", "filters"):
            flag_modified(dashboard, field)

    db.commit()
    db.refresh(dashboard)
    return dashboard


@router.delete("/{dashboard_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dashboard(
    dashboard_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.creator, UserRole.superuser)),
):
    dashboard = db.query(Dashboard).filter(Dashboard.id == dashboard_id).first()
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    db.delete(dashboard)
    db.commit()


@router.post("/{dashboard_id}/submit", response_model=DashboardOut)
async def submit_dashboard_for_review(
    dashboard_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.creator, UserRole.superuser)),
):
    """Creator submits a draft dashboard for superuser review."""
    dashboard = db.query(Dashboard).filter(Dashboard.id == dashboard_id).first()
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    if dashboard.status == NotebookStatus.published:
        raise HTTPException(status_code=400, detail="Dashboard is already published")
    if dashboard.status == NotebookStatus.pending_approval:
        raise HTTPException(status_code=400, detail="Dashboard is already submitted for review")

    dashboard.status = NotebookStatus.pending_approval
    log = AuditLog(
        user_id=current_user.id, action="submit_dashboard_for_review",
        resource_type="dashboard", resource_id=dashboard.id,
    )
    db.add(log)
    db.commit()
    db.refresh(dashboard)
    return dashboard


@router.post("/{dashboard_id}/publish", response_model=DashboardOut)
async def publish_dashboard(
    dashboard_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.superuser)),
):
    """Superuser approves and publishes a dashboard so all users can see it."""
    dashboard = db.query(Dashboard).filter(Dashboard.id == dashboard_id).first()
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    dashboard.status = NotebookStatus.published
    log = AuditLog(
        user_id=current_user.id, action="publish_dashboard",
        resource_type="dashboard", resource_id=dashboard.id,
    )
    db.add(log)
    db.commit()
    db.refresh(dashboard)
    return dashboard


@router.post("/{dashboard_id}/unpublish", response_model=DashboardOut)
async def unpublish_dashboard(
    dashboard_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.superuser)),
):
    """Superuser reverts a published dashboard back to draft."""
    dashboard = db.query(Dashboard).filter(Dashboard.id == dashboard_id).first()
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    dashboard.status = NotebookStatus.draft
    db.commit()
    db.refresh(dashboard)
    return dashboard
