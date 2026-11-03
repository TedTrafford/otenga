"""BI metadata persistence — all dashboards are stored in BI_DB_* and survive restarts."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal
from datetime import datetime
from typing import Optional

from sqlalchemy.orm.attributes import flag_modified

from .config import settings
from .database import SessionLocal
from .dashboard_date_filter import (
    get_date_column,
    get_default_preset,
    resolve_date_range,
    resolve_widget_sql,
    should_apply_date_filter,
)
from .execution_engine import execute_sql_sync
from .dashboard_widgets import build_figure, build_stacked_bar, clean_rows
from .models import Dashboard


def _format_metric(val):
    if val is None:
        return "—"
    if isinstance(val, Decimal):
        val = float(val)
    if isinstance(val, float) and val.is_integer():
        val = int(val)
    if isinstance(val, int):
        return f"{val:,}"
    return str(val)


def _infer_series_col(widget: dict, columns: list) -> Optional[str]:
    series_col = widget.get("seriesCol")
    if series_col:
        return series_col
    for candidate in (
        "fraud_decision",
        "decision",
        "status",
        "reason_code",
        "risk_segment",
        "credit_outcome",
    ):
        if candidate in columns:
            return candidate
    return None


def _rebuild_chart_figure(widget: dict, rows: list, columns: list) -> Optional[dict]:
    chart_type = widget.get("chartType") or "bar"
    x_col = widget.get("xCol")
    y_cols = widget.get("yCols") or []
    title = widget.get("title") or ""

    if chart_type == "stacked_bar" and x_col and y_cols:
        series_col = _infer_series_col(widget, columns)
        if series_col:
            return build_stacked_bar(rows, x_col, series_col, y_cols[0])

    return build_figure(rows, x_col, y_cols, chart_type, title)


def _apply_query_result(widget: dict, template_sql: str, result: dict) -> dict:
    """Merge SQL execution result into a widget dict."""
    if not result.get("success"):
        return {**widget, "sql": template_sql}

    rows = clean_rows(result.get("data") or [])
    columns = result.get("columns") or (list(rows[0].keys()) if rows else [])
    updated = {**widget, "sql": template_sql, "rows": rows, "columns": columns}

    wtype = widget.get("type")
    if wtype == "metric" and rows:
        col = widget.get("metaCol") or (columns[0] if columns else None)
        if col:
            updated["value"] = _format_metric(rows[0].get(col))

    if wtype == "chart":
        try:
            fig = _rebuild_chart_figure(widget, rows, columns)
        except Exception:
            fig = widget.get("figData")
        if fig:
            updated["figData"] = fig

    return updated


def refresh_widget(
    widget: dict,
    *,
    date_column: Optional[str] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    use_date_filter: bool = True,
) -> dict:
    """Re-run widget SQL against MPESA_DB_* and update cached result fields."""
    template_sql, sql = resolve_widget_sql(
        widget,
        date_column=date_column,
        start=start,
        end=end,
        use_date_filter=use_date_filter,
    )
    if not template_sql or template_sql.startswith("--"):
        return widget

    result = execute_sql_sync(sql)
    return _apply_query_result(widget, template_sql, result)


def refresh_dashboard_data(
    dashboard: Dashboard,
    db,
    *,
    preset: Optional[str] = None,
    start_date=None,
    end_date=None,
) -> Dashboard:
    """Re-run all widget SQL against MPESA_DB_* and persist results."""
    use_filter = should_apply_date_filter(dashboard.name, dashboard.filters)
    date_column = None
    start = end = None
    if use_filter:
        date_column = get_date_column(dashboard.name, dashboard.filters)
        if not preset:
            preset = get_default_preset(dashboard.name, dashboard.filters)
        start, end = resolve_date_range(preset, start_date, end_date)

    widgets = dashboard.widgets or []
    refreshed = list(widgets)
    sql_groups: dict[str, list[tuple[int, dict, str]]] = {}

    for index, widget in enumerate(widgets):
        if not isinstance(widget, dict):
            continue
        template_sql, executable_sql = resolve_widget_sql(
            widget,
            date_column=date_column,
            start=start,
            end=end,
            use_date_filter=use_filter,
        )
        if not template_sql or template_sql.startswith("--"):
            continue
        sql_groups.setdefault(executable_sql, []).append((index, widget, template_sql))

    if sql_groups:
        workers = max(1, min(settings.DASHBOARD_REFRESH_WORKERS, len(sql_groups)))

        def _run_sql(sql: str):
            return execute_sql_sync(sql)

        with ThreadPoolExecutor(max_workers=workers) as pool:
            future_map = {pool.submit(_run_sql, sql): (sql, items) for sql, items in sql_groups.items()}
            for future in as_completed(future_map):
                sql, items = future_map[future]
                result = future.result()
                for index, widget, template_sql in items:
                    refreshed[index] = _apply_query_result(widget, template_sql, result)

    dashboard.widgets = refreshed
    flag_modified(dashboard, "widgets")
    db.commit()
    db.refresh(dashboard)
    return dashboard


def refresh_dashboard(dashboard: Dashboard, db) -> bool:
    """Refresh SQL-backed widgets for one dashboard and persist to BI metadata DB."""
    widgets = dashboard.widgets or []
    if not widgets:
        return False

    before = dashboard.widgets
    refresh_dashboard_data(dashboard, db)
    return dashboard.widgets != before


def ensure_bi_storage():
    """Verify BI metadata DB connectivity and report persisted dashboards."""
    db = SessionLocal()
    try:
        dashboards = db.query(Dashboard).order_by(Dashboard.id).all()
        names = ", ".join(d.name for d in dashboards) if dashboards else "(none yet)"
        print(
            f"✅ BI storage @ {settings.BI_DB_HOST}/{settings.BI_DB_NAME} — {len(dashboards)} dashboard(s): {names}"
        )
        return dashboards
    except Exception as exc:
        print(f"⚠️  BI storage check failed: {exc}")
        return []
    finally:
        db.close()


def refresh_persisted_dashboards():
    """Refresh widget data from MPESA_DB_* for every persisted dashboard."""
    db = SessionLocal()
    try:
        dashboards = db.query(Dashboard).order_by(Dashboard.id).all()
        if not dashboards:
            print("✅ Dashboard refresh: no dashboards to update")
            return

        refreshed = 0
        for i, dashboard in enumerate(dashboards, 1):
            try:
                print(f"   ↻ [{i}/{len(dashboards)}] {dashboard.name!r}...")
                if refresh_dashboard(dashboard, db):
                    refreshed += 1
            except Exception as exc:
                print(f"⚠️  Dashboard refresh skipped ({dashboard.name!r}): {exc}")

        print(
            f"✅ Dashboard data refreshed from data DB "
            f"({refreshed}/{len(dashboards)} updated, {len(dashboards)} persisted)"
        )
    except Exception as exc:
        print(f"⚠️  Dashboard refresh skipped: {exc}")
    finally:
        db.close()
