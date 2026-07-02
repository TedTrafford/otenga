"""Export SQL templates and labelling config per widget id."""

_SF = "{{segment_filter}}"
_DF = "{{date_filter}}"

# Widgets where a plain phone list is self-explanatory.
PHONES_ONLY_WIDGETS = frozenset({
    "cs-kpi-customers",
    "cs-kpi-qualified",
    "cs-kpi-not-qualified",
    "cs-kpi-high-dti",
    "cf-kpi-statements",
})

# Short slug used in download filenames (falls back to slugified widget title).
WIDGET_EXPORT_LABELS: dict[str, str] = {
    "cs-kpi-customers": "customers-profiled",
    "cs-kpi-qualified": "qualified-customers",
    "cs-kpi-not-qualified": "not-qualified-customers",
    "cs-kpi-qual-rate": "qualification-breakdown",
    "cs-kpi-avg-limit": "customers-with-credit-limit",
    "cs-kpi-total-credit": "credit-extended-customers",
    "cs-kpi-avg-score": "credit-score-detail",
    "cs-kpi-high-dti": "high-dti-customers",
    "cs-chart-category": "qualification-outcome",
    "cs-chart-risk": "risk-segment-customers",
    "cs-chart-turnover-seg": "turnover-segment-customers",
    "cs-chart-score-bands": "credit-score-bands",
    "cs-chart-credit-limit": "credit-limit-distribution",
    "cs-chart-turnover-bands": "turnover-bands",
    "cs-chart-age": "statement-age-bands",
    "cs-chart-dti": "dti-bands",
    "cs-chart-monthly-turnover": "monthly-turnover",
    "cs-chart-credit-fraud": "credit-vs-fraud",
    "cs-chart-daily": "daily-profiling",
    "cs-chart-rejection": "rejection-reasons",
    "rr-kpi-customers": "customers-with-reasons",
    "fraud-kpi-reject": "fraud-rejections",
    "fraud-kpi-manual": "manual-review",
    "fraud-kpi-reduce": "reduce-limit",
    "fraud-kpi-approve": "fraud-approved",
    "fp-kpi-failed": "failed-runs",
    "fp-chart-profiling": "profiling-outcomes",
    "cf-kpi-statements": "statements-passed",
    "cf-kpi-scored": "credit-scored",
    "cf-kpi-qualified": "credit-qualified",
    "cf-kpi-not-qualified": "credit-not-qualified",
    "cf-kpi-fraud-eval": "fraud-evaluated",
    "cf-kpi-fraud-reject": "fraud-rejected",
    "cf-kpi-fraud-manual": "fraud-manual-review",
    "cf-kpi-fraud-reduce": "fraud-reduce-limit",
    "cf-kpi-fraud-approved": "fraud-approved",
    "cf-kpi-pass-both": "credit-fraud-approved",
    "cf-kpi-credit-pass-fraud-fail": "credit-ok-fraud-failed",
    "cf-kpi-conversion": "full-conversion",
    "cf-chart-funnel": "funnel-detail",
    "cf-chart-outcomes": "outcome-detail",
    "cf-table-customers": "funnel-customers",
}

COLUMN_LABELS: dict[str, str] = {
    "mobile_number": "Mobile Number",
    "phone_number": "Phone Number",
    "supplied_phone_number": "Supplied Phone",
    "extracted_phone_number": "Extracted Phone",
    "model_category": "Qualification Outcome",
    "credit_limit": "Credit Limit (KES)",
    "credit_model_score": "Credit Model Score",
    "total_score": "Score",
    "risk_segment": "Risk Segment",
    "turnover_segment": "Turnover Segment",
    "three_month_wavg": "3-Month Weighted Avg Turnover",
    "debt_to_income_ratio": "Debt-to-Income Ratio",
    "profiled_at": "Profiled At",
    "last_updated": "Last Updated",
    "reason_rank": "Reason Rank",
    "reason_code": "Reason Code",
    "feature_name": "Feature Name",
    "feature_value": "Feature Value",
    "score_gap": "Score Gap",
    "repayment_probability": "Repayment Probability (%)",
    "reason_detail": "Reason Detail",
    "created_at": "Reason Recorded At",
    "date_created": "Reason Recorded At",
    "fraud_decision": "Fraud Decision",
    "fraud_score": "Fraud Score",
    "triggered_rules": "Triggered Rules",
    "statement_span_days": "Statement Span (days)",
    "evaluated_at": "Fraud Evaluated At",
    "customer_name": "Customer Name",
    "transaction_count": "Transaction Count",
    "total_inflow": "Total Inflow (KES)",
    "total_outflow": "Total Outflow (KES)",
    "total_volume": "Total Volume (KES)",
    "first_transaction_date": "First Transaction",
    "last_transaction_date": "Last Transaction",
    "transaction_type": "Transaction Type",
    "filename": "Filename",
    "source": "Source",
    "status": "Status",
    "record_id": "Record ID",
    "rows_inserted": "Rows Inserted",
    "duration_seconds": "Duration (seconds)",
    "error": "Error",
    "start_time": "Run Time",
    "profiling_status": "Profiling Status",
    "phone_match": "Phone Match",
    "balance_check_pct": "Balance Check (%)",
    "combined_outcome": "Combined Outcome",
    "fuliza_transaction_count": "Fuliza Transaction Count",
    "fuliza_volume": "Fuliza Volume (KES)",
    "betting_transaction_count": "Betting Transaction Count",
    "total_betting_outflow": "Betting Outflow (KES)",
    "lender_inflow_count": "Lender Inflow Count",
    "total_lender_inflow": "Lender Inflow (KES)",
    "email_address": "Email Address",
    "amount": "Amount (KES)",
    "transaction_date": "Transaction Date",
    "details_preview": "Details",
    "receipt_no": "Receipt No",
    "ingestion_path": "Ingestion Path",
    "data_source": "Data Source",
    "credit_outcome": "Credit Outcome",
    "combined_outcome": "Combined Outcome",
    "statement_parsed": "Statement Parsed",
    "evaluated_at": "Fraud Evaluated At",
    "profiled_at": "Profiled At",
    "funnel_stage": "Funnel Stage",
    "pct_of_entry": "% of Entry",
    "pct_of_previous": "% of Previous Stage",
    "entry_date": "Entry Date",
    "statements_passed": "Statements Passed",
}

_LP_CTE = """
WITH _ranked_profiles AS (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY mobile_number ORDER BY last_updated DESC) AS _rn
    FROM tbl_subscriber_profiles
    WHERE 1=1 """ + _DF + """
),
latest_profiles AS (
    SELECT mobile_number, model_category, credit_limit, total_score,
           risk_segment, turnover_segment, three_month_wavg, age_days,
           debt_to_income_ratio, last_updated
    FROM _ranked_profiles
    WHERE _rn = 1
)
"""

_CS_PHONES = _LP_CTE + """
SELECT DISTINCT mobile_number
FROM latest_profiles
WHERE 1=1 """ + _SF + """
ORDER BY mobile_number
"""

_CS_DETAIL = _LP_CTE + """
SELECT mobile_number, model_category, credit_limit,
       total_score AS credit_model_score, risk_segment, turnover_segment,
       ROUND(three_month_wavg, 0) AS three_month_wavg,
       ROUND(debt_to_income_ratio, 4) AS debt_to_income_ratio,
       last_updated AS profiled_at
FROM latest_profiles
WHERE 1=1 """ + _SF + """
ORDER BY model_category, mobile_number
"""

_CS_CREDIT_LIMIT = _LP_CTE + """
SELECT mobile_number, model_category, credit_limit,
       total_score AS credit_model_score, risk_segment, turnover_segment,
       last_updated AS profiled_at
FROM latest_profiles
WHERE credit_limit > 0 """ + _SF + """
ORDER BY credit_limit DESC, mobile_number
"""

_CS_HIGH_DTI_PHONES = _LP_CTE + """
SELECT DISTINCT mobile_number
FROM latest_profiles
WHERE debt_to_income_ratio > 0.50 """ + _SF + """
ORDER BY mobile_number
"""

_CS_QUALIFIED_PHONES = _LP_CTE + """
SELECT DISTINCT mobile_number
FROM latest_profiles
WHERE model_category = 'qualified' """ + _SF + """
ORDER BY mobile_number
"""

_CS_NOT_QUALIFIED_PHONES = _LP_CTE + """
SELECT DISTINCT mobile_number
FROM latest_profiles
WHERE model_category = 'not_qualified' """ + _SF + """
ORDER BY mobile_number
"""

_RR_DETAIL = """
SELECT mobile_number, reason_rank, reason_code, feature_name, feature_value,
       score_gap, repayment_probability,
       LEFT(reason_detail, 120) AS reason_detail, date_created
FROM tbl_rejection_reasons
WHERE 1=1 """ + _SF + " " + _DF + """
ORDER BY mobile_number, reason_rank
"""

_RR_UNIFIED = """
WITH _ranked_profiles AS (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY mobile_number ORDER BY last_updated DESC) AS _rn
    FROM tbl_subscriber_profiles
),
latest_profiles AS (
    SELECT mobile_number, model_category, credit_limit,
           total_score AS credit_model_score, risk_segment, turnover_segment,
           three_month_wavg, debt_to_income_ratio
    FROM _ranked_profiles
    WHERE _rn = 1
)
SELECT rr.mobile_number, lp.model_category, lp.credit_model_score,
       lp.risk_segment, lp.turnover_segment, rr.reason_rank, rr.reason_code,
       rr.feature_name, rr.score_gap, rr.repayment_probability,
       LEFT(rr.reason_detail, 120) AS reason_detail, rr.date_created
FROM tbl_rejection_reasons rr
LEFT JOIN latest_profiles lp ON lp.mobile_number = rr.mobile_number
WHERE 1=1 """ + _SF + " " + _DF + """
ORDER BY rr.repayment_probability ASC, rr.mobile_number, rr.reason_rank
"""

_FR_DETAIL = """
SELECT mobile_number, decision AS fraud_decision, total_score AS fraud_score,
       triggered_rules, statement_span_days, evaluated_at
FROM tbl_fraud_rules
WHERE 1=1 """ + _SF + " " + _DF + """
ORDER BY fraud_decision, fraud_score IS NULL, fraud_score DESC, mobile_number
"""

_FR_UNIFIED = """
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
SELECT fr.mobile_number, lp.model_category, lp.credit_model_score, lp.credit_limit,
       fr.decision AS fraud_decision, fr.total_score AS fraud_score,
       fr.triggered_rules, fr.evaluated_at,
       CASE
           WHEN lp.model_category = 'qualified' AND fr.decision = 'Approve' THEN 'Pass Both'
           WHEN lp.model_category = 'qualified' AND fr.decision <> 'Approve' THEN 'Pass Credit / Fail Fraud'
           WHEN lp.model_category = 'not_qualified' AND fr.decision = 'Approve' THEN 'Fail Credit / Pass Fraud'
           ELSE 'Fail Both or Review'
       END AS combined_outcome
FROM tbl_fraud_rules fr
LEFT JOIN latest_profiles lp ON lp.mobile_number = fr.mobile_number
WHERE 1=1 """ + _SF + " " + _DF + """
ORDER BY fr.total_score IS NULL, fr.total_score DESC, fr.mobile_number
"""

_RMS_CUSTOMER = """
SELECT mobile_number, MAX(customer_name) AS customer_name,
       COUNT(*) AS transaction_count,
       ROUND(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 0) AS total_inflow,
       ROUND(SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END), 0) AS total_outflow,
       ROUND(SUM(ABS(amount)), 0) AS total_volume,
       MIN(transaction_date) AS first_transaction_date,
       MAX(transaction_date) AS last_transaction_date
FROM tbl_raw_mpesa_statements
WHERE mobile_number IS NOT NULL AND TRIM(mobile_number) <> ''
""" + _SF + " " + _DF + """
GROUP BY mobile_number
ORDER BY transaction_count DESC, mobile_number
"""

_RMS_TXN_DETAIL = """
SELECT mobile_number, customer_name, transaction_date, transaction_type,
       amount, LEFT(details, 100) AS details_preview, receipt_no
FROM tbl_raw_mpesa_statements
WHERE 1=1 """ + _SF + " " + _DF + """
ORDER BY transaction_date DESC, mobile_number
"""

_FP_FAILED = """
SELECT COALESCE(NULLIF(TRIM(supplied_phone_number), ''), NULLIF(TRIM(extracted_phone_number), '')) AS mobile_number,
       filename, source, status, record_id, rows_inserted,
       duration_seconds, LEFT(error, 120) AS error, start_time
FROM tbl_file_processing_logs
WHERE status = 'FAILED'
  AND COALESCE(NULLIF(TRIM(supplied_phone_number), ''), NULLIF(TRIM(extracted_phone_number), '')) IS NOT NULL
""" + _SF + " " + _DF + """
ORDER BY start_time DESC
"""

_FP_PROFILING = """
SELECT COALESCE(NULLIF(TRIM(supplied_phone_number), ''), NULLIF(TRIM(extracted_phone_number), '')) AS mobile_number,
       filename, profiling_status, phone_match, balance_check_pct,
       rows_inserted, status, start_time
FROM tbl_file_processing_logs
WHERE source = 'parse_single.py'
  AND profiling_status NOT IN ('', 'N/A')
  AND COALESCE(NULLIF(TRIM(supplied_phone_number), ''), NULLIF(TRIM(extracted_phone_number), '')) IS NOT NULL
""" + _SF + " " + _DF + """
ORDER BY start_time DESC
"""

_CF_COHORT = """
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
    SELECT c.mobile_number, lp.model_category, lp.credit_model_score, lp.credit_limit,
           lp.profiled_at, fr.decision AS fraud_decision, fr.total_score AS fraud_score,
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

_CF_DETAIL = _CF_COHORT + """
SELECT mobile_number, model_category AS credit_outcome, credit_model_score, credit_limit,
       profiled_at, fraud_decision, fraud_score, evaluated_at, combined_outcome
FROM enriched
WHERE 1=1 """ + _SF + """
ORDER BY combined_outcome, mobile_number
"""

WIDGET_EXPORT_REGISTRY: dict[str, str] = {
    # Customer Scoring — phones-only KPIs
    "cs-kpi-customers": _CS_PHONES,
    "cs-kpi-qualified": _CS_QUALIFIED_PHONES,
    "cs-kpi-not-qualified": _CS_NOT_QUALIFIED_PHONES,
    "cs-kpi-high-dti": _CS_HIGH_DTI_PHONES,
    # Customer Scoring — detailed KPIs
    "cs-kpi-qual-rate": _CS_DETAIL,
    "cs-kpi-avg-limit": _CS_CREDIT_LIMIT,
    "cs-kpi-total-credit": _CS_CREDIT_LIMIT,
    "cs-kpi-avg-score": _CS_DETAIL,
    # Customer Scoring charts
    "cs-chart-category": _CS_DETAIL,
    "cs-chart-risk": _LP_CTE + """
SELECT mobile_number, model_category, risk_segment, credit_limit,
       total_score AS credit_model_score, last_updated AS profiled_at
FROM latest_profiles WHERE risk_segment > 0 """ + _SF + """
ORDER BY risk_segment, mobile_number
""",
    "cs-chart-turnover-seg": _LP_CTE + """
SELECT mobile_number, model_category, turnover_segment, credit_limit,
       ROUND(three_month_wavg, 0) AS three_month_wavg, last_updated AS profiled_at
FROM latest_profiles WHERE turnover_segment > 0 """ + _SF + """
ORDER BY turnover_segment, mobile_number
""",
    "cs-chart-score-bands": _CS_DETAIL,
    "cs-chart-credit-limit": _CS_DETAIL,
    "cs-chart-turnover-bands": _CS_DETAIL,
    "cs-chart-age": _LP_CTE + """
SELECT mobile_number, model_category, age_days, credit_limit,
       total_score AS credit_model_score, last_updated AS profiled_at
FROM latest_profiles """ + _SF + """
ORDER BY age_days IS NULL, age_days DESC, mobile_number
""",
    "cs-chart-dti": _LP_CTE + """
SELECT mobile_number, model_category,
       ROUND(debt_to_income_ratio, 4) AS debt_to_income_ratio,
       credit_limit, total_score AS credit_model_score, last_updated AS profiled_at
FROM latest_profiles """ + _SF + """
ORDER BY debt_to_income_ratio IS NULL, debt_to_income_ratio DESC, mobile_number
""",
    "cs-chart-monthly-turnover": _LP_CTE + """
SELECT mobile_number, model_category,
       ROUND(three_month_wavg, 0) AS three_month_wavg,
       credit_limit, total_score AS credit_model_score, last_updated AS profiled_at
FROM latest_profiles """ + _SF + """
ORDER BY three_month_wavg IS NULL, three_month_wavg DESC, mobile_number
""",
    "cs-chart-credit-fraud": _LP_CTE + """
SELECT lp.mobile_number, lp.model_category, lp.credit_limit,
       lp.total_score AS credit_model_score, fr.decision AS fraud_decision,
       fr.total_score AS fraud_score, fr.triggered_rules
FROM latest_profiles lp
JOIN tbl_fraud_rules fr ON fr.mobile_number = lp.mobile_number
WHERE 1=1 """ + _SF + """
ORDER BY lp.model_category, fr.decision, lp.mobile_number
""",
    "cs-chart-daily": _CS_DETAIL,
    "cs-chart-rejection": """
WITH _ranked_profiles AS (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY mobile_number ORDER BY last_updated DESC) AS _rn
    FROM tbl_subscriber_profiles
    WHERE 1=1 """ + _DF + """
),
latest_profiles AS (
    SELECT mobile_number, model_category, total_score AS credit_model_score
    FROM _ranked_profiles
    WHERE _rn = 1
)
SELECT rr.mobile_number, lp.model_category, lp.credit_model_score,
       rr.reason_code, rr.repayment_probability, rr.date_created
FROM tbl_rejection_reasons rr
JOIN latest_profiles lp ON lp.mobile_number = rr.mobile_number
WHERE lp.model_category = 'not_qualified' """ + _SF + """
ORDER BY rr.reason_code, rr.mobile_number
""",

    # Rejection Reasons
    "rr-kpi-customers": _RR_DETAIL,
    "rr-kpi-total-rows": _RR_DETAIL,
    "rr-kpi-avg-reasons": _RR_DETAIL,
    "rr-kpi-reason-codes": _RR_DETAIL,
    "rr-kpi-weak-features": """
SELECT mobile_number, reason_code, feature_name, feature_value, score_gap,
       repayment_probability, LEFT(reason_detail, 120) AS reason_detail, date_created
FROM tbl_rejection_reasons
WHERE reason_code = 'WEAK_SCORING_FEATURE' """ + _SF + " " + _DF + """
ORDER BY score_gap IS NULL, score_gap DESC, mobile_number
""",
    "rr-kpi-avg-repay": _RR_DETAIL,
    "rr-kpi-avg-gap": """
SELECT mobile_number, reason_code, feature_name, score_gap, repayment_probability, date_created
FROM tbl_rejection_reasons
WHERE reason_code = 'WEAK_SCORING_FEATURE' """ + _SF + " " + _DF + """
ORDER BY score_gap IS NULL, score_gap DESC, mobile_number
""",
    "rr-kpi-primary": """
SELECT mobile_number, reason_code, feature_name, repayment_probability,
       score_gap, LEFT(reason_detail, 120) AS reason_detail, date_created
FROM tbl_rejection_reasons
WHERE reason_rank = 1 """ + _SF + " " + _DF + """
ORDER BY repayment_probability ASC, mobile_number
""",
    "rr-chart-reason-codes": _RR_DETAIL,
    "rr-chart-primary": """
SELECT mobile_number, reason_code, feature_name, repayment_probability,
       score_gap, date_created
FROM tbl_rejection_reasons
WHERE reason_rank = 1 """ + _SF + " " + _DF + """
ORDER BY reason_code, mobile_number
""",
    "rr-chart-repay-bands": _RR_DETAIL,
    "rr-chart-weak-features": """
SELECT mobile_number, feature_name, feature_value, score_gap, repayment_probability, date_created
FROM tbl_rejection_reasons
WHERE reason_code = 'WEAK_SCORING_FEATURE' """ + _SF + " " + _DF + """
ORDER BY feature_name, score_gap IS NULL, score_gap DESC
""",
    "rr-chart-score-gap": """
SELECT mobile_number, feature_name, score_gap, repayment_probability, date_created
FROM tbl_rejection_reasons
WHERE reason_code = 'WEAK_SCORING_FEATURE' AND score_gap IS NOT NULL """ + _SF + " " + _DF + """
ORDER BY score_gap DESC, mobile_number
""",
    "rr-chart-combinations": _RR_DETAIL,
    "rr-chart-co-occur": _RR_DETAIL,
    "rr-chart-repay-reason": _RR_DETAIL,
    "rr-chart-low-turnover": """
SELECT mobile_number, feature_value, repayment_probability,
       LEFT(reason_detail, 120) AS reason_detail, date_created
FROM tbl_rejection_reasons
WHERE reason_code = 'LOW_TURNOVER' """ + _SF + " " + _DF + """
ORDER BY feature_value ASC, mobile_number
""",
    "rr-chart-high-risk": """
SELECT mobile_number, feature_value AS credit_model_score, repayment_probability,
       LEFT(reason_detail, 120) AS reason_detail, date_created
FROM tbl_rejection_reasons
WHERE reason_code = 'HIGH_CREDIT_RISK' """ + _SF + " " + _DF + """
ORDER BY feature_value DESC, mobile_number
""",
    "rr-chart-risk-reason": _LP_CTE + """
SELECT rr.mobile_number, lp.risk_segment, lp.model_category, rr.reason_code,
       rr.repayment_probability, rr.date_created
FROM tbl_rejection_reasons rr
JOIN latest_profiles lp ON lp.mobile_number = rr.mobile_number
WHERE lp.model_category = 'not_qualified' AND rr.reason_rank = 1 """ + _SF + """
ORDER BY lp.risk_segment, rr.reason_code, rr.mobile_number
""",
    "rr-chart-daily": _RR_DETAIL,

    # Fraud Rules
    "fraud-kpi-customers": _FR_DETAIL,
    "fraud-kpi-reject": """
SELECT mobile_number, decision AS fraud_decision, total_score AS fraud_score,
       triggered_rules, evaluated_at
FROM tbl_fraud_rules WHERE decision = 'Reject' """ + _SF + " " + _DF + """
ORDER BY fraud_score DESC, mobile_number
""",
    "fraud-kpi-manual": """
SELECT mobile_number, decision AS fraud_decision, total_score AS fraud_score,
       triggered_rules, evaluated_at
FROM tbl_fraud_rules WHERE decision = 'Manual Review' """ + _SF + " " + _DF + """
ORDER BY fraud_score DESC, mobile_number
""",
    "fraud-kpi-reduce": """
SELECT mobile_number, decision AS fraud_decision, total_score AS fraud_score,
       triggered_rules, evaluated_at
FROM tbl_fraud_rules WHERE decision = 'Reduce Limit' """ + _SF + " " + _DF + """
ORDER BY fraud_score DESC, mobile_number
""",
    "fraud-kpi-approve": """
SELECT mobile_number, decision AS fraud_decision, total_score AS fraud_score,
       triggered_rules, evaluated_at
FROM tbl_fraud_rules WHERE decision = 'Approve' """ + _SF + " " + _DF + """
ORDER BY mobile_number
""",
    "fraud-kpi-reject-rate": """
SELECT mobile_number, decision AS fraud_decision, total_score AS fraud_score,
       triggered_rules, evaluated_at
FROM tbl_fraud_rules WHERE decision = 'Reject' """ + _SF + " " + _DF + """
ORDER BY fraud_score DESC, mobile_number
""",
    "fraud-kpi-avg-score": _FR_DETAIL,
    "fraud-kpi-max-score": _FR_DETAIL,
    "fraud-chart-decisions": _FR_DETAIL,
    "fraud-chart-score-bands": _FR_DETAIL,
    "fraud-chart-category-flags": _FR_DETAIL,
    "fraud-chart-credit-fraud": _FR_UNIFIED,
    "fraud-chart-rule-frequency": _FR_DETAIL,
    "fraud-chart-scatter": _FR_UNIFIED,
    "fraud-chart-co-occurring": _FR_DETAIL,

    # Raw M-Pesa Statements
    "rms-kpi-customers": _RMS_CUSTOMER,
    "rms-kpi-transactions": _RMS_CUSTOMER,
    "rms-kpi-avg-txn": _RMS_CUSTOMER,
    "rms-kpi-inflow": """
SELECT mobile_number, MAX(customer_name) AS customer_name,
       COUNT(*) AS transaction_count,
       ROUND(SUM(amount), 0) AS total_inflow
FROM tbl_raw_mpesa_statements
WHERE amount > 0 """ + _SF + " " + _DF + """
GROUP BY mobile_number
ORDER BY total_inflow DESC, mobile_number
""",
    "rms-kpi-outflow": """
SELECT mobile_number, MAX(customer_name) AS customer_name,
       COUNT(*) AS transaction_count,
       ROUND(SUM(amount), 0) AS total_outflow
FROM tbl_raw_mpesa_statements
WHERE amount < 0 """ + _SF + " " + _DF + """
GROUP BY mobile_number
ORDER BY total_outflow ASC, mobile_number
""",
    "rms-kpi-volume": _RMS_CUSTOMER,
    "rms-kpi-avg-size": _RMS_CUSTOMER,
    "rms-kpi-types": _RMS_CUSTOMER,
    "rms-chart-types": _RMS_CUSTOMER,
    "rms-chart-ingestion": _RMS_CUSTOMER,
    "rms-chart-source": _RMS_CUSTOMER,
    "rms-chart-daily": _RMS_CUSTOMER,
    "rms-chart-monthly": _RMS_CUSTOMER,
    "rms-chart-hour": _RMS_CUSTOMER,
    "rms-chart-amount": _RMS_CUSTOMER,
    "rms-chart-span": _RMS_CUSTOMER,
    "rms-chart-credit-debit": _RMS_CUSTOMER,
    "rms-chart-p2p": """
SELECT mobile_number, MAX(customer_name) AS customer_name, transaction_type,
       COUNT(*) AS transaction_count,
       ROUND(SUM(amount), 0) AS net_amount
FROM tbl_raw_mpesa_statements
WHERE transaction_type IN ('SEND MONEY', 'RECEIVED MONEY') """ + _SF + " " + _DF + """
GROUP BY mobile_number, transaction_type
ORDER BY mobile_number, transaction_type
""",
    "rms-chart-email": """
SELECT mobile_number, MAX(customer_name) AS customer_name,
       MAX(email_address) AS email_address, COUNT(*) AS transaction_count
FROM tbl_raw_mpesa_statements
WHERE email_address <> '' AND email_address LIKE '%@%' """ + _SF + " " + _DF + """
GROUP BY mobile_number
ORDER BY transaction_count DESC, mobile_number
""",

    # File Processing
    "fp-kpi-failed": _FP_FAILED,
    "fp-chart-profiling": _FP_PROFILING,

    # Customer Funnel
    "cf-kpi-statements": _CF_COHORT + "SELECT DISTINCT mobile_number FROM cohort ORDER BY mobile_number",
    "cf-kpi-scored": _CF_DETAIL.replace(_SF, " AND model_category IS NOT NULL " + _SF),
    "cf-kpi-qualified": _CF_DETAIL.replace(_SF, " AND model_category = 'qualified' " + _SF),
    "cf-kpi-not-qualified": _CF_DETAIL.replace(_SF, " AND model_category = 'not_qualified' " + _SF),
    "cf-kpi-fraud-eval": _CF_DETAIL.replace(_SF, " AND fraud_decision IS NOT NULL " + _SF),
    "cf-kpi-fraud-reject": _CF_DETAIL.replace(_SF, " AND fraud_decision = 'Reject' " + _SF),
    "cf-kpi-fraud-manual": _CF_DETAIL.replace(_SF, " AND fraud_decision = 'Manual Review' " + _SF),
    "cf-kpi-fraud-reduce": _CF_DETAIL.replace(_SF, " AND fraud_decision = 'Reduce Limit' " + _SF),
    "cf-kpi-fraud-approved": _CF_DETAIL.replace(_SF, " AND fraud_decision = 'Approve' " + _SF),
    "cf-kpi-pass-both": _CF_DETAIL.replace(
        _SF, " AND model_category = 'qualified' AND fraud_decision = 'Approve' " + _SF,
    ),
    "cf-kpi-credit-pass-fraud-fail": _CF_DETAIL.replace(
        _SF,
        " AND model_category = 'qualified' AND fraud_decision IS NOT NULL AND fraud_decision <> 'Approve' " + _SF,
    ),
    "cf-kpi-conversion": _CF_DETAIL.replace(
        _SF, " AND model_category = 'qualified' AND fraud_decision = 'Approve' " + _SF,
    ),
    "cf-chart-funnel": _CF_DETAIL,
    "cf-chart-outcomes": _CF_DETAIL,
    "cf-chart-conversion": _CF_DETAIL,
    "cf-chart-matrix": _CF_DETAIL,
    "cf-chart-credit-fraud-cross": _CF_DETAIL.replace(
        _SF, " AND model_category IS NOT NULL AND fraud_decision IS NOT NULL " + _SF,
    ),
    "cf-chart-fraud-decisions": _CF_DETAIL.replace(_SF, " AND fraud_decision IS NOT NULL " + _SF),
    "cf-chart-daily": _CF_COHORT + "SELECT DISTINCT mobile_number FROM cohort ORDER BY mobile_number",
}

WIDGET_EXPORT_SEGMENT_COLS: dict[str, str] = {
    "cs-chart-category": "model_category",
    "cs-chart-risk": "risk_segment",
    "cs-chart-turnover-seg": "turnover_segment",
    "cs-chart-score-bands": "score_band",
    "cs-chart-turnover-bands": "turnover_band",
    "cs-chart-age": "age_band",
    "cs-chart-dti": "dti_band",
    "cs-chart-credit-fraud": "model_category",
    "cs-chart-rejection": "reason_code",
    "rr-chart-reason-codes": "reason_code",
    "rr-chart-primary": "reason_code",
    "rr-chart-repay-bands": "repayment_prob_band",
    "rr-chart-weak-features": "feature_name",
    "rr-chart-score-gap": "score_gap_band",
    "rr-chart-low-turnover": "turnover_band",
    "rr-chart-high-risk": "score_band",
    "rr-chart-risk-reason": "reason_code",
    "fraud-chart-decisions": "decision",
    "fraud-chart-score-bands": "score_band",
    "fraud-chart-credit-fraud": "model_category",
    "fraud-chart-rule-frequency": "rule_name",
    "rms-chart-types": "transaction_type",
    "rms-chart-ingestion": "ingestion_path",
    "rms-chart-source": "data_source",
    "fp-chart-profiling": "profiling_status",
    "cf-chart-outcomes": "combined_outcome",
    "cf-chart-matrix": "credit_outcome",
    "cf-chart-fraud-decisions": "fraud_decision",
}
