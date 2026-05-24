# ⚡ Job Finder — Python Backend API

A role-based job board REST API built with **FastAPI**, **PostgreSQL**, **SQLAlchemy 2 (async)**, and **Celery/Redis** message queuing. This is a **full Python port** of the Node.js/Express backend — identical API contracts, same URL paths, same cookie auth strategy, and same queue polling pattern, so the **React frontend works with either backend without any changes**.

---

## 🛠 Tech Stack

| Technology | Purpose | Node.js Equivalent |
|---|---|---|
| FastAPI | HTTP server & routing | Express.js |
| SQLAlchemy 2 (async) | Database ORM | Prisma |
| Alembic | DB migrations | Prisma Migrate |
| asyncpg | Async PostgreSQL driver | — |
| PostgreSQL 16 | Relational database | Same |
| Redis 7 | Message broker | Same |
| Celery | Async job queue | Bull |
| Pydantic v2 | Request validation + env schema | Zod |
| passlib[bcrypt] | Password hashing | bcrypt |
| python-jose | JWT access & refresh tokens | jsonwebtoken |
| slowapi | Rate limiting | express-rate-limit |
| GZipMiddleware | Response compression (production) | compression |
| Docker / Docker Compose | Containerised dev environment | Same |

---

## 🏗 Project Structure

```
app/
├── main.py                        # FastAPI app factory, middleware, routers
├── config.py                      # pydantic-settings env validation — exits if vars missing
├── database.py                    # Async SQLAlchemy engine + get_db() dependency
├── models/                        # SQLAlchemy ORM models (mirrors Prisma schema exactly)
│   ├── user.py                    # User, Role enum
│   ├── profiles.py                # JobSeekerProfile, RecruiterProfile
│   ├── job.py                     # Job (with all Prisma @@index)
│   ├── application.py             # Application, ApplicationStatus enum
│   ├── saved_job.py               # SavedJob (unique constraint)
│   ├── notification.py            # Notification, NotificationType enum
│   └── report.py                  # Report, ReportStatus enum
├── schemas/                       # Pydantic v2 request schemas (mirrors Zod validators)
│   ├── auth.py                    # LoginSchema, SignupSchema
│   ├── jobseeker.py               # UpdateJobSeekerProfileSchema
│   ├── recruiter.py               # RecruiterSignupSchema, UpdateRecruiterProfileSchema
│   ├── job.py                     # JobSchema, JobUpdateSchema
│   └── application.py             # ApplicationSchema, ApplicationStatusSchema
├── routers/                       # FastAPI routers — same URL prefixes as Node.js
│   ├── auth.py                    # /api/auth/*
│   ├── jobs.py                    # /api/jobs/*
│   ├── jobseeker.py               # /api/jobseeker/*
│   ├── recruiter.py               # /api/recruiter/*
│   └── queue.py                   # /api/queue/*
├── services/                      # Business logic (direct port of Node.js services/)
│   ├── auth_service.py
│   ├── job_service.py
│   ├── jobseeker_service.py
│   └── recruiter_service.py
├── middleware/
│   ├── auth.py                    # require_auth, authorize_roles (FastAPI dependencies)
│   └── error_handler.py           # Global exception handlers
├── utils/
│   ├── hash.py                    # hash_password, compare_passwords
│   ├── token.py                   # generate/verify JWT access & refresh tokens
│   └── auth_utils.py              # Cookie setters, token helper, email check
├── errors/
│   └── app_error.py               # AppError(message, status_code)
└── queue/                         # Celery worker (mirrors Bull queue/)
    ├── celery_app.py              # Celery instance + Redis config
    ├── tasks.py                   # apply_to_job_task, save_job_task
    └── worker.py                  # Worker entry point
alembic/                           # DB migrations (replaces prisma/migrations/)
scripts/
├── docker-entrypoint.sh           # alembic upgrade head → uvicorn
└── seed.py                        # Seed script (mirrors prisma/seed.ts)
```

---

## 🔐 Roles & Permissions

| Role | Description |
|---|---|
| `JOB_SEEKER` | Browse jobs, apply, save jobs, manage profile |
| `RECRUITER` | Post/edit/delete jobs, view applicants, manage company profile |
| `ADMIN` | Reserved; no admin routes exposed yet |

---

## 🚀 Setup & Running Locally

### Prerequisites
- Docker & Docker Compose (recommended)
- Python 3.12+ (only needed if running without Docker)

### 1. Configure environment

```bash
cp .env.sample .env
# Edit .env with your actual values
```

**Key `.env` variables:**

```env
DATABASE_URL=postgresql+asyncpg://job_finder_user:secure_password_123@job-finder-db-python:5432/job_finder
ACCESS_TOKEN_SECRET=<32-char random string>
REFRESH_TOKEN_SECRET=<32-char random string>
ACCESS_TOKEN_EXPIRES_IN=15m
REFRESH_TOKEN_EXPIRES_IN=7d
PORT=5002
APP_ENV=development        # set to "production" to enable gzip compression
REDIS_URL=redis://job-finder-redis-python:6379
QUEUE_CONCURRENCY=5
CORS_ORIGIN=http://localhost:3000
```

> **Strict env validation:** `app/config.py` parses all variables through a Pydantic `BaseSettings` schema at startup. If any required variable is missing or invalid (e.g. a secret shorter than 16 characters), the process **exits immediately** with a descriptive error — mirroring the Node.js `env.ts` behaviour.

**Generate secrets:**

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2. Start with Docker

```bash
docker compose up --build
```

This starts:
- `job-finder-backend-python` on **port 5002**
- `job-finder-worker-python` (Celery) — processes queue tasks
- `job-finder-db-python` (PostgreSQL 16) on **port 5432**
- `job-finder-redis-python` (Redis 7) on **port 6379**
- `pgAdmin4` on **port 5050**

> The entrypoint automatically runs `alembic upgrade head` before starting uvicorn — no manual migration step needed.

### 3. Seed the database

```bash
docker exec job-finder-backend-python python scripts/seed.py
```

This creates demo users:

| Email | Password | Role |
|---|---|---|
| `recruiter@acme.com` | `password123` | RECRUITER |
| `jane@example.com` | `password123` | JOB_SEEKER |

### 4. Run locally (without Docker)

```bash
# Install dependencies
pip install -r requirements.txt
pip install psycopg2-binary   # needed by Alembic

# Apply migrations (requires a running Postgres)
alembic upgrade head

# Start the API server
uvicorn app.main:app --reload --port 5002

# Start the Celery worker (separate terminal)
celery -A app.queue.worker worker --loglevel=info
```

---

## 🌐 Interactive API Docs

When `APP_ENV=development`, FastAPI auto-generates:
- **Swagger UI:** `http://localhost:5002/docs`
- **ReDoc:** `http://localhost:5002/redoc`

> Docs are **disabled** in production (`APP_ENV=production`).

---

## 🧪 API Reference

Base URL: `http://localhost:5002/api`

> All error responses return `{ "error": "<message>" }`.

---

### Auth — `/api/auth`

| Method | Endpoint | Auth | Rate Limit | Description |
|---|---|---|---|---|
| `POST` | `/signup/jobseeker` | — | 5/hr | Register as Job Seeker |
| `POST` | `/signup/recruiter` | — | 5/hr | Register as Recruiter |
| `POST` | `/upgrade/recruiter` | Cookie (JOB_SEEKER) | — | Upgrade account to Recruiter |
| `POST` | `/login` | — | 10/15min | Login; sets HTTP-only cookies |
| `POST` | `/logout` | — | — | Clears both auth cookies |
| `POST` | `/refresh` | Cookie | 10/15min | Rotate tokens |
| `GET` | `/me` | Cookie | — | Get current user |

**Login** `POST /api/auth/login`
```json
{ "email": "jane@example.com", "password": "password123" }
```
Response: `{ "message": "Logged in successfully" }` + two cookies:
- `Set-Cookie: accessToken=<JWT>; HttpOnly; SameSite=Lax` (15 min)
- `Set-Cookie: refreshToken=<JWT>; HttpOnly; SameSite=Lax` (7 days)

**Signup — Recruiter** `POST /api/auth/signup/recruiter`
```json
{
  "name": "Jane Smith",
  "email": "jane@corp.com",
  "password": "secret123",
  "company_name": "Acme Corp",
  "company_website": "https://acme.com",
  "industry": "Technology",
  "description": "We build cool stuff."
}
```

---

### Jobs — `/api/jobs`

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/all` | — | Paginated active jobs (`?search=`, `?category=`, `?location=`, `?page=`, `?pageSize=`) |
| `GET` | `/{id}` | — | Single job by ID |
| `GET` | `/recruiter` | Cookie (RECRUITER) | Jobs posted by this recruiter |
| `POST` | `/` | Cookie (RECRUITER) | Create a job posting |
| `PUT` | `/{id}` | Cookie (RECRUITER) | Update a job (owner only) |
| `DELETE` | `/{id}` | Cookie (RECRUITER) | Delete a job (owner only) |

**Create / Update Job body:**
```json
{
  "title": "Senior Python Developer",
  "description": "Join our backend team...",
  "requirements": "5+ years Python, FastAPI, PostgreSQL.",
  "location": "Remote",
  "salary_range": "$120,000 – $160,000",
  "category": "Engineering"
}
```

---

### Job Seeker — `/api/jobseeker`

All endpoints require `JOB_SEEKER` role cookie.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/profile` | Get own profile |
| `PATCH` | `/profile` | Update profile |
| `POST` | `/apply/{job_id}` | **Enqueue** application → `202 + jobId` |
| `GET` | `/applications` | List own applications |
| `DELETE` | `/applications/{id}` | Withdraw an application |
| `POST` | `/saved/{job_id}` | **Enqueue** save-job write → `202 + jobId` |
| `GET` | `/saved` | List saved jobs |
| `DELETE` | `/saved/{job_id}` | Remove a saved job |

> **Async writes:** `POST /apply/{job_id}` and `POST /saved/{job_id}` enqueue via Celery and return `202 Accepted`. Poll `GET /api/queue/job/{jobId}` to track completion — identical to the Bull pattern.

**Apply response (202):**
```json
{ "jobId": "<celery-task-id>", "type": "apply-to-job", "status": "queued" }
```

---

### Recruiter — `/api/recruiter`

All endpoints require `RECRUITER` role cookie.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/profile` | Get recruiter/company profile |
| `PATCH` | `/profile` | Update company profile |
| `GET` | `/jobs/{job_id}/applications` | List applicants for a job |
| `PATCH` | `/applications/{id}/status` | Update application status |

**Application statuses:** `submitted` · `shortlisted` · `under_review` · `rejected`

```json
{ "status": "shortlisted" }
```

---

### Queue — `/api/queue`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/job/{job_id}` | Poll status of a queued Celery task |

**Response:**
```json
{
  "id": "<celery-task-id>",
  "type": "apply-to-job",
  "status": "completed",
  "result": { "id": "...", "jobId": "...", "status": "submitted" }
}
```

**Status values** (mapped from Celery → Bull-compatible):

| Celery | Returned as |
|---|---|
| `PENDING` / `RECEIVED` | `waiting` |
| `STARTED` | `active` |
| `SUCCESS` | `completed` |
| `FAILURE` / `REVOKED` | `failed` |

On `completed` → `result` field is present.  
On `failed` → `failedReason` field is present.

---

## 🛡 Global Error Handling

Registered in `app/main.py` — mirrors `errorHandler.middleware.ts`.

| Condition | HTTP Status | Response |
|---|---|---|
| `AppError` instance | `err.status_code` | `{ "error": err.message }` |
| SQLAlchemy unique constraint | `409` | `{ "error": "A record with that value already exists." }` |
| JWT errors | `401` | `{ "error": "<jwt message>" }` |
| All other errors | `500` | `{ "error": "Internal server error" }` (detail logged server-side) |

Throw from any service:
```python
raise AppError("Job not found", 404)
```

---

## 🔒 Security & Cookie Strategy

Both `accessToken` and `refreshToken` are set as `HttpOnly; SameSite=Lax` cookies — identical to the Node.js version.

| Attribute | Value | Why |
|---|---|---|
| `httponly` | `True` | Invisible to JavaScript — prevents XSS token theft |
| `secure` | `True` in production | HTTPS-only transmission |
| `samesite` | `"lax"` | Allows top-level navigation, blocks cross-site mutations |

**Why `Lax` and not `Strict`?** `SameSite=Strict` would silently drop the cookie on OAuth redirects and email links. `Lax` allows the cookie on top-level GET navigations while still blocking cross-site `POST`/`PUT`/`PATCH`/`DELETE` — covering the real CSRF surface without breaking auth flows.

---

## 🔄 Rate Limiting

| Limiter | Routes | Window | Max |
|---|---|---|---|
| Auth limiter | `POST /login`, `POST /refresh` | 15 min | 10 |
| Signup limiter | `POST /signup/*` | 1 hour | 5 |

Implemented via `slowapi` — mirrors `express-rate-limit`. Returns `429 Too Many Requests` on breach.

---

## 🗄 Database

### Alembic migrations

```bash
# Create a new migration (autogenerate from model changes)
alembic revision --autogenerate -m "describe your change"

# Apply all pending migrations
alembic upgrade head

# Roll back one migration
alembic downgrade -1
```

### Useful psql commands

```bash
# Connect from PowerShell
docker exec -it job-finder-db-python psql -U job_finder_user -d job_finder -W
# Password: secure_password_123

# Inside psql
\dt          # list all tables
\d users     # describe users table
```

### pgAdmin4

- URL: `http://localhost:5050`
- Login: `admin@example.com` / `admin`

### Check if port 5432 is in use (Windows)

```powershell
netstat -ano | findstr :5432
Get-Process -Id (Get-NetTCPConnection -LocalPort 5432).OwningProcess | Stop-Process -Force
```

---

## 🌱 Seeding

```bash
# Inside Docker
docker exec job-finder-backend-python python scripts/seed.py

# Locally
python scripts/seed.py
```

The seed script is **idempotent** — safe to run multiple times.

---

## ⚙️ Celery Worker

The Celery worker runs as a separate process/container. In Docker Compose it starts automatically as the `celery_worker` service.

```bash
# Start locally (separate terminal)
celery -A app.queue.worker worker --loglevel=info

# Monitor tasks (Flower UI — optional)
pip install flower
celery -A app.queue.worker flower --port=5555
```

---

## 🔗 Frontend Compatibility

The React frontend at `../job-finder-react` proxies all `/api` calls to port **5002**. It works with **either** this Python backend or the Node.js backend — they expose identical:
- URL paths and HTTP methods
- Request/response JSON shapes
- Cookie names (`accessToken`, `refreshToken`)
- Queue polling contract (`202` → poll `/api/queue/job/{id}`)

> Switch between backends by running only one `docker compose up` at a time (they share port 5002 and 5432).

---

## 🔧 Service Upgrade Checklist

- [ ] Read release notes for breaking changes
- [ ] Check data volume compatibility (Postgres major versions are NOT backward-compatible)
- [ ] Back up data if the volume will be deleted
- [ ] Update image tag in `docker-compose.yml`
- [ ] Run `docker compose pull <service>`
- [ ] Run `docker compose up -d <service>` (or `--build` for backend)
- [ ] Check logs: `docker compose logs -f <service>`
- [ ] Run smoke tests against the API
- [ ] Commit the `docker-compose.yml` change

### PostgreSQL major version upgrade (e.g. 15 → 16)

> ⚠️ Major versions are NOT data-compatible. Delete the volume or dump/restore.

```bash
# Dev (data is disposable)
docker compose down -v
# Bump image tag in docker-compose.yml, then:
docker compose up --build
docker exec job-finder-backend-python alembic upgrade head
docker exec job-finder-backend-python python scripts/seed.py
```

### Python runtime upgrade

Update the `FROM` line in `Dockerfile`:
```dockerfile
FROM python:3.13-slim   # was python:3.12-slim
```
Then rebuild: `docker compose up --build backend`
