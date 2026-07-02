"""Build and persist the Fraud Rules dashboard (queries remote MPESA_DB_*)."""

from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm.attributes import flag_modified

from .database import SessionLocal, engine, Base
from .execution_engine import _get_mysql_engine
from .dashboard_date_filter import default_date_filters
from .dashboard_widgets import attach_widget_exports
from .models import Dashboard, NotebookStatus

FRAUD_DATE_FILTERS = default_date_filters("tbl_fraud_rules.evaluated_at")

FRAUD_DASHBOARD_NAME = "Fraud Rules Dashboard"
FRAUD_DASHBOARD_DESCRIPTION = (
    "Fraud rules KPIs, decision breakdown, rule triggers, and customer watchlists."
)

PALETTE = ["#00D4FF", "#7C3AED", "#06FFA5", "#FF4D6D", "#FFB800", "#EC4899", "#34D399", "#F97316"]

QUERIES = {
    "kpi_summary": """
        SELECT
            COUNT(*)                                              AS customers_evaluated,
            SUM(CASE WHEN decision = 'Reject' THEN 1 ELSE 0 END)           AS reject_count,
            SUM(CASE WHEN decision = 'Manual Review' THEN 1 ELSE 0 END)    AS manual_review_count,
            SUM(CASE WHEN decision = 'Reduce Limit' THEN 1 ELSE 0 END)     AS reduce_limit_count,
            SUM(CASE WHEN decision = 'Approve' THEN 1 ELSE 0 END)          AS approve_count,
            ROUND(100.0 * SUM(CASE WHEN decision = 'Reject' THEN 1 ELSE 0 END)
                  / NULLIF(COUNT(*), 0), 1)                       AS reject_rate_pct,
            ROUND(AVG(total_score), 1)                            AS avg_fraud_score,
            MAX(total_score)                                      AS max_fraud_score,
            MAX(evaluated_at)                                     AS last_evaluated_at
        FROM tbl_fraud_rules
        WHERE 1=1 {{date_filter}}
    """,
    "decision_distribution": """
        SELECT decision, COUNT(*) AS customer_count,
               ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct
        FROM tbl_fraud_rules
        GROUP BY decision
        ORDER BY CASE decision
            WHEN 'Reject' THEN 1 WHEN 'Manual Review' THEN 2
            WHEN 'Reduce Limit' THEN 3 WHEN 'Approve' THEN 4 ELSE 5 END
    """,
    "credit_vs_fraud": """
        WITH _ranked_profiles AS (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY mobile_number ORDER BY last_updated DESC) AS _rn
    FROM tbl_subscriber_profiles
),
latest_profiles AS (
    SELECT mobile_number, model_category, credit_limit,
                   total_score AS credit_model_score, risk_segment, turnover_segment
    FROM _ranked_profiles
    WHERE _rn = 1
)
        SELECT lp.model_category, fr.decision AS fraud_decision,
               COUNT(*) AS customer_count,
               ROUND(AVG(lp.credit_model_score), 1) AS avg_credit_model_score,
               ROUND(AVG(fr.total_score), 1) AS avg_fraud_score
        FROM latest_profiles lp
        JOIN tbl_fraud_rules fr ON fr.mobile_number = lp.mobile_number
        GROUP BY lp.model_category, fr.decision
        ORDER BY customer_count DESC
    """,
    "score_distribution": """
        SELECT
            CASE
                WHEN total_score >= 80 THEN '80+ Reject'
                WHEN total_score >= 60 THEN '60-79 Manual Review'
                WHEN total_score >= 40 THEN '40-59 Reduce Limit'
                ELSE '0-39 Approve'
            END AS score_band,
            COUNT(*) AS customer_count
        FROM tbl_fraud_rules
        GROUP BY 1
        ORDER BY MIN(total_score) DESC
    """,
    "rule_frequency": """
        SELECT rule_name, rule_category, rule_weight, customers_flagged,
               ROUND(100.0 * customers_flagged / NULLIF((SELECT COUNT(*) FROM tbl_fraud_rules), 0), 1) AS pct_of_portfolio
        FROM (
            SELECT 'Device Multi-ID Linkage' AS rule_name, 'Identity & Device' AS rule_category, 40 AS rule_weight,
                   SUM(CASE WHEN flag_device_multi_id THEN 1 ELSE 0 END) AS customers_flagged FROM tbl_fraud_rules
            UNION ALL SELECT 'SIM/Phone Recency Check', 'Identity & Device', 25, SUM(CASE WHEN flag_sim_phone_recency THEN 1 ELSE 0 END) FROM tbl_fraud_rules
            UNION ALL SELECT 'Network Concentration Analysis', 'Statement & Velocity', 30, SUM(CASE WHEN flag_network_concentration THEN 1 ELSE 0 END) FROM tbl_fraud_rules
            UNION ALL SELECT 'Circular Cash Movement', 'Statement & Velocity', 10, SUM(CASE WHEN flag_circular_cash_movement THEN 1 ELSE 0 END) FROM tbl_fraud_rules
            UNION ALL SELECT 'Shared Counterparties', 'Statement & Velocity', 20, SUM(CASE WHEN flag_shared_counterparties THEN 1 ELSE 0 END) FROM tbl_fraud_rules
            UNION ALL SELECT 'Sudden Income Inflation', 'Statement & Velocity', 15, SUM(CASE WHEN flag_sudden_income_inflation THEN 1 ELSE 0 END) FROM tbl_fraud_rules
            UNION ALL SELECT 'Borrowing for Betting', 'Credit Distress', 20, SUM(CASE WHEN flag_borrowing_for_betting THEN 1 ELSE 0 END) FROM tbl_fraud_rules
            UNION ALL SELECT 'Loan Cycling Behavior', 'Credit Distress', 15, SUM(CASE WHEN flag_loan_cycling THEN 1 ELSE 0 END) FROM tbl_fraud_rules
            UNION ALL SELECT 'High Gambling Exposure', 'Credit Distress', 15, SUM(CASE WHEN flag_high_gambling_exposure THEN 1 ELSE 0 END) FROM tbl_fraud_rules
            UNION ALL SELECT 'Active Loan Stacking', 'Credit Distress', 15, SUM(CASE WHEN flag_active_loan_stacking THEN 1 ELSE 0 END) FROM tbl_fraud_rules
            UNION ALL SELECT 'Excessive Borrowing Dependency', 'Credit Distress', 10, SUM(CASE WHEN flag_excessive_borrowing_dependency THEN 1 ELSE 0 END) FROM tbl_fraud_rules
            UNION ALL SELECT 'High Volume, Low Balance', 'Credit Distress', 10, SUM(CASE WHEN flag_high_volume_low_balance THEN 1 ELSE 0 END) FROM tbl_fraud_rules
        ) r
        ORDER BY customers_flagged DESC, rule_weight DESC
    """,
    "category_flags": """
        SELECT 'Identity & Device' AS rule_category,
               SUM(CASE WHEN flag_device_multi_id OR flag_sim_phone_recency THEN 1 ELSE 0 END) AS customers_with_any_flag
        FROM tbl_fraud_rules
        UNION ALL
        SELECT 'Statement & Velocity',
               SUM(CASE WHEN flag_network_concentration OR flag_circular_cash_movement
                                    OR flag_shared_counterparties OR flag_sudden_income_inflation THEN 1 ELSE 0 END)
        FROM tbl_fraud_rules
        UNION ALL
        SELECT 'Credit Distress',
               SUM(CASE WHEN flag_borrowing_for_betting OR flag_loan_cycling
                                    OR flag_high_gambling_exposure OR flag_active_loan_stacking
                                    OR flag_excessive_borrowing_dependency OR flag_high_volume_low_balance THEN 1 ELSE 0 END)
        FROM tbl_fraud_rules
    """,
    "watchlist": """
        WITH _ranked_profiles AS (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY mobile_number ORDER BY last_updated DESC) AS _rn
    FROM tbl_subscriber_profiles
),
latest_profiles AS (
    SELECT mobile_number, credit_limit, model_category, risk_segment, turnover_segment,
                   total_score AS credit_model_score
    FROM _ranked_profiles
    WHERE _rn = 1
)
        SELECT fr.mobile_number, fr.total_score AS fraud_score, fr.decision AS fraud_decision,
               fr.triggered_rules, fr.statement_span_days, lp.credit_limit, lp.model_category,
               lp.credit_model_score, lp.risk_segment, lp.turnover_segment, fr.evaluated_at
        FROM tbl_fraud_rules fr
        LEFT JOIN latest_profiles lp ON lp.mobile_number = fr.mobile_number
        WHERE fr.decision IN ('Reject', 'Manual Review')
        ORDER BY fr.total_score DESC, fr.evaluated_at DESC
    """,
    "scatter_credit_fraud": """
        WITH _ranked_profiles AS (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY mobile_number ORDER BY last_updated DESC) AS _rn
    FROM tbl_subscriber_profiles
),
latest_profiles AS (
    SELECT mobile_number, risk_segment, turnover_segment, model_category
    FROM _ranked_profiles
    WHERE _rn = 1
)
        SELECT fr.mobile_number, fr.total_score AS fraud_score, fr.decision AS fraud_decision,
               ccl.credit_limit, ccl.profiling_category, lp.risk_segment, lp.turnover_segment, lp.model_category
        FROM tbl_fraud_rules fr
        LEFT JOIN customer_credit_limit ccl ON ccl.mobile_number = fr.mobile_number
        LEFT JOIN latest_profiles lp ON lp.mobile_number = fr.mobile_number
    """,
    "fraud_critical": """
        SELECT fr.mobile_number, fr.total_score, fr.decision, fr.triggered_rules,
               rr.reason_code, rr.reason_detail, rr.repayment_probability, rr.date_created AS reason_created_at
        FROM tbl_fraud_rules fr
        JOIN tbl_rejection_reasons rr
          ON rr.mobile_number = fr.mobile_number AND rr.reason_code = 'FRAUD_CRITICAL'
        WHERE fr.decision = 'Reject'
        ORDER BY fr.total_score DESC
    """,
    "co_occurring": """
        WITH rule_flags AS (
            SELECT mobile_number, 'Device Multi-ID' AS rule_name FROM tbl_fraud_rules WHERE flag_device_multi_id
            UNION ALL SELECT mobile_number, 'SIM Recency' FROM tbl_fraud_rules WHERE flag_sim_phone_recency
            UNION ALL SELECT mobile_number, 'Network Conc' FROM tbl_fraud_rules WHERE flag_network_concentration
            UNION ALL SELECT mobile_number, 'Circular Cash' FROM tbl_fraud_rules WHERE flag_circular_cash_movement
            UNION ALL SELECT mobile_number, 'Shared CP' FROM tbl_fraud_rules WHERE flag_shared_counterparties
            UNION ALL SELECT mobile_number, 'Income Inflation' FROM tbl_fraud_rules WHERE flag_sudden_income_inflation
            UNION ALL SELECT mobile_number, 'Borrow for Bet' FROM tbl_fraud_rules WHERE flag_borrowing_for_betting
            UNION ALL SELECT mobile_number, 'Loan Cycling' FROM tbl_fraud_rules WHERE flag_loan_cycling
            UNION ALL SELECT mobile_number, 'Gambling' FROM tbl_fraud_rules WHERE flag_high_gambling_exposure
            UNION ALL SELECT mobile_number, 'Loan Stacking' FROM tbl_fraud_rules WHERE flag_active_loan_stacking
            UNION ALL SELECT mobile_number, 'Borrowing Dep' FROM tbl_fraud_rules WHERE flag_excessive_borrowing_dependency
            UNION ALL SELECT mobile_number, 'Low Balance' FROM tbl_fraud_rules WHERE flag_high_volume_low_balance
        ),
        pairs AS (
            SELECT a.rule_name AS rule_a, b.rule_name AS rule_b, COUNT(*) AS co_occurrence_count
            FROM rule_flags a
            JOIN rule_flags b ON a.mobile_number = b.mobile_number
             AND a.rule_name IS NOT NULL AND b.rule_name IS NOT NULL AND a.rule_name < b.rule_name
            GROUP BY a.rule_name, b.rule_name
        )
        SELECT CONCAT(rule_a, ' + ', rule_b) AS rule_pair, co_occurrence_count FROM pairs
        ORDER BY co_occurrence_count DESC LIMIT 15
    """,
    "unified_customers": """
        WITH _ranked_profiles AS (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY mobile_number ORDER BY last_updated DESC) AS _rn
    FROM tbl_subscriber_profiles
),
latest_profiles AS (
    SELECT mobile_number, last_updated AS profiled_at, model_category, credit_limit,
                   total_score AS credit_model_score, risk_segment, turnover_segment,
                   three_month_wavg, debt_to_income_ratio
    FROM _ranked_profiles
    WHERE _rn = 1
)
        SELECT lp.mobile_number, lp.model_category, lp.credit_model_score, lp.credit_limit,
               lp.risk_segment, fr.total_score AS fraud_score, fr.decision AS fraud_decision,
               fr.triggered_rules,
               CASE
                   WHEN lp.model_category = 'qualified' AND fr.decision = 'Approve' THEN 'Pass Both'
                   WHEN lp.model_category = 'qualified' AND fr.decision <> 'Approve' THEN 'Pass Credit / Fail Fraud'
                   WHEN lp.model_category = 'not_qualified' AND fr.decision = 'Approve' THEN 'Fail Credit / Pass Fraud'
                   ELSE 'Fail Both or Review'
               END AS combined_outcome
        FROM latest_profiles lp
        LEFT JOIN tbl_fraud_rules fr ON fr.mobile_number = lp.mobile_number
        LEFT JOIN customer_credit_limit ccl ON ccl.mobile_number = lp.mobile_number
        ORDER BY fr.total_score IS NULL, fr.total_score DESC, lp.mobile_number
    """,
    "behavioural_metrics": """
        SELECT decision, COUNT(*) AS n,
               ROUND(AVG(CAST(JSON_UNQUOTE(JSON_EXTRACT(metrics, '$.gambling_exposure_ratio')) AS DECIMAL(20,4))), 4) AS avg_gambling_ratio,
               ROUND(AVG(CAST(JSON_UNQUOTE(JSON_EXTRACT(metrics, '$.borrowing_dependency_ratio')) AS DECIMAL(20,4))), 4) AS avg_borrowing_dep_ratio,
               ROUND(AVG(CAST(JSON_UNQUOTE(JSON_EXTRACT(metrics, '$.income_inflation_ratio')) AS DECIMAL(20,4))), 4) AS avg_income_inflation_ratio,
               ROUND(AVG(CAST(JSON_UNQUOTE(JSON_EXTRACT(metrics, '$.loan_cycle_count')) AS DECIMAL(20,4))), 1) AS avg_loan_cycles,
               ROUND(AVG(statement_span_days), 0) AS avg_statement_span_days
        FROM tbl_fraud_rules
        GROUP BY decision
        ORDER BY CASE decision WHEN 'Reject' THEN 1 WHEN 'Manual Review' THEN 2
            WHEN 'Reduce Limit' THEN 3 ELSE 4 END
    """,
}


def run_query(key: str):
    engine = _get_mysql_engine()
    template_sql = QUERIES[key].strip()
    executable_sql = template_sql.replace("{{date_filter}}", "")
    with engine.connect() as conn:
        result = conn.execute(text(executable_sql))
        rows = [dict(row._mapping) for row in result]
        columns = list(result.keys()) if rows else []
    return rows, columns, template_sql


def _serialize(val):
    if val is None:
        return None
    if isinstance(val, Decimal):
        return float(val)
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return val


def clean_rows(rows):
    return [{k: _serialize(v) for k, v in row.items()} for row in rows]


def build_figure(rows, x_col, y_cols, chart_type, title=""):
    if not rows or not x_col or not y_cols:
        return None
    sorted_rows = sorted(rows, key=lambda r: str(r.get(x_col) or ""))
    x_vals = [str(r.get(x_col) or "") for r in sorted_rows]

    if chart_type == "pie":
        traces = [{
            "type": "pie",
            "labels": x_vals,
            "values": [float(r.get(y_cols[0]) or 0) for r in sorted_rows],
            "marker": {"colors": PALETTE},
            "textinfo": "label+percent",
        }]
        return {"data": traces, "layout": {"title": {"text": title, "font": {"color": "#94A3B8", "size": 13}}, "showlegend": True}}

    traces = []
    for i, y_col in enumerate(y_cols):
        color = PALETTE[i % len(PALETTE)]
        y_vals = [None if r.get(y_col) is None else float(r.get(y_col) or 0) for r in sorted_rows]
        base = {"x": x_vals, "y": y_vals, "name": y_col, "hovertemplate": "%{x}: %{y:,.2f}<extra></extra>"}
        if chart_type in ("bar", "stacked_bar"):
            traces.append({**base, "type": "bar", "marker": {"color": color, "opacity": 0.9}})
        elif chart_type == "line":
            traces.append({**base, "type": "scatter", "mode": "lines+markers", "line": {"color": color, "width": 2.5}})
        elif chart_type == "scatter":
            traces.append({**base, "type": "scatter", "mode": "markers", "marker": {"color": color, "size": 9, "opacity": 0.8}})
        else:
            traces.append({**base, "type": "bar", "marker": {"color": color}})

    barmode = "stack" if chart_type == "stacked_bar" else "group" if chart_type == "bar" else None
    layout = {"title": {"text": title, "font": {"color": "#94A3B8", "size": 13}}, "showlegend": len(y_cols) > 1}
    if barmode:
        layout["barmode"] = barmode
    return {"data": traces, "layout": layout}


def build_stacked_by_decision(rows):
    """Pivot credit_vs_fraud rows into stacked bar figData."""
    if not rows:
        return None
    categories = sorted({r["model_category"] for r in rows})
    decisions = sorted({r["fraud_decision"] for r in rows}, key=lambda d: {
        "Reject": 1, "Manual Review": 2, "Reduce Limit": 3, "Approve": 4
    }.get(d, 5))
    lookup = {(r["model_category"], r["fraud_decision"]): r["customer_count"] for r in rows}
    traces = []
    for i, decision in enumerate(decisions):
        color = PALETTE[i % len(PALETTE)]
        traces.append({
            "type": "bar",
            "name": decision,
            "x": categories,
            "y": [lookup.get((cat, decision), 0) for cat in categories],
            "marker": {"color": color, "opacity": 0.9},
        })
    return {"data": traces, "layout": {"barmode": "stack", "showlegend": True}}


def metric_widget(widget_id, title, col, rows, sql, layout):
    val = rows[0].get(col) if rows else None
    if val is not None and not isinstance(val, str):
        val = f"{val:,}" if isinstance(val, int) else str(val)
    return {
        "widget": {
            "id": widget_id, "type": "metric", "title": title, "sql": sql,
            "rows": rows, "columns": list(rows[0].keys()) if rows else [],
            "metaCol": col, "label": title, "value": str(val) if val is not None else "—",
        },
        "layout": {**layout, "i": widget_id},
    }


def chart_widget(widget_id, title, rows, columns, sql, chart_type, x_col, y_cols, fig_data, layout):
    return {
        "widget": {
            "id": widget_id, "type": "chart", "title": title, "sql": sql,
            "rows": rows, "columns": columns, "chartType": chart_type,
            "xCol": x_col, "yCols": y_cols, "figData": fig_data,
        },
        "layout": {**layout, "i": widget_id},
    }


def table_widget(widget_id, title, rows, columns, sql, layout):
    return {
        "widget": {
            "id": widget_id, "type": "table", "title": title, "sql": sql,
            "rows": rows, "columns": columns,
        },
        "layout": {**layout, "i": widget_id},
    }


def build_dashboard():
    widgets = []
    layout = []
    y = 0

    kpi_rows, kpi_cols, kpi_sql = run_query("kpi_summary")
    kpi_rows = clean_rows(kpi_rows)
    for i, (wid, title, col) in enumerate([
        ("fraud-kpi-customers", "Customers Evaluated", "customers_evaluated"),
        ("fraud-kpi-reject", "Rejections", "reject_count"),
        ("fraud-kpi-manual", "Manual Review", "manual_review_count"),
        ("fraud-kpi-reduce", "Reduce Limit", "reduce_limit_count"),
        ("fraud-kpi-approve", "Approved", "approve_count"),
        ("fraud-kpi-reject-rate", "Reject Rate %", "reject_rate_pct"),
        ("fraud-kpi-avg-score", "Avg Fraud Score", "avg_fraud_score"),
        ("fraud-kpi-max-score", "Max Fraud Score", "max_fraud_score"),
    ]):
        item = metric_widget(wid, title, col, kpi_rows, kpi_sql, {"x": (i % 4) * 3, "y": y + (i // 4) * 5, "w": 3, "h": 5, "minW": 2, "minH": 4})
        widgets.append(item["widget"])
        layout.append(item["layout"])
    y += 10

    rows, cols, sql = run_query("decision_distribution")
    rows = clean_rows(rows)
    item = chart_widget("fraud-chart-decisions", "Decision Distribution", rows, cols, sql, "pie", "decision", ["customer_count"],
                        build_figure(rows, "decision", ["customer_count"], "pie"), {"x": 0, "y": y, "w": 4, "h": 10, "minW": 3, "minH": 6})
    widgets.append(item["widget"]); layout.append(item["layout"])

    rows, cols, sql = run_query("score_distribution")
    rows = clean_rows(rows)
    item = chart_widget("fraud-chart-score-bands", "Fraud Score Bands", rows, cols, sql, "bar", "score_band", ["customer_count"],
                        build_figure(rows, "score_band", ["customer_count"], "bar"), {"x": 4, "y": y, "w": 4, "h": 10, "minW": 3, "minH": 6})
    widgets.append(item["widget"]); layout.append(item["layout"])

    rows, cols, sql = run_query("category_flags")
    rows = clean_rows(rows)
    item = chart_widget("fraud-chart-category-flags", "Flags by Category", rows, cols, sql, "bar", "rule_category", ["customers_with_any_flag"],
                        build_figure(rows, "rule_category", ["customers_with_any_flag"], "bar"), {"x": 8, "y": y, "w": 4, "h": 10, "minW": 3, "minH": 6})
    widgets.append(item["widget"]); layout.append(item["layout"])
    y += 10

    rows, cols, sql = run_query("credit_vs_fraud")
    rows = clean_rows(rows)
    item = chart_widget("fraud-chart-credit-fraud", "Credit Model vs Fraud Outcome", rows, cols, sql, "stacked_bar", "model_category", ["customer_count"],
                        build_stacked_by_decision(rows), {"x": 0, "y": y, "w": 6, "h": 10, "minW": 4, "minH": 6})
    widgets.append(item["widget"]); layout.append(item["layout"])

    rows, cols, sql = run_query("rule_frequency")
    rows = clean_rows(rows)
    item = chart_widget("fraud-chart-rule-frequency", "Rule Trigger Frequency", rows, cols, sql, "bar", "rule_name", ["customers_flagged"],
                        build_figure(rows, "rule_name", ["customers_flagged"], "bar"), {"x": 6, "y": y, "w": 6, "h": 10, "minW": 4, "minH": 6})
    widgets.append(item["widget"]); layout.append(item["layout"])
    y += 10

    rows, cols, sql = run_query("scatter_credit_fraud")
    rows = clean_rows([r for r in rows if r.get("credit_limit") is not None and r.get("fraud_score") is not None])
    item = chart_widget("fraud-chart-scatter", "Fraud Score vs Credit Limit", rows, cols, sql, "scatter", "credit_limit", ["fraud_score"],
                        build_figure(rows, "credit_limit", ["fraud_score"], "scatter"), {"x": 0, "y": y, "w": 6, "h": 11, "minW": 4, "minH": 6})
    widgets.append(item["widget"]); layout.append(item["layout"])

    rows, cols, sql = run_query("co_occurring")
    rows = clean_rows(rows)
    item = chart_widget("fraud-chart-co-occurring", "Co-occurring Rules", rows, cols, sql, "bar", "rule_pair", ["co_occurrence_count"],
                        build_figure(rows, "rule_pair", ["co_occurrence_count"], "bar"), {"x": 6, "y": y, "w": 6, "h": 11, "minW": 4, "minH": 6})
    widgets.append(item["widget"]); layout.append(item["layout"])
    y += 11

    rows, cols, sql = run_query("watchlist")
    rows = clean_rows(rows)
    item = table_widget("fraud-table-watchlist", "High-Risk Watchlist", rows, cols, sql, {"x": 0, "y": y, "w": 12, "h": 12, "minW": 6, "minH": 6})
    widgets.append(item["widget"]); layout.append(item["layout"])
    y += 12

    rows, cols, sql = run_query("unified_customers")
    rows = clean_rows(rows)
    item = table_widget("fraud-table-unified", "Unified Customer View", rows, cols, sql, {"x": 0, "y": y, "w": 12, "h": 12, "minW": 6, "minH": 6})
    widgets.append(item["widget"]); layout.append(item["layout"])
    y += 12

    rows, cols, sql = run_query("fraud_critical")
    rows = clean_rows(rows)
    item = table_widget("fraud-table-critical", "FRAUD_CRITICAL Rejections", rows, cols, sql, {"x": 0, "y": y, "w": 6, "h": 10, "minW": 4, "minH": 6})
    widgets.append(item["widget"]); layout.append(item["layout"])

    rows, cols, sql = run_query("behavioural_metrics")
    rows = clean_rows(rows)
    item = table_widget("fraud-table-behavioural", "Behavioural Metrics by Decision", rows, cols, sql, {"x": 6, "y": y, "w": 6, "h": 10, "minW": 4, "minH": 6})
    widgets.append(item["widget"]); layout.append(item["layout"])

    attach_widget_exports(widgets)
    return widgets, layout


def ensure_fraud_dashboard(*, force: bool = False):
    """Create the bundled fraud dashboard if missing; optionally rebuild from template."""
    db = SessionLocal()
    try:
        existing = db.query(Dashboard).filter(Dashboard.name == FRAUD_DASHBOARD_NAME).first()
        if existing and not force:
            if existing.filters != FRAUD_DATE_FILTERS:
                existing.filters = FRAUD_DATE_FILTERS
                db.commit()
            print(f"✅ Fraud dashboard persisted (id={existing.id}, data DB queries on refresh)")
            return existing.id
    finally:
        db.close()

    try:
        widgets, grid_layout = build_dashboard()
    except Exception as exc:
        print(f"⚠️  Fraud dashboard build skipped (data DB): {exc}")
        return None

    db = SessionLocal()
    try:
        existing = db.query(Dashboard).filter(Dashboard.name == FRAUD_DASHBOARD_NAME).first()
        if existing:
            existing.description = FRAUD_DASHBOARD_DESCRIPTION
            existing.widgets = widgets
            existing.layout = grid_layout
            existing.filters = FRAUD_DATE_FILTERS
            existing.status = NotebookStatus.published
            flag_modified(existing, "widgets")
            flag_modified(existing, "layout")
            flag_modified(existing, "filters")
            db.commit()
            print(f"✅ Fraud dashboard rebuilt (id={existing.id}, {len(widgets)} widgets)")
            return existing.id

        dashboard = Dashboard(
            name=FRAUD_DASHBOARD_NAME,
            description=FRAUD_DASHBOARD_DESCRIPTION,
            layout=grid_layout,
            widgets=widgets,
            filters=FRAUD_DATE_FILTERS,
            status=NotebookStatus.published,
        )
        db.add(dashboard)
        db.commit()
        db.refresh(dashboard)
        print(f"✅ Fraud dashboard created (id={dashboard.id}, {len(widgets)} widgets)")
        return dashboard.id
    except Exception as exc:
        print(f"⚠️  Fraud dashboard persist failed: {exc}")
        return None
    finally:
        db.close()
