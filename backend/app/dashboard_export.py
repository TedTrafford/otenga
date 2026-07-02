"""Export dashboard widget data as labelled CSV files."""

import csv
import io
import re
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from .dashboard_date_filter import (
    get_date_column,
    resolve_date_range,
    resolve_widget_sql,
    should_apply_date_filter,
)
from .dashboard_export_queries import (
    COLUMN_LABELS,
    PHONES_ONLY_WIDGETS,
    WIDGET_EXPORT_LABELS,
    WIDGET_EXPORT_REGISTRY,
    WIDGET_EXPORT_SEGMENT_COLS,
)
from .dashboard_widgets import clean_rows
from .execution_engine import execute_sql_sync
from .models import Dashboard

PHONE_COLUMN_NAMES = ("mobile_number", "phone_number", "supplied_phone_number", "extracted_phone_number")
SEGMENT_FILTER_PLACEHOLDER = "{{segment_filter}}"
_LIMIT_RE = re.compile(r"\s+LIMIT\s+\d+\s*$", re.IGNORECASE)

PRESET_LABELS = {
    "yesterday": "Yesterday",
    "7d": "Last 7 days",
    "30d": "Last 30 days",
    "180d": "Last 6 months",
    "365d": "Last year",
    "custom": "Custom range",
}


def find_phone_column(columns: list) -> Optional[str]:
    if not columns:
        return None
    lower_map = {c.lower(): c for c in columns}
    for name in PHONE_COLUMN_NAMES:
        if name in lower_map:
            return lower_map[name]
    return None


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", (text or "").lower()).strip("-")
    return slug or "export"


def _escape_sql_literal(value: str) -> str:
    return value.replace("'", "''")


def _build_segment_filter(widget: dict, segment: Optional[str]) -> str:
    if not segment:
        return ""
    segment_col = (
        widget.get("exportSegmentCol")
        or WIDGET_EXPORT_SEGMENT_COLS.get(widget.get("id") or "")
        or widget.get("xCol")
    )
    if not segment_col:
        return ""
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_.]*$", segment_col):
        return ""
    return f"AND {segment_col} = '{_escape_sql_literal(segment)}'"


def _table_export_sql(sql: str) -> str:
    """Return full table query without row cap."""
    base = sql.strip().rstrip(";")
    return _LIMIT_RE.sub("", base)


def _export_mode(widget: dict) -> str:
    if widget.get("exportMode") == "phones":
        return "phones"
    if widget.get("exportMode") == "detail":
        return "detail"
    if widget.get("type") == "table":
        return "detail"
    wid = widget.get("id") or ""
    if wid in PHONES_ONLY_WIDGETS:
        return "phones"
    return "detail"


def resolve_export_sql(widget: dict, segment: Optional[str] = None) -> Optional[str]:
    """Return export SQL template for a widget, or None if not exportable."""
    mode = _export_mode(widget)
    template = widget.get("exportSql") or WIDGET_EXPORT_REGISTRY.get(widget.get("id"))

    if not template:
        if widget.get("type") == "table" and (widget.get("sql") or "").strip():
            template = _table_export_sql(widget["sql"])
        else:
            return None
    elif mode == "detail" and widget.get("type") == "table" and not widget.get("exportSql"):
        template = _table_export_sql(widget.get("sql") or template)

    segment_filter = _build_segment_filter(widget, segment)
    return template.replace(SEGMENT_FILTER_PLACEHOLDER, segment_filter)


def widget_is_exportable(widget: dict) -> bool:
    if not isinstance(widget, dict):
        return False
    if widget.get("exportSql") or widget.get("id") in WIDGET_EXPORT_REGISTRY:
        return True
    if widget.get("type") == "table":
        phone_col = find_phone_column(widget.get("columns") or [])
        return phone_col is not None and bool(widget.get("sql"))
    return False


def _format_period_label(
    preset: str,
    start_date: Optional[date],
    end_date: Optional[date],
    start: Optional[datetime],
    end: Optional[datetime],
) -> str:
    label = PRESET_LABELS.get(preset, preset)
    if preset == "custom" and start_date and end_date:
        return f"{label} ({start_date} to {end_date})"
    if preset == "yesterday" and start:
        return f"{label} ({start.date()})"
    if start and end and preset in {"7d", "30d", "180d", "365d"}:
        end_day = end.date()
        if end.time() == end.time().replace(hour=0, minute=0, second=0, microsecond=0):
            end_day = end.date() - timedelta(days=1)
        return f"{label} ({start.date()} to {end_day})"
    return label


def _format_cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if hasattr(value, "isoformat"):
        return value.isoformat(sep=" ", timespec="seconds")
    return str(value)


def _label_column(column: str) -> str:
    return COLUMN_LABELS.get(column, column.replace("_", " ").title())


def _build_filename(
    dashboard: Dashboard,
    widget: dict,
    preset: str,
    start_date: Optional[date],
    end_date: Optional[date],
    start: Optional[datetime],
) -> str:
    dash_slug = _slugify(dashboard.name)
    wid = widget.get("id") or ""
    widget_slug = WIDGET_EXPORT_LABELS.get(wid) or _slugify(widget.get("title") or wid)
    if preset == "yesterday" and start:
        period_slug = str(start.date())
    elif preset == "custom" and start_date and end_date:
        period_slug = f"{start_date}-to-{end_date}"
    else:
        period_slug = preset
    return f"{dash_slug}_{widget_slug}_{period_slug}.csv"


def export_widget_phones(
    dashboard: Dashboard,
    widget: dict,
    *,
    preset: str = "yesterday",
    start_date=None,
    end_date=None,
    segment: Optional[str] = None,
) -> tuple[bytes, str]:
    """Run export SQL and return (csv_bytes, filename)."""
    template_sql = resolve_export_sql(widget, segment)
    if not template_sql:
        raise ValueError("This widget does not support export")

    export_mode = _export_mode(widget)
    export_widget = {**widget, "sql": template_sql}
    use_filter = should_apply_date_filter(dashboard.name, dashboard.filters)
    date_column = start = end = None
    if use_filter:
        date_column = get_date_column(dashboard.name, dashboard.filters)
        start, end = resolve_date_range(preset, start_date, end_date)

    _, executable_sql = resolve_widget_sql(
        export_widget,
        date_column=date_column,
        start=start,
        end=end,
        use_date_filter=use_filter,
    )

    result = execute_sql_sync(executable_sql)
    if not result.get("success"):
        raise RuntimeError(result.get("error") or "Export query failed")

    rows = clean_rows(result.get("data") or [])
    columns = result.get("columns") or (list(rows[0].keys()) if rows else [])

    if export_mode == "phones":
        phone_col = find_phone_column(columns) or "mobile_number"
        columns = [phone_col]
        seen = set()
        deduped = []
        for row in rows:
            phone = row.get(phone_col)
            if phone is None:
                continue
            phone_str = str(phone).strip()
            if not phone_str or phone_str in seen:
                continue
            seen.add(phone_str)
            deduped.append({phone_col: phone_str})
        rows = deduped

    period_label = _format_period_label(preset, start_date, end_date, start, end)
    filename = _build_filename(dashboard, widget, preset, start_date, end_date, start)

    buffer = io.StringIO()
    writer = csv.writer(buffer)

    writer.writerow([f"# Dashboard: {dashboard.name}"])
    writer.writerow([f"# Widget: {widget.get('title') or widget.get('id')}"])
    if widget.get("type") == "metric" and widget.get("value"):
        writer.writerow([f"# Widget value: {widget.get('value')}"])
    writer.writerow([f"# Period: {period_label}"])
    if segment:
        writer.writerow([f"# Filter: {segment}"])
    writer.writerow([f"# Exported: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"])
    writer.writerow([f"# Rows: {len(rows)}"])
    writer.writerow([])

    headers = [_label_column(col) for col in columns]
    writer.writerow(headers)
    for row in rows:
        writer.writerow([_format_cell(row.get(col)) for col in columns])

    return buffer.getvalue().encode("utf-8"), filename
