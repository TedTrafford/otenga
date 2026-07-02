"""Build and persist the Customer Funnel dashboard (queries remote MPESA_DB_*)."""

from sqlalchemy.orm.attributes import flag_modified

from .dashboard_widgets import (
    attach_widget_exports,
    build_figure,
    build_funnel_figure,
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

DASHBOARD_NAME = "Customer Funnel Dashboard"
DASHBOARD_DESCRIPTION = (
    "End-to-end customer pipeline funnel — statement processing, credit scoring, "
    "fraud screening, and combined approval outcomes."
)

_DF = "{{date_filter}}"

FUNNEL_CORE = """
WITH cohort AS (
    SELECT DISTINCT COALESCE(
               NULLIF(TRIM(extracted_phone_number), ''),
               NULLIF(TRIM(supplied_phone_number), '')
           ) AS mobile_number
    FROM tbl_file_processing_logs
    WHERE status = 'SUCCESS'
      AND COALESCE(
              NULLIF(TRIM(extracted_phone_number), ''),
              NULLIF(TRIM(supplied_phone_number), '')
          ) IS NOT NULL
      """ + _DF + """
),
latest_profiles AS (
    SELECT * FROM (
    SELECT mobile_number, model_category, total_score AS credit_model_score,
           credit_limit, last_updated AS profiled_at,
           ROW_NUMBER() OVER (PARTITION BY mobile_number ORDER BY last_updated DESC) AS _rn
    FROM tbl_subscriber_profiles
) _lp WHERE _rn = 1
),
enriched AS (
    SELECT
        c.mobile_number,
        EXISTS (
            SELECT 1 FROM tbl_raw_mpesa_statements r
            WHERE r.mobile_number = c.mobile_number
        ) AS has_parsed_data,
        lp.mobile_number IS NOT NULL AS is_scored,
        lp.model_category,
        lp.credit_model_score,
        lp.credit_limit,
        lp.profiled_at,
        fr.mobile_number IS NOT NULL AS is_fraud_evaluated,
        fr.decision AS fraud_decision,
        fr.total_score AS fraud_score,
        fr.evaluated_at,
        CASE
            WHEN lp.mobile_number IS NULL THEN 'Awaiting Credit Score'
            WHEN fr.mobile_number IS NULL AND lp.model_category = 'qualified'
                THEN 'Credit Qualified — Pending Fraud'
            WHEN fr.mobile_number IS NULL AND lp.model_category = 'not_qualified'
                THEN 'Credit Not Qualified — Pending Fraud'
            WHEN lp.model_category = 'qualified' AND fr.decision = 'Approve'
                THEN 'Credit Qualified + Fraud Approved'
            WHEN lp.model_category = 'qualified' AND fr.decision = 'Reject'
                THEN 'Credit Qualified + Fraud Rejected'
            WHEN lp.model_category = 'qualified' AND fr.decision = 'Manual Review'
                THEN 'Credit Qualified + Manual Review'
            WHEN lp.model_category = 'qualified' AND fr.decision = 'Reduce Limit'
                THEN 'Credit Qualified + Reduce Limit'
            WHEN lp.model_category = 'not_qualified' AND fr.decision = 'Approve'
                THEN 'Credit Not Qualified + Fraud Approved'
            WHEN lp.model_category = 'not_qualified' AND fr.decision = 'Reject'
                THEN 'Credit Not Qualified + Fraud Rejected'
            WHEN lp.model_category = 'not_qualified' AND fr.decision = 'Manual Review'
                THEN 'Credit Not Qualified + Manual Review'
            WHEN lp.model_category = 'not_qualified' AND fr.decision = 'Reduce Limit'
                THEN 'Credit Not Qualified + Reduce Limit'
            ELSE 'Other'
        END AS combined_outcome
    FROM cohort c
    LEFT JOIN latest_profiles lp ON lp.mobile_number = c.mobile_number
    LEFT JOIN tbl_fraud_rules fr ON fr.mobile_number = c.mobile_number
)
"""

QUERIES = {
    "funnel_summary": f"""
        {FUNNEL_CORE}
        SELECT
            COUNT(*)                                              AS statements_passed,
            SUM(CASE WHEN has_parsed_data THEN 1 ELSE 0 END)               AS statement_data_parsed,
            SUM(CASE WHEN is_scored THEN 1 ELSE 0 END)                       AS credit_scored,
            SUM(CASE WHEN model_category = 'qualified' THEN 1 ELSE 0 END)    AS credit_qualified,
            SUM(CASE WHEN model_category = 'not_qualified' THEN 1 ELSE 0 END) AS credit_not_qualified,
            SUM(CASE WHEN is_fraud_evaluated THEN 1 ELSE 0 END)              AS fraud_evaluated,
            SUM(CASE WHEN fraud_decision = 'Reject' THEN 1 ELSE 0 END)       AS fraud_rejected,
            SUM(CASE WHEN fraud_decision = 'Manual Review' THEN 1 ELSE 0 END) AS fraud_manual_review,
            SUM(CASE WHEN fraud_decision = 'Reduce Limit' THEN 1 ELSE 0 END) AS fraud_reduce_limit,
            SUM(CASE WHEN fraud_decision = 'Approve' THEN 1 ELSE 0 END)      AS fraud_approved,
            SUM(CASE WHEN is_fraud_evaluated AND fraud_decision <> 'Approve' THEN 1 ELSE 0 END)                                                       AS fraud_not_approved,
            SUM(CASE WHEN model_category = 'qualified' AND fraud_decision = 'Approve' THEN 1 ELSE 0 END)                                                       AS pass_both,
            SUM(CASE WHEN model_category = 'qualified'
                  AND fraud_decision IS NOT NULL AND fraud_decision <> 'Approve' THEN 1 ELSE 0 END)                                                       AS credit_pass_fraud_fail,
            SUM(CASE WHEN model_category = 'not_qualified' AND fraud_decision = 'Approve' THEN 1 ELSE 0 END)                                                       AS credit_fail_fraud_pass,
            SUM(CASE WHEN model_category = 'not_qualified'
                  AND (fraud_decision IS NULL OR fraud_decision <> 'Approve') THEN 1 ELSE 0 END)                                                       AS credit_fail_fraud_fail,
            ROUND(100.0 * SUM(CASE WHEN is_scored THEN 1 ELSE 0 END)
                  / NULLIF(COUNT(*), 0), 1)                          AS scored_rate_pct,
            ROUND(100.0 * SUM(CASE WHEN model_category = 'qualified' THEN 1 ELSE 0 END)
                  / NULLIF(SUM(CASE WHEN is_scored THEN 1 ELSE 0 END), 0), 1) AS qualification_rate_pct,
            ROUND(100.0 * SUM(CASE WHEN fraud_decision = 'Approve' THEN 1 ELSE 0 END)
                  / NULLIF(SUM(CASE WHEN is_fraud_evaluated THEN 1 ELSE 0 END), 0), 1)
                                                                  AS fraud_approval_rate_pct,
            ROUND(100.0 * SUM(CASE WHEN model_category = 'qualified' AND fraud_decision = 'Approve' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 1)                             AS overall_conversion_pct
        FROM enriched
    """,
    "funnel_stages": f"""
        {FUNNEL_CORE},
        stage_counts AS (
            SELECT 'Statements Passed' AS funnel_stage, COUNT(*) AS customer_count, 1 AS stage_order
            FROM enriched
            UNION ALL
            SELECT 'Statement Data Parsed', SUM(CASE WHEN has_parsed_data THEN 1 ELSE 0 END), 2 FROM enriched
            UNION ALL
            SELECT 'Credit Scored', SUM(CASE WHEN is_scored THEN 1 ELSE 0 END), 3 FROM enriched
            UNION ALL
            SELECT 'Credit Qualified', SUM(CASE WHEN model_category = 'qualified' THEN 1 ELSE 0 END), 4 FROM enriched
            UNION ALL
            SELECT 'Fraud Evaluated', SUM(CASE WHEN is_fraud_evaluated THEN 1 ELSE 0 END), 5 FROM enriched
            UNION ALL
            SELECT 'Fraud Rejected', SUM(CASE WHEN fraud_decision = 'Reject' THEN 1 ELSE 0 END), 6 FROM enriched
            UNION ALL
            SELECT 'Fraud Manual Review', SUM(CASE WHEN fraud_decision = 'Manual Review' THEN 1 ELSE 0 END), 7 FROM enriched
            UNION ALL
            SELECT 'Fraud Reduce Limit', SUM(CASE WHEN fraud_decision = 'Reduce Limit' THEN 1 ELSE 0 END), 8 FROM enriched
            UNION ALL
            SELECT 'Fraud Approved', SUM(CASE WHEN fraud_decision = 'Approve' THEN 1 ELSE 0 END), 9 FROM enriched
            UNION ALL
            SELECT 'Credit & Fraud Approved', SUM(CASE WHEN model_category = 'qualified' AND fraud_decision = 'Approve' THEN 1 ELSE 0 END), 10 FROM enriched
        ),
        entry AS (SELECT customer_count AS entry_count FROM stage_counts WHERE stage_order = 1)
        SELECT sc.funnel_stage, sc.customer_count, sc.stage_order,
               ROUND(100.0 * sc.customer_count / NULLIF(e.entry_count, 0), 1) AS pct_of_entry,
               ROUND(100.0 * sc.customer_count
                     / NULLIF(LAG(sc.customer_count) OVER (ORDER BY sc.stage_order), 0), 1)
                   AS pct_of_previous
        FROM stage_counts sc
        CROSS JOIN entry e
        ORDER BY sc.stage_order
    """,
    "combined_outcomes": f"""
        {FUNNEL_CORE}
        SELECT combined_outcome, COUNT(*) AS customer_count,
               ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct
        FROM enriched
        GROUP BY combined_outcome
        ORDER BY customer_count DESC
    """,
    "credit_fraud_matrix": f"""
        {FUNNEL_CORE}
        SELECT
            CASE
                WHEN NOT is_scored THEN 'Not Scored'
                WHEN model_category = 'qualified' THEN 'Credit Qualified'
                ELSE 'Credit Not Qualified'
            END AS credit_outcome,
            CASE
                WHEN NOT is_fraud_evaluated THEN 'Not Evaluated'
                ELSE fraud_decision
            END AS fraud_decision,
            COUNT(*) AS customer_count
        FROM enriched
        GROUP BY 1, 2
        ORDER BY customer_count DESC
    """,
    "credit_fraud_cross": f"""
        {FUNNEL_CORE}
        SELECT
            CASE
                WHEN model_category = 'qualified' THEN 'Credit Qualified'
                ELSE 'Credit Not Qualified'
            END AS credit_outcome,
            fraud_decision,
            COUNT(*) AS customer_count
        FROM enriched
        WHERE is_scored AND is_fraud_evaluated
        GROUP BY 1, 2
        ORDER BY 1, MIN(CASE fraud_decision
            WHEN 'Reject' THEN 1 WHEN 'Manual Review' THEN 2
            WHEN 'Reduce Limit' THEN 3 WHEN 'Approve' THEN 4 ELSE 5 END)
    """,
    "fraud_by_decision": f"""
        {FUNNEL_CORE}
        SELECT fraud_decision, COUNT(*) AS customer_count
        FROM enriched
        WHERE is_fraud_evaluated
        GROUP BY fraud_decision
        ORDER BY MIN(CASE fraud_decision
            WHEN 'Reject' THEN 1 WHEN 'Manual Review' THEN 2
            WHEN 'Reduce Limit' THEN 3 WHEN 'Approve' THEN 4 ELSE 5 END)
    """,
    "daily_entries": f"""
        SELECT DATE(start_time) AS entry_date,
               COUNT(DISTINCT COALESCE(
                   NULLIF(TRIM(extracted_phone_number), ''),
                   NULLIF(TRIM(supplied_phone_number), '')
               )) AS statements_passed
        FROM tbl_file_processing_logs
        WHERE status = 'SUCCESS'
          AND COALESCE(
                  NULLIF(TRIM(extracted_phone_number), ''),
                  NULLIF(TRIM(supplied_phone_number), '')
              ) IS NOT NULL
          {_DF}
        GROUP BY DATE(start_time)
        ORDER BY entry_date DESC
        LIMIT 60
    """,
    "customer_detail": f"""
        {FUNNEL_CORE}
        SELECT mobile_number,
               CASE WHEN has_parsed_data THEN 'Yes' ELSE 'No' END AS statement_parsed,
               CASE WHEN is_scored THEN model_category ELSE 'not_scored' END AS credit_outcome,
               credit_model_score, credit_limit, profiled_at,
               CASE WHEN is_fraud_evaluated THEN fraud_decision ELSE 'not_evaluated' END AS fraud_decision,
               fraud_score, evaluated_at, combined_outcome
        FROM enriched
        ORDER BY combined_outcome, credit_outcome, mobile_number
        LIMIT 500
    """,
}

_CREDIT_FRAUD_ORDER = {
    "Reject": 1, "Manual Review": 2, "Reduce Limit": 3, "Approve": 4, "Not Evaluated": 5,
}


def _q(key: str):
    return run_query(QUERIES[key])


def build_dashboard():
    widgets = []
    layout = []
    y = 0

    kpi_rows, _, kpi_sql = _q("funnel_summary")
    kpi_rows = clean_rows(kpi_rows)
    for i, (wid, title, col) in enumerate([
        ("cf-kpi-statements", "Statements Passed", "statements_passed"),
        ("cf-kpi-scored", "Credit Scored", "credit_scored"),
        ("cf-kpi-qualified", "Credit Qualified", "credit_qualified"),
        ("cf-kpi-not-qualified", "Credit Not Qualified", "credit_not_qualified"),
        ("cf-kpi-fraud-eval", "Fraud Evaluated", "fraud_evaluated"),
        ("cf-kpi-fraud-reject", "Fraud Rejected", "fraud_rejected"),
        ("cf-kpi-fraud-manual", "Fraud Manual Review", "fraud_manual_review"),
        ("cf-kpi-fraud-reduce", "Fraud Reduce Limit", "fraud_reduce_limit"),
        ("cf-kpi-fraud-approved", "Fraud Approved", "fraud_approved"),
        ("cf-kpi-pass-both", "Credit & Fraud Approved", "pass_both"),
        ("cf-kpi-credit-pass-fraud-fail", "Credit OK, Fraud Failed", "credit_pass_fraud_fail"),
        ("cf-kpi-conversion", "Overall Conversion %", "overall_conversion_pct"),
    ]):
        item = metric_widget(
            wid, title, col, kpi_rows, kpi_sql,
            {"x": (i % 4) * 3, "y": y + (i // 4) * 5, "w": 3, "h": 5, "minW": 2, "minH": 4},
        )
        widgets.append(item["widget"])
        layout.append(item["layout"])
    y += 15

    rows, cols, sql = _q("funnel_stages")
    rows = clean_rows(rows)
    item = chart_widget(
        "cf-chart-funnel", "Customer Pipeline Funnel", rows, cols, sql, "funnel",
        "funnel_stage", ["customer_count"],
        build_funnel_figure(rows, "funnel_stage", "customer_count", "Customer Pipeline Funnel"),
        {"x": 0, "y": y, "w": 7, "h": 14, "minW": 5, "minH": 8},
    )
    widgets.append(item["widget"])
    layout.append(item["layout"])

    rows, cols, sql = _q("combined_outcomes")
    rows = clean_rows(rows)
    item = chart_widget(
        "cf-chart-outcomes", "Combined Outcomes", rows, cols, sql, "pie",
        "combined_outcome", ["customer_count"],
        build_figure(rows, "combined_outcome", ["customer_count"], "pie"),
        {"x": 7, "y": y, "w": 5, "h": 14, "minW": 4, "minH": 8},
    )
    widgets.append(item["widget"])
    layout.append(item["layout"])
    y += 14

    rows, cols, sql = _q("funnel_stages")
    rows = clean_rows(rows)
    item = chart_widget(
        "cf-chart-conversion", "Stage Conversion Rates", rows, cols, sql, "bar",
        "funnel_stage", ["pct_of_previous"],
        build_figure(rows, "funnel_stage", ["pct_of_previous"], "bar"),
        {"x": 0, "y": y, "w": 6, "h": 10, "minW": 4, "minH": 6},
    )
    widgets.append(item["widget"])
    layout.append(item["layout"])

    rows, cols, sql = _q("credit_fraud_matrix")
    rows = clean_rows(rows)
    item = chart_widget(
        "cf-chart-matrix", "Credit vs Fraud Outcomes", rows, cols, sql, "stacked_bar",
        "credit_outcome", ["customer_count"],
        build_stacked_bar(rows, "credit_outcome", "fraud_decision", "customer_count", _CREDIT_FRAUD_ORDER),
        {"x": 6, "y": y, "w": 6, "h": 10, "minW": 4, "minH": 6},
    )
    widgets.append(item["widget"])
    layout.append(item["layout"])
    y += 10

    rows, cols, sql = _q("credit_fraud_cross")
    rows = clean_rows(rows)
    item = chart_widget(
        "cf-chart-credit-fraud-cross", "Credit × Fraud (Evaluated Only)", rows, cols, sql, "stacked_bar",
        "credit_outcome", ["customer_count"],
        build_stacked_bar(rows, "credit_outcome", "fraud_decision", "customer_count", _CREDIT_FRAUD_ORDER),
        {"x": 0, "y": y, "w": 6, "h": 10, "minW": 4, "minH": 6},
    )
    widgets.append(item["widget"])
    layout.append(item["layout"])

    rows, cols, sql = _q("fraud_by_decision")
    rows = clean_rows(rows)
    item = chart_widget(
        "cf-chart-fraud-decisions", "Fraud Decisions (Scored Cohort)", rows, cols, sql, "bar",
        "fraud_decision", ["customer_count"],
        build_figure(rows, "fraud_decision", ["customer_count"], "bar"),
        {"x": 6, "y": y, "w": 6, "h": 10, "minW": 4, "minH": 6},
    )
    widgets.append(item["widget"])
    layout.append(item["layout"])
    y += 10

    rows, cols, sql = _q("daily_entries")
    rows = clean_rows(sorted(rows, key=lambda r: str(r.get("entry_date") or "")))
    item = chart_widget(
        "cf-chart-daily", "Daily Statement Entries", rows, cols, sql, "line",
        "entry_date", ["statements_passed"],
        build_figure(rows, "entry_date", ["statements_passed"], "line"),
        {"x": 0, "y": y, "w": 12, "h": 10, "minW": 6, "minH": 6},
    )
    widgets.append(item["widget"])
    layout.append(item["layout"])
    y += 10

    rows, cols, sql = _q("funnel_stages")
    rows = clean_rows(rows)
    item = table_widget(
        "cf-table-stages", "Funnel Stage Breakdown", rows, cols, sql,
        {"x": 0, "y": y, "w": 6, "h": 11, "minW": 4, "minH": 6},
    )
    widgets.append(item["widget"])
    layout.append(item["layout"])

    rows, cols, sql = _q("combined_outcomes")
    rows = clean_rows(rows)
    item = table_widget(
        "cf-table-outcomes", "Outcome Summary", rows, cols, sql,
        {"x": 6, "y": y, "w": 6, "h": 11, "minW": 4, "minH": 6},
    )
    widgets.append(item["widget"])
    layout.append(item["layout"])
    y += 11

    rows, cols, sql = _q("customer_detail")
    rows = clean_rows(rows)
    item = table_widget(
        "cf-table-customers", "Customer Funnel Detail", rows, cols, sql,
        {"x": 0, "y": y, "w": 12, "h": 12, "minW": 6, "minH": 6},
    )
    widgets.append(item["widget"])
    layout.append(item["layout"])

    attach_widget_exports(widgets)
    return widgets, layout


def ensure_customer_funnel_dashboard(*, force: bool = False):
    """Create the bundled customer funnel dashboard if missing; optionally rebuild."""
    db = SessionLocal()
    try:
        existing = db.query(Dashboard).filter(Dashboard.name == DASHBOARD_NAME).first()
        if existing and not force:
            if existing.filters != DATE_FILTERS:
                existing.filters = DATE_FILTERS
                db.commit()
            print(f"✅ Customer funnel dashboard persisted (id={existing.id})")
            return existing.id
    finally:
        db.close()

    try:
        widgets, grid_layout = build_dashboard()
    except Exception as exc:
        print(f"⚠️  Customer funnel dashboard build skipped (data DB): {exc}")
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
            print(f"✅ Customer funnel dashboard rebuilt (id={existing.id}, {len(widgets)} widgets)")
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
        print(f"✅ Customer funnel dashboard created (id={dashboard.id}, {len(widgets)} widgets)")
        return dashboard.id
    except Exception as exc:
        print(f"⚠️  Customer funnel dashboard persist failed: {exc}")
        return None
    finally:
        db.close()
