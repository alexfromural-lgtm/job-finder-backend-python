# 📚 Learning Guide — Job Finder Backend (Python / FastAPI)

This branch (`explained/learning-annotations`) adds detailed educational comments
to every source file.  Use it as a companion to the original code.

---

## 🏗️ Project Architecture

```
Client (React) ──HTTP──► FastAPI App (app/main.py)
                              │
                    ┌─────────┼─────────┐
                    ▼         ▼         ▼
                 Routers   Middleware  Error
               (HTTP layer) (Auth/CORS) Handlers
                    │
                    ▼
                 Services  ◄─────── Schemas
              (Business Logic)   (Validation)
                    │
                    ▼
           SQLAlchemy ORM  ◄─── Models
                    │          (DB tables)
                    ▼
              PostgreSQL

         FastAPI ──enqueue──► Redis ──► Celery Worker
                                              │
                                              ▼
                                        Services + DB
```

---

## 📂 File Map (What to Read in Order)

| File | What You Learn |
|------|---------------|
| `app/config.py` | Pydantic settings, env vars, `@property` |
| `app/database.py` | SQLAlchemy async engine, sessions, `yield` deps |
| `app/models/user.py` | ORM models, Enum, relationships, UUID |
| `app/models/job.py` | Foreign keys, indexes, nullable fields |
| `app/models/profiles.py` | One-to-one relations, ARRAY column |
| `app/models/application.py` | Many-to-many via junction table |
| `app/models/saved_job.py` | Composite unique constraint |
| `app/schemas/auth.py` | Pydantic validation, field validators |
| `app/schemas/job.py` | Optional fields, partial updates (PATCH) |
| `app/errors/app_error.py` | Custom exceptions |
| `app/middleware/error_handler.py` | Global exception handlers |
| `app/utils/hash.py` | bcrypt password hashing |
| `app/utils/token.py` | JWT generation & verification |
| `app/utils/auth_utils.py` | httpOnly cookies, security flags |
| `app/utils/camel_response.py` | Custom JSONResponse, regex, recursion |
| `app/middleware/auth.py` | Dependency injection, `Annotated`, factories |
| `app/routers/auth.py` | Route handlers, Depends, cookies |
| `app/routers/jobs.py` | Query params, path params, mixed auth |
| `app/routers/jobseeker.py` | Reusable deps, 202 Accepted, Celery dispatch |
| `app/routers/recruiter.py` | Resource nesting, partial update |
| `app/services/auth_service.py` | Business logic, flush vs commit |
| `app/services/job_service.py` | CRUD, pagination, ILIKE, ceiling division |
| `app/services/jobseeker_service.py` | selectinload, row-level auth, upsert |
| `app/services/recruiter_service.py` | Ownership chain verification |
| `app/queue/celery_app.py` | Celery setup, broker, backend, retries |
| `app/queue/tasks.py` | Sync+async bridge, exponential backoff |
| `app/routers/queue.py` | Task status polling, state mapping |
| `app/main.py` | App factory, middleware order, routers |

---

## 🔑 Key Concepts Index

### Python Fundamentals
- **`@property`** → `app/config.py`
- **`@classmethod` validators** → `app/schemas/auth.py`
- **`Enum`** → `app/models/user.py`, `app/models/application.py`
- **Custom exceptions** → `app/errors/app_error.py`
- **`yield` (generator)** → `app/database.py`
- **Regular expressions** → `app/utils/camel_response.py`
- **Recursion** → `app/utils/camel_response.py`

### FastAPI
- **Dependency injection** → `app/middleware/auth.py`, `app/database.py`
- **`Annotated` type hints** → `app/middleware/auth.py`
- **Router grouping** → `app/routers/*.py`
- **Query parameters** → `app/routers/jobs.py`
- **Path parameters** → `app/routers/jobs.py`
- **Custom response class** → `app/utils/camel_response.py`
- **Exception handlers** → `app/middleware/error_handler.py`
- **Middleware** → `app/main.py`

### SQLAlchemy (ORM)
- **Model definition** → `app/models/user.py`
- **Foreign keys** → `app/models/job.py`
- **Relationships** → `app/models/user.py`, `app/models/profiles.py`
- **Async queries** → `app/services/job_service.py`
- **selectinload** → `app/services/jobseeker_service.py`
- **flush vs commit** → `app/services/auth_service.py`
- **Indexes** → `app/models/job.py`
- **Unique constraints** → `app/models/saved_job.py`

### Security
- **bcrypt hashing** → `app/utils/hash.py`
- **JWT tokens** → `app/utils/token.py`
- **httpOnly cookies** → `app/utils/auth_utils.py`
- **Role-based access** → `app/middleware/auth.py`
- **Row-level authorization** → `app/services/jobseeker_service.py`

### Async Architecture
- **Celery setup** → `app/queue/celery_app.py`
- **Task definition** → `app/queue/tasks.py`
- **Sync/async bridge** → `app/queue/tasks.py`
- **Task status polling** → `app/routers/queue.py`

---

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Copy and fill in environment variables
cp .env.sample .env

# 3. Run database migrations
alembic upgrade head

# 4. Seed the database with test data
python scripts/seed.py

# 5. Start the API server
uvicorn app.main:app --reload --port 5002

# 6. Start the Celery worker (separate terminal)
celery -A app.queue.celery_app worker --loglevel=info
```

---

> **TIP:** Open `http://localhost:5002/docs` in development mode to explore the
> interactive Swagger UI — it shows all endpoints, schemas, and lets you test requests.
