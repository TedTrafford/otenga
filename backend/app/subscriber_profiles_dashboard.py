"""Build and persist the Customer Scoring dashboard (queries remote MPESA_DB_*)."""

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

DATE_FILTERS = default_date_filters("tbl_subscriber_profiles.last_updated")

DASHBOARD_NAME = "Customer Scoring Dashboard"
DASHBOARD_DESCRIPTION = (
    "Subscriber profile KPIs, qualification rates, segment distributions, "
    "rejection drivers, and credit vs fraud outcomes."
)

LATEST_PROFILES_CTE = """
WITH _ranked_profiles AS (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY mobile_number ORDER BY last_updated DESC) AS _rn
    FROM tbl_subscriber_profiles
    WHERE 1=1 {{date_filter}}
),
latest_profiles AS (
    SELECT id AS profile_id,
           mobile_number,
           last_updated,
           month1_turnover,
           month2_turnover,
           month3_turnover,
           age_days,
           three_month_wavg,
           risk_segment,
           turnover_segment,
           credit_limit,
           total_score AS credit_model_score,
           total_score,
           model_category,
           total_inflow,
           lender_inflow,
           debt_to_income_ratio,
           total_inflow_txn_count,
           lender_inflow_txn_count
    FROM _ranked_profiles
    WHERE _rn = 1
)
"""

QUERIES = {
    "kpi_summary": f"""
        {LATEST_PROFILES_CTE}
        SELECT
            COUNT(*)                                              AS customers_profiled,
            SUM(CASE WHEN model_category = 'qualified' THEN 1 ELSE 0 END)  AS qualified_count,
            SUM(CASE WHEN model_category = 'not_qualified' THEN 1 ELSE 0 END)
                                                                  AS not_qualified_count,
            ROUND(100.0 * SUM(CASE WHEN model_category = 'qualified' THEN 1 ELSE 0 END)
                  / NULLIF(COUNT(*), 0), 1)                       AS qualification_rate_pct,
            ROUND(AVG(CASE WHEN credit_limit > 0 THEN credit_limit END), 0)
                                                                  AS avg_credit_limit_qualified,
            SUM(CASE WHEN credit_limit > 0 THEN credit_limit ELSE 0 END)     AS total_credit_extended,
            ROUND(AVG(total_score), 1)                   AS avg_credit_model_score,
            ROUND(AVG(three_month_wavg), 0)              AS avg_three_month_wavg,
            ROUND(AVG(age_days), 0)                      AS avg_statement_age_days,
            ROUND(AVG(debt_to_income_ratio), 4)          AS avg_dti_ratio,
            SUM(CASE WHEN debt_to_income_ratio > 0.50 THEN 1 ELSE 0 END)   AS high_dti_customers,
            MAX(last_updated)                                     AS last_profiled_at
        FROM latest_profiles
    """,
    "model_category": f"""
        {LATEST_PROFILES_CTE}
        SELECT model_category, COUNT(*) AS customer_count,
               ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct
        FROM latest_profiles
        GROUP BY model_category
        ORDER BY customer_count DESC
    """,
    "risk_segment": f"""
        {LATEST_PROFILES_CTE}
        SELECT risk_segment, COUNT(*) AS customer_count,
               SUM(CASE WHEN model_category = 'qualified' THEN 1 ELSE 0 END) AS qualified_count,
               ROUND(AVG(total_score), 1) AS avg_credit_model_score,
               ROUND(AVG(CASE WHEN credit_limit > 0 THEN credit_limit END), 0)
                   AS avg_credit_limit
        FROM latest_profiles
        WHERE risk_segment > 0
        GROUP BY risk_segment
        ORDER BY risk_segment
    """,
    "turnover_segment": f"""
        {LATEST_PROFILES_CTE}
        SELECT turnover_segment, COUNT(*) AS customer_count,
               SUM(CASE WHEN model_category = 'qualified' THEN 1 ELSE 0 END) AS qualified_count,
               ROUND(AVG(three_month_wavg), 0) AS avg_three_month_wavg,
               ROUND(AVG(CASE WHEN credit_limit > 0 THEN credit_limit END), 0)
                   AS avg_credit_limit
        FROM latest_profiles
        WHERE turnover_segment > 0
        GROUP BY turnover_segment
        ORDER BY turnover_segment
    """,
    "segment_matrix": f"""
        {LATEST_PROFILES_CTE}
        SELECT risk_segment, turnover_segment, COUNT(*) AS customer_count,
               SUM(CASE WHEN model_category = 'qualified' THEN 1 ELSE 0 END) AS qualified_count,
               ROUND(100.0 * SUM(CASE WHEN model_category = 'qualified' THEN 1 ELSE 0 END)
                     / NULLIF(COUNT(*), 0), 1) AS qualification_rate_pct,
               ROUND(AVG(credit_limit), 0) AS avg_credit_limit
        FROM latest_profiles
        WHERE risk_segment > 0 AND turnover_segment > 0
        GROUP BY risk_segment, turnover_segment
        ORDER BY risk_segment DESC, turnover_segment DESC
    """,
    "credit_limit_dist": f"""
        {LATEST_PROFILES_CTE}
        SELECT credit_limit, COUNT(*) AS customer_count,
               ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct
        FROM latest_profiles
        GROUP BY credit_limit
        ORDER BY credit_limit DESC
    """,
    "score_bands": f"""
        {LATEST_PROFILES_CTE}
        SELECT
            CASE
                WHEN total_score >= 950 THEN '950+ (G8)'
                WHEN total_score >= 912 THEN '912-949 (G7)'
                WHEN total_score >= 877 THEN '877-911 (G6)'
                WHEN total_score >= 853 THEN '853-876 (G5)'
                WHEN total_score >= 831 THEN '831-852 (G4)'
                WHEN total_score >= 808 THEN '808-830 (G3)'
                WHEN total_score >= 776 THEN '776-807 (G2)'
                ELSE 'Below 776 (G1)'
            END AS score_band,
            COUNT(*) AS customer_count,
            SUM(CASE WHEN model_category = 'qualified' THEN 1 ELSE 0 END) AS qualified_count,
            MIN(total_score) AS band_min_score
        FROM latest_profiles
        WHERE total_score IS NOT NULL
        GROUP BY 1
        ORDER BY band_min_score DESC
    """,
    "turnover_bands": f"""
        {LATEST_PROFILES_CTE}
        SELECT
            CASE
                WHEN three_month_wavg IS NULL THEN 'Unknown'
                WHEN three_month_wavg <= 9841   THEN 'Seg 1: <= 9,841'
                WHEN three_month_wavg <= 12561  THEN 'Seg 2: 9,842-12,561'
                WHEN three_month_wavg <= 16027  THEN 'Seg 3: 12,562-16,027'
                WHEN three_month_wavg <= 23895  THEN 'Seg 4: 16,028-23,895'
                WHEN three_month_wavg <= 39179  THEN 'Seg 5: 23,896-39,179'
                WHEN three_month_wavg <= 60463  THEN 'Seg 6: 39,180-60,463'
                WHEN three_month_wavg <= 107556 THEN 'Seg 7: 60,464-107,556'
                ELSE 'Seg 8: > 107,556'
            END AS turnover_band,
            COUNT(*) AS customer_count,
            SUM(CASE WHEN model_category = 'qualified' THEN 1 ELSE 0 END) AS qualified_count
        FROM latest_profiles
        GROUP BY 1
        ORDER BY customer_count DESC
    """,
    "monthly_turnover": f"""
        {LATEST_PROFILES_CTE}
        SELECT 'month1 (recent)' AS month_label,
               ROUND(AVG(month1_turnover), 0) AS avg_turnover,
               ROUND(AVG(month1_turnover), 0)
                   AS median_turnover
        FROM latest_profiles WHERE month1_turnover IS NOT NULL
        UNION ALL
        SELECT 'month2',
               ROUND(AVG(month2_turnover), 0),
               ROUND(AVG(month2_turnover), 0)
        FROM latest_profiles WHERE month2_turnover IS NOT NULL
        UNION ALL
        SELECT 'month3 (oldest)',
               ROUND(AVG(month3_turnover), 0),
               ROUND(AVG(month3_turnover), 0)
        FROM latest_profiles WHERE month3_turnover IS NOT NULL
    """,
    "age_bands": f"""
        {LATEST_PROFILES_CTE}
        SELECT
            CASE
                WHEN age_days IS NULL THEN 'Unknown'
                WHEN age_days < 90  THEN 'Under 90 days'
                WHEN age_days < 180 THEN '90-179 days'
                WHEN age_days < 365 THEN '180-364 days'
                ELSE '365+ days'
            END AS age_band,
            COUNT(*) AS customer_count,
            SUM(CASE WHEN model_category = 'qualified' THEN 1 ELSE 0 END) AS qualified_count
        FROM latest_profiles
        GROUP BY 1
        ORDER BY customer_count DESC
    """,
    "dti_bands": f"""
        {LATEST_PROFILES_CTE}
        SELECT
            CASE
                WHEN debt_to_income_ratio IS NULL THEN 'Not computed'
                WHEN debt_to_income_ratio > 0.50 THEN 'Above 50% (blocked)'
                WHEN debt_to_income_ratio > 0.30 THEN '30-50%'
                WHEN debt_to_income_ratio > 0.15 THEN '15-30%'
                WHEN debt_to_income_ratio > 0.05 THEN '5-15%'
                ELSE 'Below 5%'
            END AS dti_band,
            COUNT(*) AS customer_count,
            SUM(CASE WHEN model_category = 'qualified' THEN 1 ELSE 0 END) AS qualified_count
        FROM latest_profiles
        GROUP BY 1
        ORDER BY customer_count DESC
    """,
    "lender_dependency": f"""
        {LATEST_PROFILES_CTE}
        SELECT model_category, COUNT(*) AS customer_count,
               ROUND(AVG(total_inflow), 0) AS avg_total_inflow,
               ROUND(AVG(lender_inflow), 0) AS avg_lender_inflow,
               ROUND(AVG(debt_to_income_ratio), 4) AS avg_dti
        FROM latest_profiles
        GROUP BY model_category
        ORDER BY model_category
    """,
    "rejection_reasons": """
        WITH _ranked_profiles AS (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY mobile_number ORDER BY last_updated DESC) AS _rn
    FROM tbl_subscriber_profiles
    WHERE 1=1 {{date_filter}}
),
latest_profiles AS (
    SELECT mobile_number, model_category
    FROM _ranked_profiles
    WHERE _rn = 1
)
        SELECT rr.reason_code, COUNT(DISTINCT rr.mobile_number) AS customers_affected,
               COUNT(*) AS reason_occurrences,
               ROUND(AVG(rr.score_gap), 1) AS avg_score_gap
        FROM tbl_rejection_reasons rr
        JOIN latest_profiles lp ON lp.mobile_number = rr.mobile_number
        WHERE lp.model_category = 'not_qualified'
        GROUP BY rr.reason_code
        ORDER BY customers_affected DESC
        LIMIT 15
    """,
    "credit_vs_fraud": f"""
        {LATEST_PROFILES_CTE}
        SELECT lp.model_category, fr.decision AS fraud_decision,
               COUNT(*) AS customer_count,
               ROUND(AVG(lp.credit_model_score), 1) AS avg_credit_model_score,
               ROUND(AVG(fr.total_score), 1) AS avg_fraud_score
        FROM latest_profiles lp
        JOIN tbl_fraud_rules fr ON fr.mobile_number = lp.mobile_number
        GROUP BY lp.model_category, fr.decision
        ORDER BY customer_count DESC
    """,
    "daily_volume": """
        SELECT DATE(last_updated) AS profile_date,
               COUNT(*) AS profile_runs,
               COUNT(DISTINCT mobile_number) AS distinct_customers,
               SUM(CASE WHEN model_category = 'qualified' THEN 1 ELSE 0 END) AS qualified_runs,
               SUM(CASE WHEN model_category = 'not_qualified' THEN 1 ELSE 0 END) AS not_qualified_runs
        FROM tbl_subscriber_profiles
    WHERE 1=1 {{date_filter}}
        GROUP BY DATE(last_updated)
        ORDER BY profile_date DESC
        LIMIT 60
    """,
    "high_dti": f"""
        {LATEST_PROFILES_CTE}
        SELECT mobile_number, debt_to_income_ratio, model_category,
               total_score AS credit_model_score, risk_segment, turnover_segment,
               total_inflow, lender_inflow, last_updated
        FROM latest_profiles
        WHERE debt_to_income_ratio > 0.50 AND model_category = 'not_qualified'
        ORDER BY debt_to_income_ratio DESC, total_score DESC
        LIMIT 100
    """,
    "qualified_fraud_flagged": f"""
        {LATEST_PROFILES_CTE}
        SELECT lp.mobile_number, lp.credit_limit, lp.credit_model_score,
               lp.risk_segment, lp.turnover_segment,
               fr.total_score AS fraud_score, fr.decision AS fraud_decision,
               fr.triggered_rules
        FROM latest_profiles lp
        JOIN tbl_fraud_rules fr ON fr.mobile_number = lp.mobile_number
        WHERE lp.model_category = 'qualified' AND fr.decision <> 'Approve'
        ORDER BY fr.total_score DESC
        LIMIT 100
    """,
    "score_drift": """
        WITH ranked AS (
            SELECT mobile_number, total_score, credit_limit, model_category, last_updated,
                   ROW_NUMBER() OVER (PARTITION BY mobile_number ORDER BY last_updated ASC, id ASC) AS rn_first,
                   ROW_NUMBER() OVER (PARTITION BY mobile_number ORDER BY last_updated DESC, id DESC) AS rn_last
            FROM tbl_subscriber_profiles
    WHERE 1=1 {{date_filter}}
        ),
        first_last AS (
            SELECT mobile_number,
                   MAX(CASE WHEN rn_first = 1 THEN total_score END) AS first_score,
                   MAX(CASE WHEN rn_last = 1 THEN total_score END) AS last_score,
                   MAX(CASE WHEN rn_first = 1 THEN credit_limit END) AS first_limit,
                   MAX(CASE WHEN rn_last = 1 THEN credit_limit END) AS last_limit,
                   MAX(CASE WHEN rn_first = 1 THEN model_category END) AS first_category,
                   MAX(CASE WHEN rn_last = 1 THEN model_category END) AS last_category,
                   MAX(CASE WHEN rn_last = 1 THEN last_updated END) AS last_profiled_at
            FROM ranked
            WHERE rn_first = 1 OR rn_last = 1
            GROUP BY mobile_number
            HAVING COUNT(*) > 1
        )
        SELECT mobile_number, first_score, last_score,
               ROUND((last_score - first_score), 1) AS score_change,
               first_limit, last_limit, last_limit - first_limit AS limit_change,
               first_category, last_category, last_profiled_at
        FROM first_last
        WHERE NOT (first_score <=> last_score AND first_limit <=> last_limit AND first_category <=> last_category)
        ORDER BY ABS(last_score - first_score) DESC
        LIMIT 100
    """,
    "latest_profiles": f"""
        {LATEST_PROFILES_CTE}
        SELECT * FROM latest_profiles
        ORDER BY last_updated DESC
        LIMIT 200
    """,
    "recent_activity": """
        SELECT id AS profile_id, mobile_number, model_category, credit_limit,
               total_score AS credit_model_score, risk_segment, turnover_segment,
               three_month_wavg, debt_to_income_ratio, last_updated
        FROM tbl_subscriber_profiles
    WHERE 1=1 {{date_filter}}
        ORDER BY last_updated DESC, id DESC
        LIMIT 50
    """,
}

_FRAUD_DECISION_ORDER = {"Reject": 1, "Manual Review": 2, "Reduce Limit": 3, "Approve": 4}


def _q(key: str):
    return run_query(QUERIES[key])


def build_dashboard():
    widgets = []
    layout = []
    y = 0

    kpi_rows, _, kpi_sql = _q("kpi_summary")
    kpi_rows = clean_rows(kpi_rows)
    for i, (wid, title, col) in enumerate([
        ("cs-kpi-customers", "Customers Profiled", "customers_profiled"),
        ("cs-kpi-qualified", "Qualified", "qualified_count"),
        ("cs-kpi-not-qualified", "Not Qualified", "not_qualified_count"),
        ("cs-kpi-qual-rate", "Qualification Rate %", "qualification_rate_pct"),
        ("cs-kpi-avg-limit", "Avg Credit Limit", "avg_credit_limit_qualified"),
        ("cs-kpi-total-credit", "Total Credit Extended", "total_credit_extended"),
        ("cs-kpi-avg-score", "Avg Credit Score", "avg_credit_model_score"),
        ("cs-kpi-high-dti", "High DTI (>50%)", "high_dti_customers"),
    ]):
        item = metric_widget(
            wid, title, col, kpi_rows, kpi_sql,
            {"x": (i % 4) * 3, "y": y + (i // 4) * 5, "w": 3, "h": 5, "minW": 2, "minH": 4},
        )
        widgets.append(item["widget"])
        layout.append(item["layout"])
    y += 10

    rows, cols, sql = _q("model_category")
    rows = clean_rows(rows)
    item = chart_widget(
        "cs-chart-category", "Qualification Outcome", rows, cols, sql, "pie",
        "model_category", ["customer_count"],
        build_figure(rows, "model_category", ["customer_count"], "pie"),
        {"x": 0, "y": y, "w": 4, "h": 10, "minW": 3, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])

    rows, cols, sql = _q("risk_segment")
    rows = clean_rows(rows)
    item = chart_widget(
        "cs-chart-risk", "Risk Segment Distribution", rows, cols, sql, "bar",
        "risk_segment", ["customer_count"],
        build_figure(rows, "risk_segment", ["customer_count"], "bar"),
        {"x": 4, "y": y, "w": 4, "h": 10, "minW": 3, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])

    rows, cols, sql = _q("turnover_segment")
    rows = clean_rows(rows)
    item = chart_widget(
        "cs-chart-turnover-seg", "Turnover Segment Distribution", rows, cols, sql, "bar",
        "turnover_segment", ["customer_count"],
        build_figure(rows, "turnover_segment", ["customer_count"], "bar"),
        {"x": 8, "y": y, "w": 4, "h": 10, "minW": 3, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])
    y += 10

    rows, cols, sql = _q("score_bands")
    rows = clean_rows(sorted(rows, key=lambda r: -(r.get("band_min_score") or 0)))
    item = chart_widget(
        "cs-chart-score-bands", "Credit Model Score Bands", rows, cols, sql, "bar",
        "score_band", ["customer_count"],
        build_figure(rows, "score_band", ["customer_count"], "bar"),
        {"x": 0, "y": y, "w": 6, "h": 10, "minW": 4, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])

    rows, cols, sql = _q("credit_limit_dist")
    rows = clean_rows(rows)
    item = chart_widget(
        "cs-chart-credit-limit", "Credit Limit Distribution", rows, cols, sql, "bar",
        "credit_limit", ["customer_count"],
        build_figure(rows, "credit_limit", ["customer_count"], "bar"),
        {"x": 6, "y": y, "w": 6, "h": 10, "minW": 4, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])
    y += 10

    rows, cols, sql = _q("turnover_bands")
    rows = clean_rows(rows)
    item = chart_widget(
        "cs-chart-turnover-bands", "Three-Month Turnover Bands", rows, cols, sql, "bar",
        "turnover_band", ["customer_count"],
        build_figure(rows, "turnover_band", ["customer_count"], "bar"),
        {"x": 0, "y": y, "w": 4, "h": 10, "minW": 3, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])

    rows, cols, sql = _q("age_bands")
    rows = clean_rows(rows)
    item = chart_widget(
        "cs-chart-age", "Statement Age Distribution", rows, cols, sql, "bar",
        "age_band", ["customer_count"],
        build_figure(rows, "age_band", ["customer_count"], "bar"),
        {"x": 4, "y": y, "w": 4, "h": 10, "minW": 3, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])

    rows, cols, sql = _q("dti_bands")
    rows = clean_rows(rows)
    item = chart_widget(
        "cs-chart-dti", "Debt-to-Income Ratio Bands", rows, cols, sql, "bar",
        "dti_band", ["customer_count"],
        build_figure(rows, "dti_band", ["customer_count"], "bar"),
        {"x": 8, "y": y, "w": 4, "h": 10, "minW": 3, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])
    y += 10

    rows, cols, sql = _q("monthly_turnover")
    rows = clean_rows(rows)
    item = chart_widget(
        "cs-chart-monthly-turnover", "Avg Monthly Turnover", rows, cols, sql, "bar",
        "month_label", ["avg_turnover", "median_turnover"],
        build_figure(rows, "month_label", ["avg_turnover", "median_turnover"], "bar"),
        {"x": 0, "y": y, "w": 6, "h": 10, "minW": 4, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])

    rows, cols, sql = _q("credit_vs_fraud")
    rows = clean_rows(rows)
    item = chart_widget(
        "cs-chart-credit-fraud", "Credit Model vs Fraud Outcome", rows, cols, sql, "stacked_bar",
        "model_category", ["customer_count"],
        build_stacked_bar(rows, "model_category", "fraud_decision", "customer_count", _FRAUD_DECISION_ORDER),
        {"x": 6, "y": y, "w": 6, "h": 10, "minW": 4, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])
    y += 10

    rows, cols, sql = _q("daily_volume")
    rows = clean_rows(sorted(rows, key=lambda r: str(r.get("profile_date") or "")))
    item = chart_widget(
        "cs-chart-daily", "Daily Profiling Volume", rows, cols, sql, "line",
        "profile_date", ["qualified_runs", "not_qualified_runs"],
        build_figure(rows, "profile_date", ["qualified_runs", "not_qualified_runs"], "line"),
        {"x": 0, "y": y, "w": 6, "h": 10, "minW": 4, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])

    rows, cols, sql = _q("rejection_reasons")
    rows = clean_rows(rows)
    item = chart_widget(
        "cs-chart-rejection", "Top Rejection Reasons", rows, cols, sql, "bar",
        "reason_code", ["customers_affected"],
        build_figure(rows, "reason_code", ["customers_affected"], "bar"),
        {"x": 6, "y": y, "w": 6, "h": 10, "minW": 4, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])
    y += 10

    rows, cols, sql = _q("segment_matrix")
    rows = clean_rows(rows)
    item = table_widget(
        "cs-table-segment-matrix", "Risk x Turnover Segment Matrix", rows, cols, sql,
        {"x": 0, "y": y, "w": 6, "h": 10, "minW": 4, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])
    y += 10

    rows, cols, sql = _q("recent_activity")
    rows = clean_rows(rows)
    item = table_widget(
        "cs-table-recent", "Recent Profiling Activity", rows, cols, sql,
        {"x": 0, "y": y, "w": 12, "h": 11, "minW": 6, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])
    y += 11

    rows, cols, sql = _q("latest_profiles")
    rows = clean_rows(rows)
    item = table_widget(
        "cs-table-latest", "Latest Profile per Customer", rows, cols, sql,
        {"x": 0, "y": y, "w": 12, "h": 12, "minW": 6, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])
    y += 12

    rows, cols, sql = _q("high_dti")
    rows = clean_rows(rows)
    item = table_widget(
        "cs-table-high-dti", "High DTI Blocked Customers", rows, cols, sql,
        {"x": 0, "y": y, "w": 6, "h": 11, "minW": 4, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])

    rows, cols, sql = _q("qualified_fraud_flagged")
    rows = clean_rows(rows)
    item = table_widget(
        "cs-table-qualified-fraud", "Qualified but Fraud Flagged", rows, cols, sql,
        {"x": 6, "y": y, "w": 6, "h": 11, "minW": 4, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])
    y += 11

    rows, cols, sql = _q("score_drift")
    rows = clean_rows(rows)
    item = table_widget(
        "cs-table-score-drift", "Score & Limit Drift (Re-profiles)", rows, cols, sql,
        {"x": 0, "y": y, "w": 6, "h": 11, "minW": 4, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])

    rows, cols, sql = _q("lender_dependency")
    rows = clean_rows(rows)
    item = table_widget(
        "cs-table-lender-dep", "Lender Dependency by Category", rows, cols, sql,
        {"x": 6, "y": y, "w": 6, "h": 11, "minW": 4, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])

    attach_widget_exports(widgets)
    return widgets, layout


def ensure_subscriber_profiles_dashboard(*, force: bool = False):
    """Create the bundled customer scoring dashboard if missing; optionally rebuild."""
    db = SessionLocal()
    try:
        existing = db.query(Dashboard).filter(Dashboard.name == DASHBOARD_NAME).first()
        if existing and not force:
            if existing.filters != DATE_FILTERS:
                existing.filters = DATE_FILTERS
                db.commit()
            print(f"✅ Customer scoring dashboard persisted (id={existing.id})")
            return existing.id
    finally:
        db.close()

    try:
        widgets, grid_layout = build_dashboard()
    except Exception as exc:
        print(f"⚠️  Customer scoring dashboard build skipped (data DB): {exc}")
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
            print(f"✅ Customer scoring dashboard rebuilt (id={existing.id}, {len(widgets)} widgets)")
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
        print(f"✅ Customer scoring dashboard created (id={dashboard.id}, {len(widgets)} widgets)")
        return dashboard.id
    except Exception as exc:
        print(f"⚠️  Customer scoring dashboard persist failed: {exc}")
        return None
    finally:
        db.close()
