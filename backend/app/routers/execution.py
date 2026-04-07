from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import Dict, Any
import json
import asyncio
from ..database import get_db
from ..auth import get_current_active_user
from ..models import User, Notebook
from ..schemas import ExecuteRequest, ExecuteResult
from ..execution_engine import execute_cell, get_db_tables, get_table_schema, clear_notebook_context

router = APIRouter()


@router.post("/cell", response_model=ExecuteResult)
async def execute_cell_endpoint(
    request: ExecuteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    notebook_id = str(request.notebook_id) if request.notebook_id else None
    result = await execute_cell(
        cell_type=request.cell_type,
        code=request.code,
        context=request.context,
        notebook_id=notebook_id,
    )
    return ExecuteResult(
        cell_id=request.cell_id,
        **result,
    )


@router.get("/schema/tables")
async def get_tables(current_user: User = Depends(get_current_active_user)):
    return get_db_tables()


@router.get("/schema/tables/{table_name}")
async def get_table_info(
    table_name: str,
    current_user: User = Depends(get_current_active_user),
):
    return get_table_schema(table_name)


@router.delete("/context/{notebook_id}")
async def clear_context(
    notebook_id: str,
    current_user: User = Depends(get_current_active_user),
):
    clear_notebook_context(notebook_id)
    return {"message": "Context cleared"}


@router.websocket("/ws/{notebook_id}")
async def websocket_execute(websocket: WebSocket, notebook_id: str):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)

            cell_type = payload.get("cell_type", "sql")
            code = payload.get("code", "")
            cell_id = payload.get("cell_id", "")
            context = payload.get("context", {})

            await websocket.send_json({"type": "start", "cell_id": cell_id})

            result = await execute_cell(
                cell_type=cell_type,
                code=code,
                context=context,
                notebook_id=notebook_id,
            )

            await websocket.send_json({
                "type": "result",
                "cell_id": cell_id,
                **result,
            })
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({"type": "error", "error": str(e)})
