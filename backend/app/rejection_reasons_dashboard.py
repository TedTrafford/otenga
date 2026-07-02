"""Build and persist the Rejection Reasons dashboard (queries remote MPESA_DB_*)."""

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

DATE_FILTERS = default_date_filters("tbl_rejection_reasons.date_created")

DASHBOARD_NAME = "Rejection Reasons Dashboard"
DASHBOARD_DESCRIPTION = (
    "Credit decline drivers, weak scorecard features, reason co-occurrence, "
    "repayment probability, and segment-level rejection patterns."
)

LATEST_PROFILES_CTE = """
WITH _ranked_profiles AS (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY mobile_number ORDER BY last_updated DESC) AS _rn
    FROM tbl_subscriber_profiles
),
latest_profiles AS (
    SELECT id AS profile_id,
           mobile_number,
           last_updated,
           model_category,
           credit_limit,
           total_score AS credit_model_score,
           risk_segment,
           turnover_segment,
           three_month_wavg,
           age_days,
           debt_to_income_ratio,
           total_inflow,
           lender_inflow
    FROM _ranked_profiles
    WHERE _rn = 1
)
"""

QUERIES = {
    "kpi_summary": """
        SELECT
            COUNT(*)                                              AS total_reason_rows,
            COUNT(DISTINCT mobile_number)                         AS customers_with_reasons,
            ROUND(COUNT(*) / NULLIF(COUNT(DISTINCT mobile_number), 0), 2)
                                                                  AS avg_reasons_per_customer,
            SUM(CASE WHEN reason_rank = 1 THEN 1 ELSE 0 END)               AS primary_reason_rows,
            COUNT(DISTINCT reason_code)                           AS distinct_reason_codes,
            COUNT(DISTINCT CASE WHEN feature_name IS NOT NULL AND feature_name <> '' THEN feature_name END)
                                                                  AS distinct_weak_features,
            ROUND(AVG(repayment_probability), 2)         AS avg_repayment_probability,
            ROUND(AVG(CASE WHEN reason_code = 'WEAK_SCORING_FEATURE' THEN score_gap END), 1)
                                                                  AS avg_weak_feature_score_gap,
            MAX(date_created)                                       AS last_reason_at
        FROM tbl_rejection_reasons
        WHERE 1=1 {{date_filter}}
    """,
    "active_rejections": f"""
        {LATEST_PROFILES_CTE}
        SELECT COUNT(DISTINCT rr.mobile_number) AS active_rejected_customers,
               COUNT(*) AS active_reason_rows,
               ROUND(AVG(rr.repayment_probability), 2) AS avg_repayment_probability
        FROM tbl_rejection_reasons rr
        JOIN latest_profiles lp ON lp.mobile_number = rr.mobile_number
        WHERE lp.model_category = 'not_qualified'
    """,
    "reason_code_dist": """
        SELECT reason_code, COUNT(*) AS reason_occurrences,
               COUNT(DISTINCT mobile_number) AS customers_affected,
               ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct_of_all_reasons
        FROM tbl_rejection_reasons
        GROUP BY reason_code
        ORDER BY customers_affected DESC
    """,
    "primary_reason": """
        SELECT reason_code, COUNT(*) AS customer_count,
               ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct
        FROM tbl_rejection_reasons
        WHERE reason_rank = 1
        GROUP BY reason_code
        ORDER BY customer_count DESC
    """,
    "reason_combinations": """
        SELECT reason_combination, COUNT(*) AS customer_count
        FROM (
            SELECT mobile_number,
                   GROUP_CONCAT(reason_code ORDER BY reason_rank SEPARATOR ' + ') AS reason_combination
            FROM tbl_rejection_reasons
            GROUP BY mobile_number
        ) t
        GROUP BY reason_combination
        ORDER BY customer_count DESC
        LIMIT 15
    """,
    "reason_co_occurrence": """
        WITH customer_reasons AS (
            SELECT DISTINCT mobile_number, reason_code FROM tbl_rejection_reasons
        ),
        pairs AS (
            SELECT a.reason_code AS reason_a, b.reason_code AS reason_b,
                   COUNT(*) AS co_occurrence_count
            FROM customer_reasons a
            JOIN customer_reasons b
              ON a.mobile_number = b.mobile_number AND a.reason_code < b.reason_code
            GROUP BY a.reason_code, b.reason_code
        )
        SELECT CONCAT(reason_a, ' + ', reason_b) AS reason_pair, co_occurrence_count
        FROM pairs
        ORDER BY co_occurrence_count DESC
        LIMIT 15
    """,
    "weak_features": """
        SELECT feature_name, COUNT(*) AS customer_count,
               ROUND(AVG(score_gap), 1) AS avg_score_gap,
               ROUND(AVG(repayment_probability), 2) AS avg_repayment_probability
        FROM tbl_rejection_reasons
        WHERE reason_code = 'WEAK_SCORING_FEATURE'
        GROUP BY feature_name
        ORDER BY customer_count DESC
        LIMIT 15
    """,
    "score_gap_bands": """
        SELECT
            CASE
                WHEN score_gap >= 100 THEN '100+ pts (critical)'
                WHEN score_gap >= 90  THEN '90-99 pts'
                WHEN score_gap >= 80  THEN '80-89 pts'
                WHEN score_gap >= 70  THEN '70-79 pts'
                ELSE 'Below 70 pts'
            END AS score_gap_band,
            COUNT(*) AS customer_count,
            ROUND(AVG(score_gap), 1) AS avg_gap_in_band
        FROM tbl_rejection_reasons
        WHERE reason_code = 'WEAK_SCORING_FEATURE' AND score_gap IS NOT NULL
        GROUP BY 1
        ORDER BY avg_gap_in_band DESC
    """,
    "low_turnover_bands": """
        SELECT
            CASE
                WHEN feature_value IS NULL THEN 'Unknown'
                WHEN feature_value <= 9841   THEN 'Seg 1: <= 9,841'
                WHEN feature_value <= 12561  THEN 'Seg 2: 9,842-12,561'
                WHEN feature_value <= 16027  THEN 'Seg 3: 12,562-16,027'
                WHEN feature_value <= 23895  THEN 'Seg 4: 16,028-23,895'
                WHEN feature_value <= 39179  THEN 'Seg 5: 23,896-39,179'
                WHEN feature_value <= 60463  THEN 'Seg 6: 39,180-60,463'
                WHEN feature_value <= 107556 THEN 'Seg 7: 60,464-107,556'
                ELSE 'Seg 8: > 107,556'
            END AS turnover_band,
            COUNT(*) AS customer_count
        FROM tbl_rejection_reasons
        WHERE reason_code = 'LOW_TURNOVER'
        GROUP BY 1
        ORDER BY customer_count DESC
    """,
    "high_credit_risk_bands": """
        SELECT
            CASE
                WHEN feature_value >= 831 THEN '831-852 (G4 near threshold)'
                WHEN feature_value >= 808 THEN '808-830 (G3)'
                WHEN feature_value >= 776 THEN '776-807 (G2)'
                ELSE 'Below 776 (G1)'
            END AS score_band,
            COUNT(*) AS customer_count
        FROM tbl_rejection_reasons
        WHERE reason_code = 'HIGH_CREDIT_RISK' AND feature_value IS NOT NULL
        GROUP BY 1
        ORDER BY customer_count DESC
    """,
    "repayment_by_reason": """
        SELECT reason_code, COUNT(*) AS reason_occurrences,
               ROUND(AVG(repayment_probability), 2) AS avg_repayment_probability,
               ROUND(MIN(repayment_probability), 2) AS min_repayment_probability
        FROM tbl_rejection_reasons
        GROUP BY reason_code
        ORDER BY avg_repayment_probability ASC
    """,
    "repayment_bands": """
        SELECT
            CASE
                WHEN repayment_probability >= 99 THEN '99%+'
                WHEN repayment_probability >= 98 THEN '98-98.9%'
                WHEN repayment_probability >= 97 THEN '97-97.9%'
                WHEN repayment_probability >= 95 THEN '95-96.9%'
                ELSE 'Below 95%'
            END AS repayment_prob_band,
            COUNT(*) AS reason_occurrences,
            COUNT(DISTINCT mobile_number) AS customers_affected
        FROM tbl_rejection_reasons
        WHERE repayment_probability IS NOT NULL
        GROUP BY 1
        ORDER BY MIN(repayment_probability) DESC
    """,
    "primary_reason_by_risk": f"""
        {LATEST_PROFILES_CTE}
        SELECT lp.risk_segment, rr.reason_code, COUNT(*) AS customer_count
        FROM tbl_rejection_reasons rr
        JOIN latest_profiles lp ON lp.mobile_number = rr.mobile_number
        WHERE lp.model_category = 'not_qualified' AND rr.reason_rank = 1
        GROUP BY lp.risk_segment, rr.reason_code
        ORDER BY lp.risk_segment, customer_count DESC
    """,
    "daily_volume": """
        SELECT DATE(date_created) AS reason_date,
               COUNT(*) AS reason_rows,
               COUNT(DISTINCT mobile_number) AS distinct_customers,
               SUM(CASE WHEN reason_code = 'WEAK_SCORING_FEATURE' THEN 1 ELSE 0 END) AS weak_feature_count,
               SUM(CASE WHEN reason_code = 'LOW_TURNOVER' THEN 1 ELSE 0 END) AS low_turnover_count,
               SUM(CASE WHEN reason_code = 'HIGH_CREDIT_RISK' THEN 1 ELSE 0 END) AS high_credit_risk_count
        FROM tbl_rejection_reasons
        GROUP BY DATE(date_created)
        ORDER BY reason_date DESC
        LIMIT 60
    """,
    "weak_feature_watchlist": """
        SELECT mobile_number, feature_name, feature_value,
               score_actual, score_max, score_gap,
               repayment_probability, LEFT(reason_detail, 100) AS reason_detail, date_created
        FROM tbl_rejection_reasons
        WHERE reason_code = 'WEAK_SCORING_FEATURE' AND reason_rank = 1
        ORDER BY score_gap DESC, repayment_probability ASC
        LIMIT 50
    """,
    "high_credit_risk_watchlist": """
        SELECT rr.mobile_number, rr.feature_value AS total_score,
               rr.repayment_probability, lp.risk_segment, lp.turnover_segment,
               lp.three_month_wavg, LEFT(rr.reason_detail, 100) AS reason_detail, rr.date_created
        FROM tbl_rejection_reasons rr
        LEFT JOIN (
            SELECT * FROM (
    SELECT mobile_number, risk_segment, turnover_segment, three_month_wavg,
           ROW_NUMBER() OVER (PARTITION BY mobile_number ORDER BY last_updated DESC) AS _rn
    FROM tbl_subscriber_profiles
) _lp WHERE _rn = 1
        ) lp ON lp.mobile_number = rr.mobile_number
        WHERE rr.reason_code = 'HIGH_CREDIT_RISK'
        ORDER BY rr.feature_value DESC
        LIMIT 50
    """,
    "lowest_repayment": """
        SELECT mobile_number, reason_rank, reason_code, repayment_probability,
               feature_name, feature_value, score_gap, date_created
        FROM tbl_rejection_reasons
        ORDER BY repayment_probability ASC, score_gap IS NULL, score_gap DESC
        LIMIT 50
    """,
    "high_dti": f"""
        {LATEST_PROFILES_CTE}
        SELECT rr.mobile_number, rr.feature_value AS dti_ratio,
               lp.total_inflow, lp.lender_inflow, lp.credit_model_score,
               rr.repayment_probability, LEFT(rr.reason_detail, 100) AS reason_detail, rr.date_created
        FROM tbl_rejection_reasons rr
        LEFT JOIN latest_profiles lp ON lp.mobile_number = rr.mobile_number
        WHERE rr.reason_code = 'HIGH_DEBT_TO_INCOME_RATIO'
        ORDER BY rr.feature_value DESC
        LIMIT 50
    """,
    "fraud_critical": """
        SELECT rr.mobile_number, fr.total_score AS fraud_score, fr.decision AS fraud_decision,
               fr.triggered_rules, rr.repayment_probability,
               LEFT(rr.reason_detail, 100) AS reason_detail, rr.date_created
        FROM tbl_rejection_reasons rr
        JOIN tbl_fraud_rules fr ON fr.mobile_number = rr.mobile_number
        WHERE rr.reason_code = 'FRAUD_CRITICAL'
        ORDER BY fr.total_score DESC
        LIMIT 50
    """,
    "unified_rejections": f"""
        {LATEST_PROFILES_CTE}
        SELECT rr.mobile_number, lp.credit_model_score, lp.risk_segment, lp.turnover_segment,
               lp.three_month_wavg, lp.debt_to_income_ratio,
               rr.reason_rank, rr.reason_code, rr.feature_name, rr.feature_value,
               rr.score_gap, rr.repayment_probability,
               LEFT(rr.reason_detail, 120) AS reason_detail_preview, rr.date_created
        FROM tbl_rejection_reasons rr
        LEFT JOIN latest_profiles lp ON lp.mobile_number = rr.mobile_number
        WHERE lp.model_category = 'not_qualified' OR lp.mobile_number IS NULL
        ORDER BY rr.repayment_probability ASC, rr.reason_rank, rr.mobile_number
        LIMIT 200
    """,
    "recent_activity": """
        SELECT id, mobile_number, reason_rank, reason_code, feature_name,
               score_gap, repayment_probability,
               LEFT(reason_detail, 80) AS reason_preview, date_created
        FROM tbl_rejection_reasons
        ORDER BY date_created DESC, id DESC
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
        ("rr-kpi-customers", "Customers with Reasons", "customers_with_reasons"),
        ("rr-kpi-total-rows", "Total Reason Rows", "total_reason_rows"),
        ("rr-kpi-avg-reasons", "Avg Reasons / Customer", "avg_reasons_per_customer"),
        ("rr-kpi-reason-codes", "Distinct Reason Codes", "distinct_reason_codes"),
        ("rr-kpi-weak-features", "Weak Score Features", "distinct_weak_features"),
        ("rr-kpi-avg-repay", "Avg Repayment Prob %", "avg_repayment_probability"),
        ("rr-kpi-avg-gap", "Avg Weak Feature Gap", "avg_weak_feature_score_gap"),
        ("rr-kpi-primary", "Primary Reason Rows", "primary_reason_rows"),
    ]):
        item = metric_widget(
            wid, title, col, kpi_rows, kpi_sql,
            {"x": (i % 4) * 3, "y": y + (i // 4) * 5, "w": 3, "h": 5, "minW": 2, "minH": 4},
        )
        widgets.append(item["widget"])
        layout.append(item["layout"])
    y += 10

    rows, cols, sql = _q("reason_code_dist")
    rows = clean_rows(rows)
    item = chart_widget(
        "rr-chart-reason-codes", "Reason Code Distribution", rows, cols, sql, "pie",
        "reason_code", ["customers_affected"],
        build_figure(rows, "reason_code", ["customers_affected"], "pie"),
        {"x": 0, "y": y, "w": 4, "h": 10, "minW": 3, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])

    rows, cols, sql = _q("primary_reason")
    rows = clean_rows(rows)
    item = chart_widget(
        "rr-chart-primary", "Primary Reason (Rank 1)", rows, cols, sql, "pie",
        "reason_code", ["customer_count"],
        build_figure(rows, "reason_code", ["customer_count"], "pie"),
        {"x": 4, "y": y, "w": 4, "h": 10, "minW": 3, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])

    rows, cols, sql = _q("repayment_bands")
    rows = clean_rows(rows)
    item = chart_widget(
        "rr-chart-repay-bands", "Repayment Probability Bands", rows, cols, sql, "bar",
        "repayment_prob_band", ["customers_affected"],
        build_figure(rows, "repayment_prob_band", ["customers_affected"], "bar"),
        {"x": 8, "y": y, "w": 4, "h": 10, "minW": 3, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])
    y += 10

    rows, cols, sql = _q("weak_features")
    rows = clean_rows(rows)
    item = chart_widget(
        "rr-chart-weak-features", "Top Weak Scorecard Features", rows, cols, sql, "bar",
        "feature_name", ["customer_count"],
        build_figure(rows, "feature_name", ["customer_count"], "bar"),
        {"x": 0, "y": y, "w": 6, "h": 10, "minW": 4, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])

    rows, cols, sql = _q("score_gap_bands")
    rows = clean_rows(rows)
    item = chart_widget(
        "rr-chart-score-gap", "Weak Feature Score Gap Bands", rows, cols, sql, "bar",
        "score_gap_band", ["customer_count"],
        build_figure(rows, "score_gap_band", ["customer_count"], "bar"),
        {"x": 6, "y": y, "w": 6, "h": 10, "minW": 4, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])
    y += 10

    rows, cols, sql = _q("reason_combinations")
    rows = clean_rows(rows)
    item = chart_widget(
        "rr-chart-combinations", "Reason Combinations per Customer", rows, cols, sql, "bar",
        "reason_combination", ["customer_count"],
        build_figure(rows, "reason_combination", ["customer_count"], "bar"),
        {"x": 0, "y": y, "w": 6, "h": 10, "minW": 4, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])

    rows, cols, sql = _q("reason_co_occurrence")
    rows = clean_rows(rows)
    item = chart_widget(
        "rr-chart-co-occur", "Co-occurring Reason Pairs", rows, cols, sql, "bar",
        "reason_pair", ["co_occurrence_count"],
        build_figure(rows, "reason_pair", ["co_occurrence_count"], "bar"),
        {"x": 6, "y": y, "w": 6, "h": 10, "minW": 4, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])
    y += 10

    rows, cols, sql = _q("repayment_by_reason")
    rows = clean_rows(rows)
    item = chart_widget(
        "rr-chart-repay-reason", "Avg Repayment Prob by Reason", rows, cols, sql, "bar",
        "reason_code", ["avg_repayment_probability"],
        build_figure(rows, "reason_code", ["avg_repayment_probability"], "bar"),
        {"x": 0, "y": y, "w": 4, "h": 10, "minW": 3, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])

    rows, cols, sql = _q("low_turnover_bands")
    rows = clean_rows(rows)
    item = chart_widget(
        "rr-chart-low-turnover", "LOW_TURNOVER by Turnover Band", rows, cols, sql, "bar",
        "turnover_band", ["customer_count"],
        build_figure(rows, "turnover_band", ["customer_count"], "bar"),
        {"x": 4, "y": y, "w": 4, "h": 10, "minW": 3, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])

    rows, cols, sql = _q("high_credit_risk_bands")
    rows = clean_rows(rows)
    item = chart_widget(
        "rr-chart-high-risk", "HIGH_CREDIT_RISK Score Bands", rows, cols, sql, "bar",
        "score_band", ["customer_count"],
        build_figure(rows, "score_band", ["customer_count"], "bar"),
        {"x": 8, "y": y, "w": 4, "h": 10, "minW": 3, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])
    y += 10

    rows, cols, sql = _q("primary_reason_by_risk")
    rows = clean_rows(rows)
    item = chart_widget(
        "rr-chart-risk-reason", "Primary Reason by Risk Segment", rows, cols, sql, "stacked_bar",
        "risk_segment", ["customer_count"],
        build_stacked_bar(rows, "risk_segment", "reason_code", "customer_count"),
        {"x": 0, "y": y, "w": 6, "h": 10, "minW": 4, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])

    rows, cols, sql = _q("daily_volume")
    rows = clean_rows(sorted(rows, key=lambda r: str(r.get("reason_date") or "")))
    item = chart_widget(
        "rr-chart-daily", "Daily Rejection Reason Volume", rows, cols, sql, "line",
        "reason_date", ["weak_feature_count", "low_turnover_count", "high_credit_risk_count"],
        build_figure(rows, "reason_date", ["weak_feature_count", "low_turnover_count", "high_credit_risk_count"], "line"),
        {"x": 6, "y": y, "w": 6, "h": 10, "minW": 4, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])
    y += 10

    rows, cols, sql = _q("recent_activity")
    rows = clean_rows(rows)
    item = table_widget(
        "rr-table-recent", "Recent Rejection Activity", rows, cols, sql,
        {"x": 0, "y": y, "w": 12, "h": 11, "minW": 6, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])
    y += 11

    rows, cols, sql = _q("unified_rejections")
    rows = clean_rows(rows)
    item = table_widget(
        "rr-table-unified", "Active Rejections with Profile Context", rows, cols, sql,
        {"x": 0, "y": y, "w": 12, "h": 12, "minW": 6, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])
    y += 12

    rows, cols, sql = _q("weak_feature_watchlist")
    rows = clean_rows(rows)
    item = table_widget(
        "rr-table-weak", "Weak Feature Watchlist (Largest Gaps)", rows, cols, sql,
        {"x": 0, "y": y, "w": 6, "h": 11, "minW": 4, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])

    rows, cols, sql = _q("high_credit_risk_watchlist")
    rows = clean_rows(rows)
    item = table_widget(
        "rr-table-high-risk", "HIGH_CREDIT_RISK Watchlist", rows, cols, sql,
        {"x": 6, "y": y, "w": 6, "h": 11, "minW": 4, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])
    y += 11

    rows, cols, sql = _q("lowest_repayment")
    rows = clean_rows(rows)
    item = table_widget(
        "rr-table-low-repay", "Lowest Repayment Probability", rows, cols, sql,
        {"x": 0, "y": y, "w": 6, "h": 11, "minW": 4, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])

    rows, cols, sql = _q("high_dti")
    rows = clean_rows(rows)
    item = table_widget(
        "rr-table-high-dti", "HIGH_DEBT_TO_INCOME_RATIO", rows, cols, sql,
        {"x": 6, "y": y, "w": 6, "h": 11, "minW": 4, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])
    y += 11

    rows, cols, sql = _q("fraud_critical")
    rows = clean_rows(rows)
    item = table_widget(
        "rr-table-fraud", "FRAUD_CRITICAL Rejections", rows, cols, sql,
        {"x": 0, "y": y, "w": 12, "h": 10, "minW": 6, "minH": 6},
    )
    widgets.append(item["widget"]); layout.append(item["layout"])

    attach_widget_exports(widgets)
    return widgets, layout


def ensure_rejection_reasons_dashboard(*, force: bool = False):
    """Create the bundled rejection reasons dashboard if missing; optionally rebuild."""
    db = SessionLocal()
    try:
        existing = db.query(Dashboard).filter(Dashboard.name == DASHBOARD_NAME).first()
        if existing and not force:
            if existing.filters != DATE_FILTERS:
                existing.filters = DATE_FILTERS
                db.commit()
            print(f"✅ Rejection reasons dashboard persisted (id={existing.id})")
            return existing.id
    finally:
        db.close()

    try:
        widgets, grid_layout = build_dashboard()
    except Exception as exc:
        print(f"⚠️  Rejection reasons dashboard build skipped (data DB): {exc}")
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
            print(f"✅ Rejection reasons dashboard rebuilt (id={existing.id}, {len(widgets)} widgets)")
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
        print(f"✅ Rejection reasons dashboard created (id={dashboard.id}, {len(widgets)} widgets)")
        return dashboard.id
    except Exception as exc:
        print(f"⚠️  Rejection reasons dashboard persist failed: {exc}")
        return None
    finally:
        db.close()
