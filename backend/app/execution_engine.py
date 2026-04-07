import asyncio
import json
import sys
import traceback
import time
from io import StringIO
from typing import Any, Dict, Optional
import sqlalchemy
import pandas as pd
import numpy as np
from .config import settings

# Global notebook execution contexts: notebook_id -> {var_name: value}
_notebook_contexts: Dict[str, Dict[str, Any]] = {}


def _get_mysql_engine():
    url = (
        f"mysql+pymysql://{settings.MPESA_DB_USER}:{settings.MPESA_DB_PASSWORD}"
        f"@{settings.MPESA_DB_HOST}:{settings.MPESA_DB_PORT}/{settings.MPESA_DB_NAME}"
    )
    return sqlalchemy.create_engine(url, pool_pre_ping=True)


def _interpolate_variables(code: str, context: Dict[str, Any]) -> str:
    """Replace {{variable}} placeholders with context values."""
    import re
    def replacer(match):
        var_name = match.group(1).strip()
        val = context.get(var_name, match.group(0))
        return str(val) if not isinstance(val, str) else f"'{val}'"
    return re.sub(r"\{\{([^}]+)\}\}", replacer, code)


def _serialize_result(obj: Any) -> Dict[str, Any]:
    """Serialize various Python objects to JSON-safe dict."""
    if isinstance(obj, pd.DataFrame):
        return {
            "type": "dataframe",
            "data": json.loads(obj.to_json(orient="records", date_format="iso")),
            "columns": obj.columns.tolist(),
            "shape": list(obj.shape),
            "dtypes": {col: str(dtype) for col, dtype in obj.dtypes.items()},
        }
    try:
        import plotly.graph_objects as go
        if isinstance(obj, go.Figure):
            return {"type": "plotly", "data": json.loads(obj.to_json())}
    except ImportError:
        pass
    if isinstance(obj, (dict, list)):
        return {"type": "json", "data": obj}
    return {"type": "text", "data": str(obj)}


def execute_sql_sync(
    query: str,
    context: Optional[Dict[str, Any]] = None,
    notebook_id: Optional[str] = None,
) -> Dict[str, Any]:
    start = time.time()
    try:
        if context:
            query = _interpolate_variables(query, context)

        engine = _get_mysql_engine()
        with engine.connect() as conn:
            df = pd.read_sql_query(sqlalchemy.text(query), conn)

        elapsed_ms = (time.time() - start) * 1000

        if notebook_id:
            ctx = _notebook_contexts.setdefault(notebook_id, {})
            ctx["_last_df"] = df
            ctx["_last_sql_result"] = df

        return {
            "success": True,
            "type": "dataframe",
            "data": json.loads(df.to_json(orient="records", date_format="iso")),
            "columns": df.columns.tolist(),
            "shape": list(df.shape),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "execution_time_ms": elapsed_ms,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
            "execution_time_ms": (time.time() - start) * 1000,
        }


def execute_python_sync(
    code: str,
    context: Optional[Dict[str, Any]] = None,
    notebook_id: Optional[str] = None,
) -> Dict[str, Any]:
    start = time.time()

    nb_ctx = _notebook_contexts.get(notebook_id or "", {}) if notebook_id else {}
    local_vars: Dict[str, Any] = {**nb_ctx, **(context or {})}

    stdout_buf = StringIO()
    old_stdout = sys.stdout
    sys.stdout = stdout_buf

    safe_builtins = {
        "__import__": __import__,
        "print": print,
        "len": len, "range": range, "list": list, "dict": dict, "set": set,
        "tuple": tuple, "str": str, "int": int, "float": float, "bool": bool,
        "type": type, "isinstance": isinstance, "issubclass": issubclass,
        "enumerate": enumerate, "zip": zip, "map": map, "filter": filter,
        "sorted": sorted, "reversed": reversed, "sum": sum, "min": min,
        "max": max, "abs": abs, "round": round, "pow": pow, "divmod": divmod,
        "chr": chr, "ord": ord, "hex": hex, "oct": oct, "bin": bin,
        "repr": repr, "hash": hash, "id": id, "vars": vars,
        "any": any, "all": all, "next": next, "iter": iter,
        "open": open, "Exception": Exception, "ValueError": ValueError,
        "KeyError": KeyError, "IndexError": IndexError, "TypeError": TypeError,
    }

    try:
        import plotly.express as px
        import plotly.graph_objects as go
        import plotly
    except ImportError:
        px = go = plotly = None

    exec_globals = {
        "__builtins__": safe_builtins,
        "pd": pd,
        "pandas": pd,
        "np": np,
        "numpy": np,
        "json": json,
    }
    if px:
        exec_globals.update({"px": px, "go": go, "plotly": plotly})

    try:
        exec(compile(code, "<cell>", "exec"), exec_globals, local_vars)

        sys.stdout = old_stdout
        stdout_output = stdout_buf.getvalue()
        elapsed_ms = (time.time() - start) * 1000

        if notebook_id:
            _notebook_contexts[notebook_id] = {
                **_notebook_contexts.get(notebook_id, {}),
                **{k: v for k, v in local_vars.items() if not k.startswith("_")}
            }

        # Detect what was produced - priority: plotly figure > dataframe > text
        figure = None
        dataframe = None
        last_expr = None

        for val in reversed(list(local_vars.values())):
            if go and isinstance(val, go.Figure):
                figure = val
                break

        if figure is None:
            for val in reversed(list(local_vars.values())):
                if isinstance(val, pd.DataFrame):
                    dataframe = val
                    break

        if figure:
            return {
                "success": True,
                "type": "plotly",
                "data": json.loads(figure.to_json()),
                "stdout": stdout_output,
                "execution_time_ms": elapsed_ms,
            }
        elif dataframe is not None:
            return {
                "success": True,
                **_serialize_result(dataframe),
                "stdout": stdout_output,
                "execution_time_ms": elapsed_ms,
            }
        else:
            return {
                "success": True,
                "type": "text",
                "data": stdout_output,
                "stdout": stdout_output,
                "execution_time_ms": elapsed_ms,
            }

    except Exception as e:
        sys.stdout = old_stdout
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
            "execution_time_ms": (time.time() - start) * 1000,
        }


async def execute_cell(
    cell_type: str,
    code: str,
    context: Optional[Dict[str, Any]] = None,
    notebook_id: Optional[str] = None,
) -> Dict[str, Any]:
    if cell_type == "sql":
        result = await asyncio.to_thread(execute_sql_sync, code, context, notebook_id)
    elif cell_type == "python":
        result = await asyncio.to_thread(execute_python_sync, code, context, notebook_id)
    else:
        result = {"success": True, "type": "markdown", "data": code}
    return result


def get_notebook_context(notebook_id: str) -> Dict[str, Any]:
    return _notebook_contexts.get(notebook_id, {})


def clear_notebook_context(notebook_id: str):
    _notebook_contexts.pop(notebook_id, None)


def get_db_tables() -> Dict[str, Any]:
    try:
        engine = _get_mysql_engine()
        with engine.connect() as conn:
            result = conn.execute(sqlalchemy.text("SHOW TABLES"))
            tables = [row[0] for row in result]
        return {"success": True, "tables": tables}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_table_schema(table_name: str) -> Dict[str, Any]:
    try:
        engine = _get_mysql_engine()
        with engine.connect() as conn:
            result = conn.execute(sqlalchemy.text(f"DESCRIBE `{table_name}`"))
            columns = [
                {"field": row[0], "type": row[1], "null": row[2], "key": row[3], "default": row[4]}
                for row in result
            ]
        return {"success": True, "table": table_name, "columns": columns}
    except Exception as e:
        return {"success": False, "error": str(e)}
