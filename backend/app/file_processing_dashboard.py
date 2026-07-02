"""Build and persist the File Processing dashboard (queries remote MPESA_DB_*)."""

from sqlalchemy.orm.attributes import flag_modified

from .dashboard_widgets import (
    attach_widget_exports,
    build_figure,
    build_stacked_bar,
    chart_widget,
    clean_rows,
    metric_widget,
    run_query,
    table_widget,
)
from .database import SessionLocal
from .dashboard_date_filter import default_date_filters
from .models import Dashboard, NotebookStatus

DATE_FILTERS = default_date_filters("tbl_file_processing_logs.start_time")

DASHBOARD_NAME = "File Processing Dashboard"
DASHBOARD_DESCRIPTION = (
    "M-Pesa statement parse runs, success rates, errors, phone validation, and throughput."
)

QUERIES = {
    "kpi_summary": """
        SELECT
            COUNT(*)                                              AS total_runs,
            COUNT(DISTINCT filename)                              AS distinct_files,
            SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END)            AS success_count,
            SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END)             AS failed_count,
            SUM(CASE WHEN status = 'SKIPPED' THEN 1 ELSE 0 END)            AS skipped_count,
            ROUND(100.0 * SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END)
                  / NULLIF(COUNT(*), 0), 1)                       AS success_rate_pct,
            ROUND(100.0 * SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END)
                  / NULLIF(COUNT(*), 0), 1)                       AS failure_rate_pct,
            SUM(rows_inserted)                                    AS total_rows_inserted,
            SUM(rows_skipped)                                     AS total_rows_skipped,
            ROUND(AVG(CASE WHEN status = 'SUCCESS' THEN duration_seconds END), 2)
                                                                  AS avg_success_duration_sec,
            ROUND(MAX(duration_seconds), 2)                       AS max_duration_sec,
            ROUND(AVG(CASE WHEN status = 'SUCCESS' THEN rows_inserted END), 0)
                                                                  AS avg_rows_per_success,
            MAX(start_time)                                       AS last_run_at
        FROM tbl_file_processing_logs
        WHERE 1=1 {{date_filter}}
    """,
    "status_distribution": """
        SELECT
            status,
            COUNT(*) AS run_count,
            ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct
        FROM tbl_file_processing_logs
        GROUP BY status
        ORDER BY CASE status
            WHEN 'SUCCESS' THEN 1 WHEN 'FAILED' THEN 2 WHEN 'SKIPPED' THEN 3 ELSE 4 END
    """,
    "status_distribution_latest": """
        WITH latest_file_logs AS (
            SELECT * FROM (
            SELECT filename, status,
                   ROW_NUMBER() OVER (PARTITION BY filename ORDER BY start_time DESC) AS _rn
            FROM tbl_file_processing_logs
        ) _fp WHERE _rn = 1
        )
        SELECT status, COUNT(*) AS file_count,
               ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct
        FROM latest_file_logs
        GROUP BY status
        ORDER BY file_count DESC
    """,
    "source_comparison": """
        SELECT source, COUNT(*) AS run_count,
               COUNT(DISTINCT filename) AS distinct_files,
               ROUND(100.0 * SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END)
                     / NULLIF(COUNT(*), 0), 1) AS success_rate_pct,
               SUM(rows_inserted) AS rows_inserted
        FROM tbl_file_processing_logs
        GROUP BY source
        ORDER BY run_count DESC
    """,
    "source_status": """
        SELECT source, status, COUNT(*) AS run_count
        FROM tbl_file_processing_logs
        GROUP BY source, status
        ORDER BY source, run_count DESC
    """,
    "daily_volume": """
        SELECT DATE(start_time) AS run_date,
               COUNT(*) AS total_runs,
               SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) AS success_runs,
               SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) AS failed_runs,
               SUM(CASE WHEN status = 'SKIPPED' THEN 1 ELSE 0 END) AS skipped_runs,
               SUM(rows_inserted) AS rows_inserted
        FROM tbl_file_processing_logs
        GROUP BY DATE(start_time)
        ORDER BY run_date DESC
        LIMIT 60
    """,
    "hour_of_day": """
        SELECT HOUR(start_time) AS hour_of_day,
               COUNT(*) AS run_count,
               SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) AS success_runs,
               SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) AS failed_runs
        FROM tbl_file_processing_logs
        GROUP BY HOUR(start_time)
        ORDER BY hour_of_day
    """,
    "error_breakdown": """
        SELECT
            CASE
                WHEN error LIKE '%not been decrypted%' THEN 'File not decrypted'
                WHEN error LIKE '%already exist%' THEN 'Duplicate submission'
                WHEN error LIKE '%no transactions%' OR error LIKE '%csv not created%'
                    THEN 'No transactions parsed'
                ELSE LEFT(error, 80)
            END AS error_category,
            COUNT(*) AS run_count
        FROM tbl_file_processing_logs
        WHERE error <> ''
        GROUP BY 1
        ORDER BY run_count DESC
        LIMIT 15
    """,
    "profiling_outcome": """
        SELECT profiling_status, COUNT(*) AS run_count,
               ROUND(AVG(balance_check_pct), 2) AS avg_balance_check_pct
        FROM tbl_file_processing_logs
        WHERE source = 'parse_single.py'
          AND profiling_status NOT IN ('', 'N/A')
        GROUP BY profiling_status
        ORDER BY run_count DESC
    """,
    "balance_check_bands": """
        SELECT
            CASE
                WHEN balance_check_pct IS NULL THEN 'Not recorded'
                WHEN balance_check_pct >= 95 THEN '95%+ Excellent'
                WHEN balance_check_pct >= 85 THEN '85-94% Good'
                WHEN balance_check_pct >= 70 THEN '70-84% Acceptable'
                ELSE 'Below 70% — review'
            END AS balance_check_band,
            COUNT(*) AS run_count
        FROM tbl_file_processing_logs
        WHERE source = 'parse_single.py'
          AND status IN ('SUCCESS', 'SKIPPED')
        GROUP BY 1
        ORDER BY run_count DESC
    """,
    "duration_scatter": """
        SELECT filename, source, status,
               rows_inserted + rows_skipped AS total_parsed_rows,
               duration_seconds
        FROM tbl_file_processing_logs
        WHERE status IN ('SUCCESS', 'SKIPPED')
          AND (rows_inserted > 0 OR rows_skipped > 0)
        ORDER BY total_parsed_rows DESC
        LIMIT 500
    """,
    "failed_watchlist": """
        SELECT id, filename, md5, source, record_id,
               supplied_phone_number, extracted_phone_number,
               duration_seconds, start_time, error
        FROM tbl_file_processing_logs
        WHERE status = 'FAILED'
        ORDER BY start_time DESC
        LIMIT 100
    """,
    "skipped_submissions": """
        SELECT id, filename, md5, source, record_id,
               rows_inserted, rows_skipped,
               supplied_phone_number, extracted_phone_number,
               profiling_status, phone_match, start_time, error
        FROM tbl_file_processing_logs
        WHERE status = 'SKIPPED'
        ORDER BY start_time DESC
        LIMIT 100
    """,
    "still_failing": """
        WITH latest_file_logs AS (
            SELECT * FROM (
            SELECT filename, md5, status, start_time, error,
                   COUNT(*) OVER (PARTITION BY filename) AS total_attempts,
                   ROW_NUMBER() OVER (PARTITION BY filename ORDER BY start_time DESC) AS _rn
            FROM tbl_file_processing_logs
        ) _fp WHERE _rn = 1
        )
        SELECT filename, md5, total_attempts,
               start_time AS last_attempt_at, error AS last_error
        FROM latest_file_logs
        WHERE status = 'FAILED'
        ORDER BY total_attempts DESC, last_attempt_at DESC
        LIMIT 100
    """,
    "phone_mismatch": """
        SELECT id, filename, record_id,
               supplied_phone_number, extracted_phone_number,
               phone_match, profiling_status, balance_check_pct,
               rows_inserted, status, start_time
        FROM tbl_file_processing_logs
        WHERE source = 'parse_single.py'
          AND phone_match = 'NO_MATCH'
        ORDER BY start_time DESC
        LIMIT 100
    """,
    "duration_stats": """
        SELECT status, COUNT(*) AS run_count,
               ROUND(AVG(duration_seconds), 2) AS avg_duration_sec,
               ROUND(MAX(duration_seconds) * 0.95, 2)
                   AS p95_duration_sec,
               ROUND(MAX(duration_seconds), 2) AS max_duration_sec
        FROM tbl_file_processing_logs
        GROUP BY status
        ORDER BY run_count DESC
    """,
    "latest_per_file": """
        WITH latest_file_logs AS (
            SELECT * FROM (
            SELECT id, filename, md5, source, record_id,
                   rows_inserted, rows_skipped, start_time, duration_seconds,
                   status, profiling_status, phone_match, balance_check_pct,
                   supplied_phone_number, extracted_phone_number, error,
                   ROW_NUMBER() OVER (PARTITION BY filename ORDER BY start_time DESC) AS _rn
            FROM tbl_file_processing_logs
        ) _fp WHERE _rn = 1
        )
        SELECT * FROM latest_file_logs
        ORDER BY start_time DESC
        LIMIT 200
    """,
    "api_records": """
        SELECT record_id, COUNT(*) AS submission_count,
               COUNT(DISTINCT filename) AS distinct_files,
               SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) AS success_count,
               SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) AS failed_count,
               SUM(rows_inserted) AS total_rows_inserted,
               MAX(start_time) AS last_submission_at
        FROM tbl_file_processing_logs
        WHERE record_id <> ''
        GROUP BY record_id
        ORDER BY last_submission_at DESC
        LIMIT 100
    """,
    "recent_activity": """
        SELECT id, filename, source, status,
               rows_inserted, rows_skipped, duration_seconds,
               record_id, phone_match,
               LEFT(error, 80) AS error_preview, start_time
        FROM tbl_file_processing_logs
        ORDER BY start_time DESC, id DESC
        LIMIT 50
    """,
}

_STATUS_ORDER = {"SUCCESS": 1, "FAILED": 2, "SKIPPED": 3}


def _q(key: str):
    return run_query(QUERIES[key])


def build_dashboard():
    widgets = []
    layout = []
    y = 0

    kpi_rows, _, kpi_sql = _q("kpi_summary")
    kpi_rows = clean_rows(kpi_rows)
    for i, (wid, title, col) in enumerate([
        ("fp-kpi-total-runs", "Total Runs", "total_runs"),
        ("fp-kpi-distinct-files", "Distinct Files", "distinct_files"),
        ("fp-kpi-success", "Successful Runs", "success_count"),
        ("fp-kpi-failed", "Failed Runs", "failed_count"),
        ("fp-kpi-skipped", "Skipped Runs", "skipped_count"),
        ("fp-kpi-success-rate", "Success Rate %", "success_rate_pct"),
        ("fp-kpi-rows-inserted", "Rows Inserted", "total_rows_inserted"),
        ("fp-kpi-avg-duration", "Avg Success Duration (s)", "avg_success_duration_sec"),
    ]):
        item = metric_widget(
            wid, title, col, kpi_rows, kpi_sql,
            {"x": (i % 4) * 3, "y": y + (i // 4) * 5, "w": 3, "h": 5, "minW": 2, "minH": 4},
        )
        widgets.append(item["widget"])
        layout.append(item["layout"])
    y += 10

    rows, cols, sql = _q("status_distribution")
    rows = clean_rows(rows)
    item = chart_widget(
        "fp-chart-status", "Run Status Distribution", rows, cols, sql, "pie",
        "status", ["run_count"],
        build_figure(rows, "status", ["run_count"], "pie"),
        {"x": 0, "y": y, "w": 4, "h": 10, "minW": 3, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])

    rows, cols, sql = _q("status_distribution_latest")
    rows = clean_rows(rows)
    item = chart_widget(
        "fp-chart-status-latest", "Latest Attempt per File", rows, cols, sql, "pie",
        "status", ["file_count"],
        build_figure(rows, "status", ["file_count"], "pie"),
        {"x": 4, "y": y, "w": 4, "h": 10, "minW": 3, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])

    rows, cols, sql = _q("source_comparison")
    rows = clean_rows(rows)
    item = chart_widget(
        "fp-chart-source", "Runs by Source", rows, cols, sql, "bar",
        "source", ["run_count"],
        build_figure(rows, "source", ["run_count"], "bar"),
        {"x": 8, "y": y, "w": 4, "h": 10, "minW": 3, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])
    y += 10

    rows, cols, sql = _q("source_status")
    rows = clean_rows(rows)
    item = chart_widget(
        "fp-chart-source-status", "Status by Source", rows, cols, sql, "stacked_bar",
        "source", ["run_count"],
        build_stacked_bar(rows, "source", "status", "run_count", _STATUS_ORDER),
        {"x": 0, "y": y, "w": 6, "h": 10, "minW": 4, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])

    rows, cols, sql = _q("daily_volume")
    rows = clean_rows(sorted(rows, key=lambda r: str(r.get("run_date") or "")))
    item = chart_widget(
        "fp-chart-daily", "Daily Processing Volume", rows, cols, sql, "line",
        "run_date", ["success_runs", "failed_runs", "skipped_runs"],
        build_figure(rows, "run_date", ["success_runs", "failed_runs", "skipped_runs"], "line"),
        {"x": 6, "y": y, "w": 6, "h": 10, "minW": 4, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])
    y += 10

    rows, cols, sql = _q("hour_of_day")
    rows = clean_rows(sorted(rows, key=lambda r: r.get("hour_of_day") or 0))
    item = chart_widget(
        "fp-chart-hour", "Runs by Hour of Day", rows, cols, sql, "bar",
        "hour_of_day", ["run_count"],
        build_figure(rows, "hour_of_day", ["run_count"], "bar"),
        {"x": 0, "y": y, "w": 4, "h": 10, "minW": 3, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])

    rows, cols, sql = _q("error_breakdown")
    rows = clean_rows(rows)
    item = chart_widget(
        "fp-chart-errors", "Error Categories", rows, cols, sql, "bar",
        "error_category", ["run_count"],
        build_figure(rows, "error_category", ["run_count"], "bar"),
        {"x": 4, "y": y, "w": 4, "h": 10, "minW": 3, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])

    rows, cols, sql = _q("balance_check_bands")
    rows = clean_rows(rows)
    item = chart_widget(
        "fp-chart-balance", "Balance Check Quality", rows, cols, sql, "bar",
        "balance_check_band", ["run_count"],
        build_figure(rows, "balance_check_band", ["run_count"], "bar"),
        {"x": 8, "y": y, "w": 4, "h": 10, "minW": 3, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])
    y += 10

    rows, cols, sql = _q("profiling_outcome")
    rows = clean_rows(rows)
    item = chart_widget(
        "fp-chart-profiling", "Profiling Outcomes (API)", rows, cols, sql, "bar",
        "profiling_status", ["run_count"],
        build_figure(rows, "profiling_status", ["run_count"], "bar"),
        {"x": 0, "y": y, "w": 6, "h": 10, "minW": 4, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])

    rows, cols, sql = _q("duration_scatter")
    rows = clean_rows([r for r in rows if r.get("duration_seconds") is not None])
    item = chart_widget(
        "fp-chart-scatter", "Duration vs Parsed Rows", rows, cols, sql, "scatter",
        "total_parsed_rows", ["duration_seconds"],
        build_figure(rows, "total_parsed_rows", ["duration_seconds"], "scatter"),
        {"x": 6, "y": y, "w": 6, "h": 10, "minW": 4, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])
    y += 10

    rows, cols, sql = _q("recent_activity")
    rows = clean_rows(rows)
    item = table_widget(
        "fp-table-recent", "Recent Activity", rows, cols, sql,
        {"x": 0, "y": y, "w": 12, "h": 11, "minW": 6, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])
    y += 11

    rows, cols, sql = _q("failed_watchlist")
    rows = clean_rows(rows)
    item = table_widget(
        "fp-table-failed", "Failed Runs", rows, cols, sql,
        {"x": 0, "y": y, "w": 6, "h": 11, "minW": 4, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])

    rows, cols, sql = _q("still_failing")
    rows = clean_rows(rows)
    item = table_widget(
        "fp-table-still-failing", "Still Failing After Retries", rows, cols, sql,
        {"x": 6, "y": y, "w": 6, "h": 11, "minW": 4, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])
    y += 11

    rows, cols, sql = _q("skipped_submissions")
    rows = clean_rows(rows)
    item = table_widget(
        "fp-table-skipped", "Skipped / Duplicate Submissions", rows, cols, sql,
        {"x": 0, "y": y, "w": 6, "h": 11, "minW": 4, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])

    rows, cols, sql = _q("phone_mismatch")
    rows = clean_rows(rows)
    item = table_widget(
        "fp-table-phone-mismatch", "Phone Number Mismatches", rows, cols, sql,
        {"x": 6, "y": y, "w": 6, "h": 11, "minW": 4, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])
    y += 11

    rows, cols, sql = _q("latest_per_file")
    rows = clean_rows(rows)
    item = table_widget(
        "fp-table-latest-file", "Latest Attempt per File", rows, cols, sql,
        {"x": 0, "y": y, "w": 12, "h": 12, "minW": 6, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])
    y += 12

    rows, cols, sql = _q("duration_stats")
    rows = clean_rows(rows)
    item = table_widget(
        "fp-table-duration", "Duration Stats by Status", rows, cols, sql,
        {"x": 0, "y": y, "w": 6, "h": 10, "minW": 4, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])

    rows, cols, sql = _q("api_records")
    rows = clean_rows(rows)
    item = table_widget(
        "fp-table-api-records", "API Record Activity", rows, cols, sql,
        {"x": 6, "y": y, "w": 6, "h": 10, "minW": 4, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])

    attach_widget_exports(widgets)
    return widgets, layout


def ensure_file_processing_dashboard(*, force: bool = False):
    """Create the bundled file processing dashboard if missing; optionally rebuild."""
    db = SessionLocal()
    try:
        existing = db.query(Dashboard).filter(Dashboard.name == DASHBOARD_NAME).first()
        if existing and not force:
            if existing.filters != DATE_FILTERS:
                existing.filters = DATE_FILTERS
                db.commit()
            print(f"✅ File processing dashboard persisted (id={existing.id})")
            return existing.id
    finally:
        db.close()

    try:
        widgets, grid_layout = build_dashboard()
    except Exception as exc:
        print(f"⚠️  File processing dashboard build skipped (data DB): {exc}")
        return None

    db = SessionLocal()
    try:
        existing = db.query(Dashboard).filter(Dashboard.name == DASHBOARD_NAME).first()
        if existing:
            existing.description = DASHBOARD_DESCRIPTION
            existing.widgets = widgets
            existing.layout = grid_layout
            existing.filters = DATE_FILTERS
            existing.status = NotebookStatus.published
            flag_modified(existing, "widgets")
            flag_modified(existing, "layout")
            flag_modified(existing, "filters")
            db.commit()
            print(f"✅ File processing dashboard rebuilt (id={existing.id}, {len(widgets)} widgets)")
            return existing.id

        dashboard = Dashboard(
            name=DASHBOARD_NAME,
            description=DASHBOARD_DESCRIPTION,
            layout=grid_layout,
            widgets=widgets,
            filters=DATE_FILTERS,
            status=NotebookStatus.published,
        )
        db.add(dashboard)
        db.commit()
        db.refresh(dashboard)
        print(f"✅ File processing dashboard created (id={dashboard.id}, {len(widgets)} widgets)")
        return dashboard.id
    except Exception as exc:
        print(f"⚠️  File processing dashboard persist failed: {exc}")
        return None
    finally:
        db.close()
