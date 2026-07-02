from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from typing import List, Optional
from datetime import date
from ..database import get_db
from ..auth import get_current_active_user, require_role
from ..models import User, Dashboard, UserRole, NotebookStatus, AuditLog
from ..schemas import DashboardCreate, DashboardUpdate, DashboardOut, DashboardSummaryOut, DashboardRefreshRequest
from ..bi_storage import refresh_dashboard_data
from ..dashboard_export import export_widget_phones, widget_is_exportable

router = APIRouter()


@router.get("/", response_model=List[DashboardSummaryOut])
async def list_dashboards(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List dashboard metadata only — avoids sorting huge widget JSON blobs in MySQL."""
    query = db.query(
        Dashboard.id,
        Dashboard.name,
        Dashboard.description,
        Dashboard.status,
        Dashboard.created_at,
        Dashboard.updated_at,
    )
    if current_user.role == UserRole.viewer:
        query = query.filter(Dashboard.status == NotebookStatus.published)
    # Order by id (not updated_at) — MySQL runs out of sort memory when sorting wide JSON rows.
    rows = query.order_by(Dashboard.id.desc()).all()

    count_rows = db.execute(
        text("SELECT id, COALESCE(JSON_LENGTH(widgets), 0) AS widget_count FROM dashboards")
    ).all()
    widget_counts = {r.id: int(r.widget_count or 0) for r in count_rows}

    return [
        DashboardSummaryOut(
            id=r.id,
            name=r.name,
            description=r.description,
            status=r.status,
            widget_count=widget_counts.get(r.id, 0),
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in rows
    ]


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


@router.get("/pending", response_model=List[DashboardSummaryOut])
async def list_pending_dashboards(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.superuser)),
):
    """Return dashboards awaiting superuser approval (metadata only)."""
    rows = (
        db.query(
            Dashboard.id,
            Dashboard.name,
            Dashboard.description,
            Dashboard.status,
            Dashboard.created_at,
            Dashboard.updated_at,
        )
        .filter(Dashboard.status == NotebookStatus.pending_approval)
        .order_by(Dashboard.id.desc())
        .all()
    )
    count_rows = db.execute(
        text(
            "SELECT id, COALESCE(JSON_LENGTH(widgets), 0) AS widget_count "
            "FROM dashboards WHERE status = 'pending_approval'"
        )
    ).all()
    widget_counts = {r.id: int(r.widget_count or 0) for r in count_rows}
    return [
        DashboardSummaryOut(
            id=r.id,
            name=r.name,
            description=r.description,
            status=r.status,
            widget_count=widget_counts.get(r.id, 0),
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in rows
    ]


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


@router.post("/{dashboard_id}/refresh", response_model=DashboardOut)
async def refresh_dashboard_endpoint(
    dashboard_id: int,
    body: DashboardRefreshRequest = DashboardRefreshRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Re-query MPESA_DB_* for every widget when a dashboard is opened or filtered."""
    dashboard = db.query(Dashboard).filter(Dashboard.id == dashboard_id).first()
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    if current_user.role == UserRole.viewer and dashboard.status != NotebookStatus.published:
        raise HTTPException(status_code=403, detail="Dashboard not published")
    try:
        refresh_dashboard_data(
            dashboard,
            db,
            preset=body.preset,
            start_date=body.start_date,
            end_date=body.end_date,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Dashboard refresh failed: {exc}") from exc
    return dashboard


@router.get("/{dashboard_id}/widgets/{widget_id}/export")
async def export_widget_customers(
    dashboard_id: int,
    widget_id: str,
    preset: str = "yesterday",
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    segment: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Download labelled CSV data for a dashboard widget."""
    dashboard = db.query(Dashboard).filter(Dashboard.id == dashboard_id).first()
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    if current_user.role == UserRole.viewer and dashboard.status != NotebookStatus.published:
        raise HTTPException(status_code=403, detail="Dashboard not published")

    widget = next(
        (w for w in (dashboard.widgets or []) if isinstance(w, dict) and w.get("id") == widget_id),
        None,
    )
    if not widget:
        raise HTTPException(status_code=404, detail="Widget not found")
    if not widget_is_exportable(widget):
        raise HTTPException(status_code=400, detail="This widget does not support export")

    try:
        csv_bytes, filename = export_widget_phones(
            dashboard,
            widget,
            preset=preset,
            start_date=start_date,
            end_date=end_date,
            segment=segment,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Export failed: {exc}") from exc

    log = AuditLog(
        user_id=current_user.id,
        action="export_widget_phones",
        resource_type="dashboard",
        resource_id=dashboard.id,
        details={"widget_id": widget_id, "segment": segment, "preset": preset},
    )
    db.add(log)
    db.commit()

    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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
