# ⚡ Otenga — Python-Native Business Intelligence Platform

> A collaborative BI platform where data creators write SQL, transform with Python/Pandas, and publish interactive dashboards.

## ✨ Features

| Feature | Details |
|---|---|
| **Polyglot Notebook** | Chain SQL + Python cells. SQL results auto-become DataFrames |
| **Live Execution** | Execute cells against your MySQL database in real-time |
| **Rich Visualizations** | Plotly/Express charts rendered inline — bar, line, scatter, pie, stacked bar |
| **Dashboard Builder** | Drag-and-drop canvas to build and publish interactive dashboards |
| **Superuser Management** | Superusers can disable, re-enable, or delete user accounts |
| **Role-Based Access** | `viewer`, `creator`, `superuser` with fine-grained permissions |
| **SSO Integration** | Single sign-on with any Laravel app — token passthrough, auto user provisioning |
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

**1. Configure environment variables:**

```bash
cp backend/.env.example backend/.env   # then fill in real values
cp .env.example .env                   # then fill in real values
```

> Never commit the real `.env` files — they are git-ignored. Always edit the copies.

**2. Start the backend:**
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**3. Start the frontend:**
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

## 🔗 Laravel SSO Integration

Otenga can be unified with any Laravel application that issues JWTs, giving users a single login across both systems.

### How it works

```
User logs in to Laravel app
        ↓
Laravel redirects to:  https://<otenga>/sso?token=<laravel_jwt>
        ↓
Otenga validates the token using the shared secret
        ↓
User is auto-provisioned in BI_Otenga (first visit) or looked up by email
        ↓
Otenga issues its own session token — user lands on the dashboard
```

### Setup

**1. Configure `.env` on the Otenga backend:**

Copy `.env.example` to `.env` and set the two SSO keys (never commit the real `.env`):

```env
# Must match jwt.secret (or APP_KEY) in the Laravel app's .env
LARAVEL_JWT_SECRET=your_laravel_jwt_secret_here

# URL on the Laravel side that triggers login and redirects back to Otenga
# Laravel should append ?token=<jwt> to the return_to value it receives
LARAVEL_APP_URL=https://your-laravel-app.example.com
```

**2. Configure the Laravel app** to redirect to Otenga after authentication:

```php
// In your Laravel SSO controller
$token = auth()->user()->createToken(); // using tymon/jwt-auth or similar
return redirect("https://<otenga_url>/sso?token={$token}");
```

**3. Restart the backend.** The "Continue with Company App" button appears on the Otenga login page automatically when `LARAVEL_JWT_SECRET` is set.

### Expected JWT claims

The Laravel token should include at minimum:

| Claim | Description |
|---|---|
| `email` | User's email address (used as the unique identifier) |
| `name` | Full name |
| `phone_number` or `phone` | Phone number |
| `role` or `roles` | Role string or array |

### Role mapping

| Laravel role | Otenga role |
|---|---|
| `admin`, `superadmin`, `administrator` | `superuser` |
| `creator`, `analyst`, `data_analyst`, `manager`, `editor`, `staff` | `creator` |
| anything else / missing | `viewer` |

> Roles can be overridden per-user by a superuser inside Otenga after the first SSO login.

### SSO user accounts

- First-time SSO users are created with status `active` — no email verification or approval step is required (they are already vetted by the Laravel app).
- If a user previously registered manually via the Otenga form, their first SSO login will automatically activate the account.
- Users provisioned via SSO have a randomly-generated unusable password; they must always log in through the SSO flow.

---

## 👥 User Management

All users are provisioned exclusively through **Laravel SSO**. There is no self-registration or email verification flow.

### How users get access

```
User logs into the Laravel app
        ↓
Laravel redirects to Otenga with a signed JWT
        ↓
Otenga auto-provisions the user on first visit (status: active)
        ↓
User lands on the dashboard
```

### User Statuses

| Status | Meaning |
|---|---|
| `active` | Can sign in |
| `disabled` | Suspended by superuser |

### Role Permissions

| Role | Capabilities |
|---|---|
| **Viewer** | Browse and view published reports & dashboards |
| **Creator** | Write SQL/Python notebooks, build dashboards, submit for review; access Settings |
| **Superuser** | Full access: manage users (disable/enable/delete/change roles), audit logs |

---

## 🏗️ Architecture

```
otenga/
├── .env                              # Root SSO + DB credentials (git-ignored — copy from .env.example)
├── .env.example                      # Safe template for root .env
├── backend/
│   ├── .env                          # Backend credentials (git-ignored — copy from .env.example)
│   ├── .env.example                  # Safe template for backend .env
│   └── app/
│       ├── main.py                   # FastAPI app + CORS + startup migrations
│       ├── config.py                 # Settings (BI_DB + Data_Science + SMTP + SSO)
│       ├── models.py                 # SQLAlchemy models (MySQL — BI_Otenga)
│       ├── auth.py                   # JWT authentication + role guards
│       ├── database.py               # MySQL engine (auto-creates BI_Otenga schema)
│       ├── execution_engine.py       # SQL + Python sandbox; auto-strips commas from numeric strings
│       └── routers/
│           ├── auth_router.py        # Login (local + Laravel SSO)
│           ├── users.py              # User CRUD + disable/enable/delete
│           ├── notebooks.py          # Notebook CRUD
│           ├── dashboards.py         # Dashboard CRUD
│           └── execution.py          # Cell execution API
│
└── frontend/
    └── src/
        ├── components/
        │   ├── layout/               # Sidebar, TopBar (portal dropdowns), Layout
        │   ├── auth/                 # Login + Register + SSO button
        │   ├── editor/               # Notebook + Cell + ResultViewer
        │   ├── dashboard/            # Dashboard builder + widget config
        │   └── charts/               # Plotly chart renderer
        ├── pages/
        │   ├── SSOCallbackPage.jsx   # Laravel SSO redirect handler
        │   ├── UsersPage.jsx         # User management (members / audit log)
        │   └── ...                   # HomePage, EditorPage, DashboardPage, etc.
        ├── store/                    # Zustand (authStore — includes loginWithSSOToken)
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
MPESA_DB_USER=<see .env>
MPESA_DB_PASSWORD=<see .env>
```

> Credentials are stored in `.env` files which are **git-ignored**. See `.env.example` for the full list of required variables.

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
| POST | `/auth/login` | Sign in with username + password, returns JWT | No |
| GET | `/auth/me` | Current user info | Yes |
| POST | `/auth/sso` | Exchange Laravel JWT for Otenga session | No |
| GET | `/auth/sso/config` | Check whether SSO is enabled | No |

### Users *(superuser only)*
| Method | Path | Description |
|---|---|---|
| GET | `/users/` | List all users |
| GET | `/users/{id}` | Get a single user |
| PUT | `/users/{id}` | Update role / status |
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

Interactive API docs:
- **Local:** http://localhost:8000/api/docs
- **Production:** `{APP_BASE_URL}` on the backend host at `/api/docs` (set `APP_BASE_URL` in `backend/.env`)

---

## 🔒 Security & Environment Variables

Credentials are managed exclusively through `.env` files that are never committed to version control.

| File | Purpose | Committed? |
|---|---|---|
| `.env` | Root SSO + DB credentials | No — git-ignored |
| `.env.example` | Safe template (blank values) | Yes |
| `backend/.env` | Backend DB, SMTP, JWT secret | No — git-ignored |
| `backend/.env.example` | Safe template (blank values) | Yes |

**Setting up on a new machine:**
```bash
cp .env.example .env
cp backend/.env.example backend/.env
# then open both files and fill in real values
```

> SMTP / email variables in `backend/.env.example` are no longer used. They can be left blank.

**CORS:** The backend allows requests from `APP_BASE_URL` (from `backend/.env`) plus local dev origins. To allow additional origins, edit `backend/app/main.py`.

---

## 🗂️ Data Quality

The execution engine automatically cleans data read from MySQL before returning it to the frontend:

- **Comma stripping in numeric columns** — string columns where every value is a number formatted with commas (e.g. phone numbers stored as `0722,123,456` or credit limits stored as `50,000`) are cleaned to `0722123456` / `50000`. Columns with genuine textual commas (names, addresses) are left untouched.
