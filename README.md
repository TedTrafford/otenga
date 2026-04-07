# ⚡ Otenga — Python-Native Business Intelligence Platform

> A collaborative BI platform where data creators write SQL, transform with Python/Pandas, and publish interactive dashboards — built for **Aleza Credit**.

## ✨ Features

| Feature | Details |
|---|---|
| **Polyglot Notebook** | Chain SQL + Python cells. SQL results auto-become DataFrames |
| **Live Execution** | Execute cells against your MySQL database in real-time |
| **Rich Visualizations** | Plotly/Express charts rendered inline — bar, line, scatter, pie, stacked bar |
| **Dashboard Builder** | Drag-and-drop canvas to build and publish interactive dashboards |
| **Self-Registration** | Users can register themselves; email verification required before approval |
| **Email Verification** | Token-based email verification sent via SMTP (Gmail, Outlook, etc.) |
| **Superuser Approval** | Superusers approve, disable, or delete user accounts |
| **Role-Based Access** | `viewer`, `creator`, `superuser` with fine-grained permissions |
| **Audit Logging** | Full audit trail of all user and admin actions |
| **Fluid Theme** | Glassmorphism UI with animated gradients and nebula effects |

---

## 🚀 Quick Start

### One-Command Start

```bash
chmod +x start.sh
./start.sh
```

Then open **http://localhost:5173**

### Manual Setup

**Backend:**
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

---

## 🔑 Default Credentials

| Username | Password | Role |
|---|---|---|
| `admin` | `admin123` | Superuser |
| `creator` | `creator123` | Creator |
| `viewer` | `viewer123` | Viewer |

> Default accounts are seeded automatically on first run and marked as `active` (no email verification required).

---

## 📧 Email & SMTP Configuration

Copy `backend/.env` and fill in your credentials.  
**Without SMTP** verification links print to the backend console (dev mode).

```env
# Gmail SMTP (recommended)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-gmail@gmail.com
SMTP_PASSWORD=xxxx-xxxx-xxxx-xxxx     # Gmail App Password (see below)
SMTP_FROM_EMAIL=your-gmail@gmail.com
SMTP_FROM_NAME=Otenga BI Platform

# Base URL used to build verification links
APP_BASE_URL=http://localhost:5173
```

### Generating a Gmail App Password

1. Go to [myaccount.google.com/security](https://myaccount.google.com/security) and enable **2-Step Verification**.
2. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords).
3. Choose **Mail → Other (Custom name)** → type `Otenga` → **Generate**.
4. Copy the 16-character password (no spaces) into `SMTP_PASSWORD`.

---

## 👥 User Registration & Approval Flow

```
User registers (viewer only)
        ↓
Verification email sent to inbox
        ↓
User clicks link → email verified
        ↓
Appears in Admin → User Management → "Pending Approval"
        ↓
Superuser approves → account active, user can sign in
```

**Admin fallbacks (no email received):**
- Open **Admin → User Management → Unverified** tab.
- Click **"Verify manually"** to skip email and move the account to Pending Approval.
- Alternatively, find the verification link printed in the backend console.

### User Statuses

| Status | Meaning |
|---|---|
| `email_pending` | Registered; must click email verification link |
| `pending` | Email verified; awaiting superuser approval |
| `active` | Approved; can sign in |
| `disabled` | Suspended by superuser |

### Role Permissions

| Role | Capabilities |
|---|---|
| **Viewer** | Browse and view published reports & dashboards |
| **Creator** | Write SQL/Python notebooks, build dashboards, submit for review; access Settings |
| **Superuser** | Full access: approve/reject submissions, manage users, change roles, audit logs |

---

## 🏗️ Architecture

```
otenga/
├── backend/
│   ├── .env                          # SMTP & DB credentials (create from template)
│   └── app/
│       ├── main.py                   # FastAPI app + startup migrations
│       ├── config.py                 # Settings (BI_DB + Data_Science + SMTP)
│       ├── models.py                 # SQLAlchemy models (MySQL — BI_Otenga)
│       ├── auth.py                   # JWT authentication + role guards
│       ├── database.py               # MySQL engine (auto-creates BI_Otenga schema)
│       ├── email_service.py          # SMTP email sender with console fallback
│       ├── execution_engine.py       # SQL + Python sandbox execution
│       └── routers/
│           ├── auth_router.py        # Login, register, verify-email, resend
│           ├── users.py              # User CRUD + approve/disable/verify
│           ├── notebooks.py          # Notebook CRUD
│           ├── dashboards.py         # Dashboard CRUD
│           └── execution.py          # Cell execution API
│
└── frontend/
    └── src/
        ├── components/
        │   ├── layout/               # Sidebar, TopBar (portal dropdowns), Layout
        │   ├── auth/                 # Login + Register tabs
        │   ├── editor/               # Notebook + Cell + ResultViewer
        │   ├── dashboard/            # Dashboard builder + widget config
        │   └── charts/               # Plotly chart renderer
        ├── pages/
        │   ├── VerifyEmailPage.jsx   # Email verification landing page
        │   ├── UsersPage.jsx         # User management (unverified / pending / members)
        │   └── ...                   # HomePage, EditorPage, DashboardPage, etc.
        ├── store/                    # Zustand (authStore, notebookStore, etc.)
        └── api/                      # Axios client + typed API helpers
```

---

## 🔌 Databases

| Database | Purpose |
|---|---|
| `BI_Otenga` on `139.84.243.180` | App metadata — users, notebooks, dashboards, audit logs |
| `Data_Science` on `139.84.243.180` | Data source queried by notebooks |

Both use the same host credentials. The `BI_Otenga` schema is created automatically on first run.

```env
MPESA_DB_HOST=139.84.243.180
MPESA_DB_PORT=3306
MPESA_DB_USER=staging
MPESA_DB_PASSWORD=...
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, SQLAlchemy, MySQL (pymysql) |
| Execution | Python `exec()` sandbox + SQLAlchemy for MySQL |
| Auth | JWT (python-jose) + native bcrypt |
| Email | Python `smtplib` (STARTTLS / SSL) |
| Frontend | React 18 + Vite |
| State | Zustand |
| Styling | TailwindCSS + custom glassmorphism theme |
| Charts | Plotly.js / react-plotly.js |
| Editor | Monaco Editor (`@monaco-editor/react`) |
| Animations | Framer Motion |
| Layout | react-grid-layout |

---

## 📡 API Endpoints

Base URL: `http://localhost:8000/api/v1`

### Authentication
| Method | Path | Description | Auth required |
|---|---|---|---|
| POST | `/auth/login` | Sign in, returns JWT | No |
| POST | `/auth/register` | Public sign-up (viewer, email_pending) | No |
| GET | `/auth/verify-email?token=` | Verify email from link | No |
| POST | `/auth/resend-verification?email=` | Resend verification email | No |
| GET | `/auth/me` | Current user info | Yes |

### Users *(superuser only)*
| Method | Path | Description |
|---|---|---|
| GET | `/users/` | List all active/disabled users |
| GET | `/users/pending` | List users awaiting approval |
| GET | `/users/unverified` | List users with unverified email |
| PUT | `/users/{id}` | Update role / status |
| POST | `/users/{id}/approve` | Approve a pending account |
| POST | `/users/{id}/verify-email` | Manually verify email (admin bypass) |
| POST | `/users/{id}/disable` | Disable an account |
| POST | `/users/{id}/enable` | Re-enable a disabled account |
| DELETE | `/users/{id}` | Delete a user |
| GET | `/users/audit/logs` | View audit trail |

### Notebooks
| Method | Path | Description |
|---|---|---|
| GET | `/notebooks/` | List notebooks |
| POST | `/notebooks/` | Create notebook |
| PUT | `/notebooks/{id}` | Update notebook |
| POST | `/notebooks/{id}/publish` | Submit for review |
| POST | `/notebooks/{id}/approve` | Approve notebook |

### Execution
| Method | Path | Description |
|---|---|---|
| POST | `/execute/cell` | Execute SQL or Python cell |
| GET | `/execute/schema/tables` | List available tables |
| GET | `/execute/schema/tables/{table}` | Describe table columns |

### Dashboards
| Method | Path | Description |
|---|---|---|
| GET | `/dashboards/` | List dashboards |
| POST | `/dashboards/` | Create dashboard |
| PUT | `/dashboards/{id}` | Update layout / widgets |
| DELETE | `/dashboards/{id}` | Delete dashboard |

Interactive API docs: **http://localhost:8000/api/docs**
