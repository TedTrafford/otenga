"""Date-range filtering for dashboard widget SQL (MPESA_DB_*)."""

import re
from datetime import date, datetime, timedelta, timezone
from typing import Optional, Tuple

# Primary timestamp column per bundled dashboard (table-qualified where helpful).
DASHBOARD_DATE_COLUMNS = {
    "Fraud Rules Dashboard": "tbl_fraud_rules.evaluated_at",
    "File Processing Dashboard": "tbl_file_processing_logs.start_time",
    "Customer Scoring Dashboard": "tbl_subscriber_profiles.last_updated",
    "Rejection Reasons Dashboard": "tbl_rejection_reasons.date_created",
    "Raw M-Pesa Statements Dashboard": "tbl_raw_mpesa_statements.transaction_date",
    "Customer Funnel Dashboard": "tbl_file_processing_logs.start_time",
}

# Columns stored as DATE (not DATETIME) — compare on date boundaries only.
_DATE_COLUMNS = frozenset({
    "tbl_raw_mpesa_statements.transaction_date",
    "transaction_date",
})

VALID_PRESETS = frozenset({"yesterday", "7d", "30d", "180d", "365d", "custom"})
DEFAULT_PRESET = "yesterday"


def get_date_column(dashboard_name: str, filters: Optional[list] = None) -> str:
    if filters:
        for f in filters:
            if isinstance(f, dict) and f.get("type") == "date" and f.get("column"):
                return f["column"]
    return DASHBOARD_DATE_COLUMNS.get(dashboard_name, "created_at")


def resolve_date_range(
    preset: str = DEFAULT_PRESET,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> Tuple[datetime, datetime]:
    """Return [start, end) UTC datetimes for a preset or custom range."""
    preset = preset if preset in VALID_PRESETS else DEFAULT_PRESET
    now = datetime.now(timezone.utc)
    today = now.date()

    if preset == "custom":
        if not start_date or not end_date:
            raise ValueError("Custom range requires start_date and end_date")
        if end_date < start_date:
            raise ValueError("end_date must be on or after start_date")
        start = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
        end = datetime.combine(end_date + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
        return start, end

    if preset == "yesterday":
        y = today - timedelta(days=1)
        start = datetime.combine(y, datetime.min.time(), tzinfo=timezone.utc)
        end = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)
        return start, end

    days = {"7d": 7, "30d": 30, "180d": 180, "365d": 365}[preset]
    start = datetime.combine(today - timedelta(days=days), datetime.min.time(), tzinfo=timezone.utc)
    return start, now


def _bare_column(date_column: str) -> str:
    return date_column.split(".", 1)[-1]


def _find_tail_clause_index(sql: str) -> int:
    """Index before the outer query's first GROUP BY / ORDER BY / LIMIT."""
    upper = sql.upper()
    insert_at = len(sql)
    for token in (
        r"\s+GROUP\s+BY",
        r"\s+ORDER\s+BY",
        r"\s+LIMIT\s",
        r"\nGROUP\s+BY",
        r"\nORDER\s+BY",
        r"\nLIMIT\s",
    ):
        match = re.search(token, upper)
        if match:
            insert_at = min(insert_at, match.start())
    return insert_at


def _strip_baked_date_filters(sql: str) -> str:
    """Remove runtime date-filter fragments accidentally persisted into widget SQL."""
    clause = r"\w+\s>=\s'[^']+'\s+AND\s+\w+\s<\s'[^']+'"
    sql = re.sub(
        rf"(\bWHERE\b\s+)1=1\s+AND\s+{clause}\s+AND\s+",
        r"\1",
        sql,
        flags=re.IGNORECASE,
    )
    sql = re.sub(
        rf"(\bWHERE\b\s+)1=1\s+AND\s+{clause}\b",
        "",
        sql,
        flags=re.IGNORECASE,
    )
    sql = re.sub(
        rf"\n\s+WHERE\s+1=1\s+AND\s+{clause}\b",
        "",
        sql,
        flags=re.IGNORECASE,
    )
    return sql


_SQL_CLAUSE_WORDS = frozenset({
    "GROUP", "ORDER", "WHERE", "LEFT", "RIGHT", "INNER", "JOIN", "CROSS",
    "LIMIT", "HAVING", "UNION", "ON", "USING", "LATERAL",
})


def _end_of_table_reference(sql: str, from_match: re.Match) -> int:
    """Return index after ``FROM <table>`` and an optional alias."""
    pos = from_match.end()
    rest = sql[pos:]
    alias_match = re.match(r"\s+(?:AS\s+)?(\w+)\b", rest, re.IGNORECASE)
    if alias_match and alias_match.group(1).upper() not in _SQL_CLAUSE_WORDS:
        pos += alias_match.end()
    return pos


def repair_widget_sql_template(sql: str) -> str:
    """Strip broken runtime date-filter fragments so placeholders can be re-applied."""
    sql = re.sub(
        r"\s+WHERE\s+1=1\s+\{\{date_filter\}\}\s+AND\s+",
        " AND ",
        sql,
        flags=re.IGNORECASE,
    )
    sql = re.sub(r"\s+WHERE\s+1=1\s+\{\{date_filter\}\}", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\{\{date_filter\}\}", "", sql)
    return _strip_baked_date_filters(sql.strip())


def apply_date_filter_placeholder(sql: str, date_column: Optional[str] = None) -> str:
    """Ensure widget SQL has a {{date_filter}} placeholder at the source table scan.

    Prefers filtering at the fact-table scan inside CTEs/subqueries. Join-heavy
    queries fall back to the outer WHERE (or a new one before GROUP BY/ORDER BY).
    """
    if "{{date_filter}}" in sql:
        return sql

    stripped = sql.strip().rstrip(";")
    tail_at = _find_tail_clause_index(stripped)

    if date_column and "." in date_column:
        table = date_column.split(".", 1)[0]
        pattern = re.compile(rf"\bFROM\s+{re.escape(table)}\b", re.IGNORECASE)
        match = pattern.search(stripped)
        if match:
            insert_pos = _end_of_table_reference(stripped, match)
            rest = stripped[insert_pos:insert_pos + 200]
            where_at_scan = re.match(r"\s+WHERE\b", rest, re.IGNORECASE)
            join_at_scan = re.match(
                r"\s+(?:LEFT|RIGHT|INNER|CROSS|JOIN|ON)\b",
                rest,
                re.IGNORECASE,
            )
            if where_at_scan and not join_at_scan:
                where_end = insert_pos + where_at_scan.end()
                return stripped[:where_end] + " 1=1 {{date_filter}} AND" + stripped[where_end:]
            if not join_at_scan:
                return stripped[:insert_pos] + "\n    WHERE 1=1 {{date_filter}}" + stripped[insert_pos:]

    prefix = stripped[:tail_at]
    suffix = stripped[tail_at:]
    where_matches = list(re.finditer(r"\bWHERE\b", prefix, re.IGNORECASE))
    if where_matches:
        return prefix + " {{date_filter}}" + suffix
    return prefix + " WHERE 1=1 {{date_filter}}" + suffix


def build_date_filter_clause(date_column: str, start: datetime, end: datetime) -> str:
    col = _bare_column(date_column)
    if date_column in _DATE_COLUMNS or date_column.endswith(".transaction_date"):
        start_s = start.strftime("%Y-%m-%d")
        end_s = end.strftime("%Y-%m-%d")
        return f"AND {col} >= '{start_s}' AND {col} < '{end_s}'"

    start_s = start.strftime("%Y-%m-%d %H:%M:%S")
    end_s = end.strftime("%Y-%m-%d %H:%M:%S")
    return f"AND {col} >= '{start_s}' AND {col} < '{end_s}'"


def inject_date_filter(
    sql: str,
    date_column: str,
    start: datetime,
    end: datetime,
) -> str:
    sql = apply_date_filter_placeholder(sql, date_column)
    clause = build_date_filter_clause(date_column, start, end)
    return sql.replace("{{date_filter}}", clause)


def resolve_widget_sql(
    widget: dict,
    *,
    date_column: Optional[str] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    use_date_filter: bool = True,
) -> tuple[str, str]:
    """Return (template_sql, executable_sql) for a widget."""
    template_sql = (widget.get("sql") or "").strip()
    if not template_sql or template_sql.startswith("--"):
        return template_sql, template_sql

    template_sql = repair_widget_sql_template(template_sql)

    if use_date_filter:
        template_sql = apply_date_filter_placeholder(template_sql, date_column)
        if date_column and start and end:
            return template_sql, inject_date_filter(template_sql, date_column, start, end)
        return template_sql, template_sql.replace("{{date_filter}}", "")

    return template_sql, template_sql.replace("{{date_filter}}", "")


def should_apply_date_filter(dashboard_name: str, filters: Optional[list] = None) -> bool:
    if filters and any(isinstance(f, dict) and f.get("type") == "date" for f in filters):
        return True
    return dashboard_name in DASHBOARD_DATE_COLUMNS


def get_default_preset(dashboard_name: str, filters: Optional[list] = None) -> str:
    """Dashboard-wide default time range (falls back to yesterday)."""
    if filters:
        for f in filters:
            if isinstance(f, dict) and f.get("type") == "date" and f.get("default_preset"):
                preset = f["default_preset"]
                if preset in VALID_PRESETS:
                    return preset
    return DEFAULT_PRESET


def default_date_filters(date_column: str) -> list:
    return [{"type": "date", "column": date_column, "default_preset": DEFAULT_PRESET}]
