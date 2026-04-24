from pydantic import BaseModel, EmailStr
from typing import Optional, List, Any, Dict
from datetime import datetime
from .models import UserRole, UserStatus, NotebookStatus


class UserBase(BaseModel):
    username: str
    email: str
    role: UserRole = UserRole.viewer


class UserCreate(UserBase):
    password: str
    full_name: Optional[str] = None


class UserUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None
    is_active: Optional[bool] = None


class UserOut(UserBase):
    id: int
    is_active: bool
    status: UserStatus
    avatar_color: str
    full_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserOut


class TokenData(BaseModel):
    username: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class CellBase(BaseModel):
    id: str
    type: str  # "sql" | "python" | "markdown"
    code: str
    result: Optional[Dict[str, Any]] = None
    position: int
    is_running: bool = False


class NotebookBase(BaseModel):
    name: str
    description: Optional[str] = None
    tags: Optional[List[str]] = []


class NotebookCreate(NotebookBase):
    cells: Optional[List[CellBase]] = []


class NotebookUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    cells: Optional[List[Dict[str, Any]]] = None
    status: Optional[NotebookStatus] = None
    tags: Optional[List[str]] = None


class NotebookOut(NotebookBase):
    id: int
    owner_id: int
    cells: List[Dict[str, Any]]
    status: NotebookStatus
    created_at: datetime
    updated_at: datetime
    owner: Optional[UserOut] = None

    class Config:
        from_attributes = True


class DashboardBase(BaseModel):
    name: str
    description: Optional[str] = None


class DashboardCreate(DashboardBase):
    notebook_id: Optional[int] = None
    layout: Optional[List[Dict[str, Any]]] = []
    widgets: Optional[List[Dict[str, Any]]] = []
    filters: Optional[List[Dict[str, Any]]] = []


class DashboardUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    layout: Optional[List[Dict[str, Any]]] = None
    widgets: Optional[List[Dict[str, Any]]] = None
    filters: Optional[List[Dict[str, Any]]] = None
    status: Optional[NotebookStatus] = None


class DashboardOut(DashboardBase):
    id: int
    notebook_id: Optional[int]
    layout: List[Dict[str, Any]]
    widgets: List[Dict[str, Any]]
    filters: List[Dict[str, Any]]
    status: NotebookStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ExecuteRequest(BaseModel):
    cell_id: str
    cell_type: str  # "sql" | "python"
    code: str
    notebook_id: Optional[int] = None
    context: Optional[Dict[str, Any]] = {}


class ExecuteResult(BaseModel):
    cell_id: str
    success: bool
    type: Optional[str] = None  # "dataframe" | "plotly" | "text" | "error"
    data: Optional[Any] = None
    columns: Optional[List[str]] = None
    shape: Optional[List[int]] = None
    stdout: Optional[str] = None
    error: Optional[str] = None
    traceback: Optional[str] = None
    execution_time_ms: Optional[float] = None


class AuditLogOut(BaseModel):
    id: int
    user_id: int
    action: str
    resource_type: Optional[str]
    resource_id: Optional[int]
    details: Optional[Dict[str, Any]]
    created_at: datetime
    user: Optional[UserOut] = None

    class Config:
        from_attributes = True


class DataSourceTest(BaseModel):
    host: str
    port: int
    database: str
    username: str
    password: str
    db_type: str = "mysql"
