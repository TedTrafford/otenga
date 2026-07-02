"""Build and persist the Raw M-Pesa Statements dashboard (queries remote MPESA_DB_*)."""

from sqlalchemy.orm.attributes import flag_modified

from .dashboard_widgets import (
    attach_widget_exports,
    build_figure,
    chart_widget,
    clean_rows,
    metric_widget,
    run_query,
    table_widget,
)
from .database import SessionLocal
from .dashboard_date_filter import default_date_filters
from .models import Dashboard, NotebookStatus

DATE_FILTERS = default_date_filters("tbl_raw_mpesa_statements.transaction_date")
_DF = "{{date_filter}}"

CUSTOMER_STATEMENTS_CTE = f"""
WITH customer_statements AS (
    SELECT
        mobile_number,
        MAX(customer_name)    AS customer_name,
        MAX(email_address)    AS email_address,
        MAX(statement_period) AS statement_period,
        COUNT(*)              AS transaction_count,
        MIN(transaction_date) AS first_transaction_date,
        MAX(transaction_date) AS last_transaction_date,
        MAX(transaction_date) - MIN(transaction_date) AS statement_span_days,
        SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) AS total_inflow,
        SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END) AS total_outflow,
        SUM(ABS(amount))      AS total_volume,
        COUNT(DISTINCT transaction_type) AS distinct_transaction_types,
        COUNT(DISTINCT receipt_no)       AS distinct_receipts
    FROM tbl_raw_mpesa_statements
    WHERE 1=1 {_DF}
    GROUP BY mobile_number
)
"""

DASHBOARD_NAME = "Raw M-Pesa Statements Dashboard"
DASHBOARD_DESCRIPTION = (
    "Parsed statement transactions, volume trends, ingestion sources, "
    "Fuliza/betting/lender signals, and unified customer views."
)

QUERIES = {
    "kpi_summary": """
        SELECT
            COUNT(*)                                              AS total_transactions,
            COUNT(DISTINCT mobile_number)                         AS distinct_customers,
            ROUND(COUNT(*) / NULLIF(COUNT(DISTINCT mobile_number), 0), 0)
                                                                  AS avg_transactions_per_customer,
            ROUND(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 0) AS total_inflow,
            ROUND(SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END), 0) AS total_outflow,
            ROUND(SUM(ABS(amount)), 0)                   AS total_absolute_volume,
            ROUND(AVG(ABS(amount)), 2)                   AS avg_transaction_size,
            COUNT(DISTINCT transaction_type)                      AS distinct_transaction_types,
            MIN(transaction_date)                                 AS earliest_transaction,
            MAX(transaction_date)                                 AS latest_transaction
        FROM tbl_raw_mpesa_statements
        WHERE 1=1 {{date_filter}}
    """,
    "pipeline_coverage": """
        SELECT
            (SELECT COUNT(DISTINCT mobile_number) FROM tbl_raw_mpesa_statements)
                AS statement_customers,
            (SELECT COUNT(DISTINCT mobile_number) FROM tbl_subscriber_profiles)
                AS profiled_customers,
            (SELECT COUNT(DISTINCT mobile_number) FROM tbl_fraud_rules)
                AS fraud_scored_customers,
            (SELECT COUNT(DISTINCT s.mobile_number)
             FROM tbl_raw_mpesa_statements s
             LEFT JOIN (SELECT DISTINCT mobile_number FROM tbl_subscriber_profiles) sp
                    ON sp.mobile_number = s.mobile_number
             WHERE sp.mobile_number IS NULL) AS unprofiled_customers
    """,
    "transaction_types": """
        SELECT transaction_type, COUNT(*) AS transaction_count,
               COUNT(DISTINCT mobile_number) AS distinct_customers,
               ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct
        FROM tbl_raw_mpesa_statements
        WHERE 1=1 {{date_filter}}
        GROUP BY transaction_type
        ORDER BY transaction_count DESC
        LIMIT 15
    """,
    "credit_debit_by_type": """
        SELECT transaction_type,
               SUM(CASE WHEN amount > 0 THEN 1 ELSE 0 END) AS credit_rows,
               SUM(CASE WHEN amount < 0 THEN 1 ELSE 0 END) AS debit_rows
        FROM tbl_raw_mpesa_statements
        WHERE 1=1 {{date_filter}}
        GROUP BY transaction_type
        ORDER BY COUNT(*) DESC
        LIMIT 12
    """,
    "daily_volume": """
        SELECT transaction_date, COUNT(*) AS transaction_count,
               COUNT(DISTINCT mobile_number) AS distinct_customers,
               ROUND(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 0) AS total_inflow,
               ROUND(SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END), 0) AS total_outflow
        FROM tbl_raw_mpesa_statements
        WHERE 1=1 {{date_filter}}
        GROUP BY transaction_date
        ORDER BY transaction_date DESC
        LIMIT 60
    """,
    "monthly_volume": """
        SELECT DATE(DATE_FORMAT(transaction_date, '%Y-%m-01')) AS transaction_month,
               COUNT(*) AS transaction_count,
               COUNT(DISTINCT mobile_number) AS distinct_customers,
               ROUND(SUM(ABS(amount)), 0) AS absolute_volume
        FROM tbl_raw_mpesa_statements
        WHERE 1=1 {{date_filter}}
        GROUP BY DATE(DATE_FORMAT(transaction_date, '%Y-%m-01'))
        ORDER BY transaction_month DESC
        LIMIT 24
    """,
    "hour_of_day": """
        SELECT HOUR(transaction_time) AS hour_of_day,
               COUNT(*) AS transaction_count,
               ROUND(AVG(ABS(amount)), 2) AS avg_transaction_size
        FROM tbl_raw_mpesa_statements
        WHERE 1=1 {{date_filter}}
        GROUP BY HOUR(transaction_time)
        ORDER BY hour_of_day
    """,
    "amount_bands": """
        SELECT
            CASE
                WHEN ABS(amount) >= 10000 THEN '10,000+'
                WHEN ABS(amount) >= 5000  THEN '5,000-9,999'
                WHEN ABS(amount) >= 1000  THEN '1,000-4,999'
                WHEN ABS(amount) >= 500   THEN '500-999'
                WHEN ABS(amount) >= 100   THEN '100-499'
                WHEN ABS(amount) >= 20    THEN '20-99'
                ELSE 'Under 20'
            END AS amount_band,
            COUNT(*) AS transaction_count,
            ROUND(SUM(ABS(amount)), 0) AS volume_in_band
        FROM tbl_raw_mpesa_statements
        WHERE 1=1 {{date_filter}}
        GROUP BY 1
        ORDER BY MIN(ABS(amount)) DESC
    """,
    "span_bands": f"""
        {CUSTOMER_STATEMENTS_CTE}
        SELECT
            CASE
                WHEN statement_span_days IS NULL THEN 'Unknown'
                WHEN statement_span_days < 90  THEN 'Under 90 days'
                WHEN statement_span_days < 180 THEN '90-179 days'
                WHEN statement_span_days < 365 THEN '180-364 days'
                ELSE '365+ days'
            END AS span_band,
            COUNT(*) AS customer_count
        FROM customer_statements
        GROUP BY 1
        ORDER BY customer_count DESC
    """,
    "ingestion_path": """
        SELECT
            CASE
                WHEN record_id <> '' THEN 'API / CRB app'
                ELSE 'Batch upload'
            END AS ingestion_path,
            COUNT(*) AS transaction_count,
            ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct
        FROM tbl_raw_mpesa_statements
        WHERE 1=1 {{date_filter}}
        GROUP BY 1
        ORDER BY transaction_count DESC
    """,
    "data_source": """
        SELECT COALESCE(NULLIF(JSON_UNQUOTE(JSON_EXTRACT(metadata, '$.source')), ''), 'batch parser') AS data_source,
               COUNT(*) AS transaction_count,
               COUNT(DISTINCT mobile_number) AS distinct_customers
        FROM tbl_raw_mpesa_statements
        WHERE 1=1 {{date_filter}}
        GROUP BY 1
        ORDER BY transaction_count DESC
    """,
    "p2p_activity": """
        SELECT transaction_type, COUNT(*) AS transaction_count,
               ROUND(SUM(amount), 0) AS net_amount
        FROM tbl_raw_mpesa_statements
        WHERE transaction_type IN ('SEND MONEY', 'RECEIVED MONEY') {{date_filter}}
        GROUP BY transaction_type
        ORDER BY transaction_count DESC
    """,
    "email_domains": """
        SELECT LOWER(SUBSTRING_INDEX(email_address, '@', -1)) AS email_domain,
               COUNT(DISTINCT mobile_number) AS distinct_customers,
               COUNT(*) AS transaction_count
        FROM tbl_raw_mpesa_statements
        WHERE email_address <> '' AND email_address LIKE '%@%' {{date_filter}}
        GROUP BY 1
        ORDER BY distinct_customers DESC
        LIMIT 15
    """,
    "fuliza_summary": """
        SELECT COUNT(*) AS fuliza_transaction_count,
               COUNT(DISTINCT mobile_number) AS distinct_customers,
               ROUND(SUM(ABS(amount)), 0) AS fuliza_absolute_volume
        FROM tbl_raw_mpesa_statements
        WHERE details LIKE '%fuliza%' {{date_filter}}
    """,
    "betting_summary": """
        SELECT COUNT(*) AS betting_transaction_count,
               COUNT(DISTINCT mobile_number) AS distinct_customers,
               ROUND(SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END), 0) AS total_betting_outflow
        FROM tbl_raw_mpesa_statements
        WHERE details LIKE '%sportybet%' OR details LIKE '%sportpesa%'
           OR details LIKE '%betika%' OR details LIKE '%odibets%'
           OR details LIKE '%betway%' OR details LIKE '%1xbet%'
           OR details LIKE '%mozzartbet%' OR details LIKE '%betin%' {{date_filter}}
    """,
    "large_transactions": """
        SELECT id, mobile_number, transaction_date, transaction_type,
               amount, balance, LEFT(details, 100) AS details_preview, receipt_no
        FROM tbl_raw_mpesa_statements
        WHERE ABS(amount) >= 10000 {{date_filter}}
        ORDER BY ABS(amount) DESC, transaction_date DESC
        LIMIT 50
    """,
    "customer_summary": f"""
        {CUSTOMER_STATEMENTS_CTE}
        SELECT * FROM customer_statements
        ORDER BY transaction_count DESC, total_volume DESC
        LIMIT 200
    """,
    "top_by_count": """
        SELECT mobile_number, MAX(customer_name) AS customer_name,
               COUNT(*) AS transaction_count,
               ROUND(SUM(ABS(amount)), 0) AS total_volume
        FROM tbl_raw_mpesa_statements
        WHERE 1=1 {{date_filter}}
        GROUP BY mobile_number
        ORDER BY transaction_count DESC
        LIMIT 25
    """,
    "top_by_volume": """
        SELECT mobile_number, MAX(customer_name) AS customer_name,
               COUNT(*) AS transaction_count,
               ROUND(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 0) AS total_inflow,
               ROUND(SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END), 0) AS total_outflow,
               ROUND(SUM(ABS(amount)), 0) AS total_volume
        FROM tbl_raw_mpesa_statements
        WHERE 1=1 {{date_filter}}
        GROUP BY mobile_number
        ORDER BY total_volume DESC
        LIMIT 25
    """,
    "fuliza_customers": """
        SELECT mobile_number, MAX(customer_name) AS customer_name,
               COUNT(*) AS fuliza_transaction_count,
               ROUND(SUM(ABS(amount)), 0) AS fuliza_volume
        FROM tbl_raw_mpesa_statements
        WHERE details LIKE '%fuliza%' {{date_filter}}
        GROUP BY mobile_number
        ORDER BY fuliza_transaction_count DESC
        LIMIT 25
    """,
    "betting_customers": """
        SELECT mobile_number, MAX(customer_name) AS customer_name,
               COUNT(*) AS betting_transaction_count,
               ROUND(SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END), 0) AS total_betting_outflow
        FROM tbl_raw_mpesa_statements
        WHERE details LIKE '%sportybet%' OR details LIKE '%sportpesa%'
           OR details LIKE '%betika%' OR details LIKE '%odibets%'
           OR details LIKE '%betway%' OR details LIKE '%1xbet%' {{date_filter}}
        GROUP BY mobile_number
        ORDER BY total_betting_outflow ASC
        LIMIT 25
    """,
    "lender_inflow": """
        SELECT mobile_number, MAX(customer_name) AS customer_name,
               COUNT(*) AS lender_inflow_count,
               ROUND(SUM(amount), 0) AS total_lender_inflow
        FROM tbl_raw_mpesa_statements
        WHERE amount > 0
          AND (details LIKE '%tala%' OR details LIKE '%branch%'
               OR details LIKE '%zenka%' OR details LIKE '%okash%'
               OR details LIKE '%mshwari%' OR details LIKE '%timiza%'
               OR details LIKE '%ipesa%' OR details LIKE '%kashway%') {{date_filter}}
        GROUP BY mobile_number
        ORDER BY total_lender_inflow DESC
        LIMIT 25
    """,
    "unified_customers": f"""
        {CUSTOMER_STATEMENTS_CTE.strip()},
        latest_profiles AS (
            SELECT * FROM (
    SELECT mobile_number, model_category, credit_limit,
                   total_score AS credit_model_score, last_updated AS profiled_at,
           ROW_NUMBER() OVER (PARTITION BY mobile_number ORDER BY last_updated DESC) AS _rn
    FROM tbl_subscriber_profiles
) _lp WHERE _rn = 1
        )
        SELECT cs.mobile_number, cs.customer_name, cs.transaction_count,
               cs.statement_span_days, cs.first_transaction_date, cs.last_transaction_date,
               ROUND(cs.total_volume, 0) AS total_volume,
               lp.model_category, lp.credit_limit, lp.credit_model_score,
               fr.total_score AS fraud_score, fr.decision AS fraud_decision
        FROM customer_statements cs
        LEFT JOIN latest_profiles lp ON lp.mobile_number = cs.mobile_number
        LEFT JOIN tbl_fraud_rules fr ON fr.mobile_number = cs.mobile_number
        ORDER BY cs.transaction_count DESC
        LIMIT 200
    """,
    "recent_transactions": """
        SELECT id, mobile_number, customer_name, transaction_date,
               transaction_type, amount, balance,
               LEFT(details, 80) AS details_preview, receipt_no
        FROM tbl_raw_mpesa_statements
        WHERE 1=1 {{date_filter}}
        ORDER BY transaction_date DESC, transaction_time DESC, id DESC
        LIMIT 50
    """,
}


def _q(key: str):
    return run_query(QUERIES[key])


def build_dashboard():
    widgets = []
    layout = []
    y = 0

    kpi_rows, _, kpi_sql = _q("kpi_summary")
    kpi_rows = clean_rows(kpi_rows)
    for i, (wid, title, col) in enumerate([
        ("rms-kpi-transactions", "Total Transactions", "total_transactions"),
        ("rms-kpi-customers", "Distinct Customers", "distinct_customers"),
        ("rms-kpi-avg-txn", "Avg Txns / Customer", "avg_transactions_per_customer"),
        ("rms-kpi-inflow", "Total Inflow", "total_inflow"),
        ("rms-kpi-outflow", "Total Outflow", "total_outflow"),
        ("rms-kpi-volume", "Absolute Volume", "total_absolute_volume"),
        ("rms-kpi-avg-size", "Avg Transaction Size", "avg_transaction_size"),
        ("rms-kpi-types", "Transaction Types", "distinct_transaction_types"),
    ]):
        item = metric_widget(
            wid, title, col, kpi_rows, kpi_sql,
            {"x": (i % 4) * 3, "y": y + (i // 4) * 5, "w": 3, "h": 5, "minW": 2, "minH": 4},
        )
        widgets.append(item["widget"])
        layout.append(item["layout"])
    y += 10

    rows, cols, sql = _q("transaction_types")
    rows = clean_rows(rows)
    item = chart_widget(
        "rms-chart-types", "Transaction Type Mix", rows, cols, sql, "pie",
        "transaction_type", ["transaction_count"],
        build_figure(rows, "transaction_type", ["transaction_count"], "pie"),
        {"x": 0, "y": y, "w": 4, "h": 10, "minW": 3, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])

    rows, cols, sql = _q("ingestion_path")
    rows = clean_rows(rows)
    item = chart_widget(
        "rms-chart-ingestion", "Ingestion Path", rows, cols, sql, "pie",
        "ingestion_path", ["transaction_count"],
        build_figure(rows, "ingestion_path", ["transaction_count"], "pie"),
        {"x": 4, "y": y, "w": 4, "h": 10, "minW": 3, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])

    rows, cols, sql = _q("data_source")
    rows = clean_rows(rows)
    item = chart_widget(
        "rms-chart-source", "Data Source", rows, cols, sql, "bar",
        "data_source", ["transaction_count"],
        build_figure(rows, "data_source", ["transaction_count"], "bar"),
        {"x": 8, "y": y, "w": 4, "h": 10, "minW": 3, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])
    y += 10

    rows, cols, sql = _q("daily_volume")
    rows = clean_rows(sorted(rows, key=lambda r: str(r.get("transaction_date") or "")))
    item = chart_widget(
        "rms-chart-daily", "Daily Transaction Volume", rows, cols, sql, "line",
        "transaction_date", ["transaction_count"],
        build_figure(rows, "transaction_date", ["transaction_count"], "line"),
        {"x": 0, "y": y, "w": 6, "h": 10, "minW": 4, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])

    rows, cols, sql = _q("monthly_volume")
    rows = clean_rows(sorted(rows, key=lambda r: str(r.get("transaction_month") or "")))
    item = chart_widget(
        "rms-chart-monthly", "Monthly Absolute Volume", rows, cols, sql, "bar",
        "transaction_month", ["absolute_volume"],
        build_figure(rows, "transaction_month", ["absolute_volume"], "bar"),
        {"x": 6, "y": y, "w": 6, "h": 10, "minW": 4, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])
    y += 10

    rows, cols, sql = _q("hour_of_day")
    rows = clean_rows(sorted(rows, key=lambda r: r.get("hour_of_day") or 0))
    item = chart_widget(
        "rms-chart-hour", "Transactions by Hour", rows, cols, sql, "bar",
        "hour_of_day", ["transaction_count"],
        build_figure(rows, "hour_of_day", ["transaction_count"], "bar"),
        {"x": 0, "y": y, "w": 4, "h": 10, "minW": 3, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])

    rows, cols, sql = _q("amount_bands")
    rows = clean_rows(rows)
    item = chart_widget(
        "rms-chart-amount", "Transaction Amount Bands", rows, cols, sql, "bar",
        "amount_band", ["transaction_count"],
        build_figure(rows, "amount_band", ["transaction_count"], "bar"),
        {"x": 4, "y": y, "w": 4, "h": 10, "minW": 3, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])

    rows, cols, sql = _q("span_bands")
    rows = clean_rows(rows)
    item = chart_widget(
        "rms-chart-span", "Statement Span per Customer", rows, cols, sql, "bar",
        "span_band", ["customer_count"],
        build_figure(rows, "span_band", ["customer_count"], "bar"),
        {"x": 8, "y": y, "w": 4, "h": 10, "minW": 3, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])
    y += 10

    rows, cols, sql = _q("credit_debit_by_type")
    rows = clean_rows(rows)
    item = chart_widget(
        "rms-chart-credit-debit", "Credit vs Debit by Type", rows, cols, sql, "bar",
        "transaction_type", ["credit_rows", "debit_rows"],
        build_figure(rows, "transaction_type", ["credit_rows", "debit_rows"], "bar"),
        {"x": 0, "y": y, "w": 6, "h": 10, "minW": 4, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])

    rows, cols, sql = _q("p2p_activity")
    rows = clean_rows(rows)
    item = chart_widget(
        "rms-chart-p2p", "P2P Activity", rows, cols, sql, "bar",
        "transaction_type", ["transaction_count"],
        build_figure(rows, "transaction_type", ["transaction_count"], "bar"),
        {"x": 6, "y": y, "w": 6, "h": 10, "minW": 4, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])
    y += 10

    rows, cols, sql = _q("email_domains")
    rows = clean_rows(rows)
    item = chart_widget(
        "rms-chart-email", "Top Email Domains", rows, cols, sql, "bar",
        "email_domain", ["distinct_customers"],
        build_figure(rows, "email_domain", ["distinct_customers"], "bar"),
        {"x": 0, "y": y, "w": 12, "h": 10, "minW": 6, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])
    y += 10

    rows, cols, sql = _q("recent_transactions")
    rows = clean_rows(rows)
    item = table_widget(
        "rms-table-recent", "Recent Transactions", rows, cols, sql,
        {"x": 0, "y": y, "w": 12, "h": 11, "minW": 6, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])
    y += 11

    rows, cols, sql = _q("customer_summary")
    rows = clean_rows(rows)
    item = table_widget(
        "rms-table-customers", "Per-Customer Statement Summary", rows, cols, sql,
        {"x": 0, "y": y, "w": 12, "h": 12, "minW": 6, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])
    y += 12

    rows, cols, sql = _q("unified_customers")
    rows = clean_rows(rows)
    item = table_widget(
        "rms-table-unified", "Statements + Credit + Fraud View", rows, cols, sql,
        {"x": 0, "y": y, "w": 12, "h": 12, "minW": 6, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])
    y += 12

    rows, cols, sql = _q("top_by_count")
    rows = clean_rows(rows)
    item = table_widget(
        "rms-table-top-count", "Top Customers by Transaction Count", rows, cols, sql,
        {"x": 0, "y": y, "w": 6, "h": 11, "minW": 4, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])

    rows, cols, sql = _q("top_by_volume")
    rows = clean_rows(rows)
    item = table_widget(
        "rms-table-top-volume", "Top Customers by Volume", rows, cols, sql,
        {"x": 6, "y": y, "w": 6, "h": 11, "minW": 4, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])
    y += 11

    rows, cols, sql = _q("large_transactions")
    rows = clean_rows(rows)
    item = table_widget(
        "rms-table-large", "Large Transactions (>= 10,000)", rows, cols, sql,
        {"x": 0, "y": y, "w": 6, "h": 11, "minW": 4, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])

    rows, cols, sql = _q("fuliza_customers")
    rows = clean_rows(rows)
    item = table_widget(
        "rms-table-fuliza", "Top Fuliza Customers", rows, cols, sql,
        {"x": 6, "y": y, "w": 6, "h": 11, "minW": 4, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])
    y += 11

    rows, cols, sql = _q("betting_customers")
    rows = clean_rows(rows)
    item = table_widget(
        "rms-table-betting", "Top Betting Customers", rows, cols, sql,
        {"x": 0, "y": y, "w": 6, "h": 11, "minW": 4, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])

    rows, cols, sql = _q("lender_inflow")
    rows = clean_rows(rows)
    item = table_widget(
        "rms-table-lender", "Top Digital Lender Inflow", rows, cols, sql,
        {"x": 6, "y": y, "w": 6, "h": 11, "minW": 4, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])

    attach_widget_exports(widgets)
    return widgets, layout


def ensure_raw_mpesa_statements_dashboard(*, force: bool = False):
    """Create the bundled raw M-Pesa statements dashboard if missing; optionally rebuild."""
    db = SessionLocal()
    try:
        existing = db.query(Dashboard).filter(Dashboard.name == DASHBOARD_NAME).first()
        if existing and not force:
            if existing.filters != DATE_FILTERS:
                existing.filters = DATE_FILTERS
                db.commit()
            print(f"✅ Raw M-Pesa statements dashboard persisted (id={existing.id})")
            return existing.id
    finally:
        db.close()

    try:
        widgets, grid_layout = build_dashboard()
    except Exception as exc:
        print(f"⚠️  Raw M-Pesa statements dashboard build skipped (data DB): {exc}")
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
            print(f"✅ Raw M-Pesa statements dashboard rebuilt (id={existing.id}, {len(widgets)} widgets)")
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
        print(f"✅ Raw M-Pesa statements dashboard created (id={dashboard.id}, {len(widgets)} widgets)")
        return dashboard.id
    except Exception as exc:
        print(f"⚠️  Raw M-Pesa statements dashboard persist failed: {exc}")
        return None
    finally:
        db.close()
