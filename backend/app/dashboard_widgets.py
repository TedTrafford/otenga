"""Shared helpers for building persisted dashboard widgets."""

from decimal import Decimal

from sqlalchemy import text

from .execution_engine import _get_mysql_engine

PALETTE = ["#00D4FF", "#7C3AED", "#06FFA5", "#FF4D6D", "#FFB800", "#EC4899", "#34D399", "#F97316"]


DATE_FILTER_PLACEHOLDER = "{{date_filter}}"


def run_query(sql: str):
    """Execute dashboard seed SQL; keeps {{date_filter}} in stored template, strips it at build time."""
    engine = _get_mysql_engine()
    template_sql = sql.strip()
    executable_sql = template_sql.replace(DATE_FILTER_PLACEHOLDER, "")
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


def build_funnel_figure(rows, stage_col, value_col, title=""):
    """Build a Plotly funnel chart from ordered stage rows."""
    if not rows:
        return None
    ordered = sorted(rows, key=lambda r: r.get("stage_order") or 0)
    stages = [str(r.get(stage_col) or "") for r in ordered]
    values = [float(r.get(value_col) or 0) for r in ordered]
    return {
        "data": [{
            "type": "funnel",
            "y": stages,
            "x": values,
            "textinfo": "value+percent initial",
            "marker": {"color": PALETTE[: len(stages)]},
        }],
        "layout": {
            "title": {"text": title, "font": {"color": "#94A3B8", "size": 13}},
            "showlegend": False,
        },
    }


def build_stacked_bar(rows, x_col, series_col, value_col, series_order=None):
    """Pivot long-format rows into a stacked bar figure."""
    if not rows:
        return None
    categories = sorted({r[x_col] for r in rows})
    series_values = sorted({r[series_col] for r in rows}, key=lambda s: (series_order or {}).get(s, 999))
    lookup = {(r[x_col], r[series_col]): r[value_col] for r in rows}
    traces = []
    for i, series in enumerate(series_values):
        color = PALETTE[i % len(PALETTE)]
        traces.append({
            "type": "bar",
            "name": str(series),
            "x": categories,
            "y": [lookup.get((cat, series), 0) for cat in categories],
            "marker": {"color": color, "opacity": 0.9},
        })
    return {"data": traces, "layout": {"barmode": "stack", "showlegend": True}}


def metric_widget(widget_id, title, col, rows, sql, layout, export_sql=None):
    val = rows[0].get(col) if rows else None
    if val is not None and not isinstance(val, str):
        val = f"{val:,}" if isinstance(val, int) else str(val)
    widget = {
        "id": widget_id, "type": "metric", "title": title, "sql": sql,
        "rows": rows, "columns": list(rows[0].keys()) if rows else [],
        "metaCol": col, "label": title, "value": str(val) if val is not None else "—",
    }
    if export_sql:
        widget["exportSql"] = export_sql
    return {"widget": widget, "layout": {**layout, "i": widget_id}}


def chart_widget(widget_id, title, rows, columns, sql, chart_type, x_col, y_cols, fig_data, layout, export_sql=None, export_segment_col=None):
    widget = {
        "id": widget_id, "type": "chart", "title": title, "sql": sql,
        "rows": rows, "columns": columns, "chartType": chart_type,
        "xCol": x_col, "yCols": y_cols, "figData": fig_data,
    }
    if export_sql:
        widget["exportSql"] = export_sql
    if export_segment_col:
        widget["exportSegmentCol"] = export_segment_col
    return {"widget": widget, "layout": {**layout, "i": widget_id}}


def table_widget(widget_id, title, rows, columns, sql, layout, export_sql=None):
    widget = {
        "id": widget_id, "type": "table", "title": title, "sql": sql,
        "rows": rows, "columns": columns,
    }
    if export_sql:
        widget["exportSql"] = export_sql
    return {"widget": widget, "layout": {**layout, "i": widget_id}}


def attach_widget_exports(widgets, export_queries=None, segment_cols=None):
    """Attach exportSql / exportSegmentCol from registry maps onto widget dicts."""
    from .dashboard_export_queries import WIDGET_EXPORT_REGISTRY, WIDGET_EXPORT_SEGMENT_COLS, PHONES_ONLY_WIDGETS

    exports = export_queries or WIDGET_EXPORT_REGISTRY
    segments = segment_cols or WIDGET_EXPORT_SEGMENT_COLS
    for widget in widgets:
        if not isinstance(widget, dict):
            continue
        wid = widget.get("id")
        if wid in exports and not widget.get("exportSql"):
            widget["exportSql"] = exports[wid]
        if wid in segments and not widget.get("exportSegmentCol"):
            widget["exportSegmentCol"] = segments[wid]
        if wid in PHONES_ONLY_WIDGETS:
            widget["exportMode"] = "phones"
        elif widget.get("type") == "table":
            widget["exportMode"] = "detail"
        elif wid in exports:
            widget["exportMode"] = "detail"
        from .dashboard_export import widget_is_exportable
        if widget_is_exportable(widget):
            widget["exportable"] = True
    return widgets
