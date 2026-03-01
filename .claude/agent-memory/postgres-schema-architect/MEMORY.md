# DO-main Project Memory

## Project: DO-main (Desk Booking System)

Working directory: /Users/alishtelman/Documents/DO-main

## Key Architectural Decisions

### ID Strategy
- **Integer IDs (SERIAL / autoincrement)** — NOT UUIDs.
- Frontend and schemas.py use `PositiveInt` for all IDs.
- Do not switch to UUID without explicit user request.

### SQLAlchemy Setup
- `Base.metadata.create_all()` at startup — no Alembic.
- `DATABASE_URL` from env, fallback: `postgresql://postgres:postgres@localhost:5432/deskbooking`
- SQLAlchemy 2.x compatible syntax used throughout.

### Business Rules Encoded as DB Constraints
- `Desk.type` CHECK: `('flex', 'fixed')`
- `Reservation.status` CHECK: `('active', 'cancelled')`
- `User.role` CHECK: `('admin', 'user')`
- Overlap logic enforced in application layer (storage.py), not DB exclusion constraint.
  Reason: existing storage.py already handles overlap via `_time_overlaps()`; DB-level
  overlap prevention would require `btree_gist` extension — not confirmed available.

### Schema-to-Model Type Mappings (from schemas.py)
- `Policy.office_id`: Optional FK (nullable) — a policy can be global (no office).
- `Policy.min_duration_minutes` default = 30, `no_show_timeout_minutes` default = 15.
- `Reservation.user_id`: `String(120)` — NOT a FK. Frontend passes username as plain string.
- `Desk.assigned_to`: `String(120)` — NOT a FK. Stores username string.
- `Reservation.start_time` / `end_time`: NOT NULL in current schemas (required fields).

### Naming Conventions
- Table names: plural snake_case (`users`, `offices`, `floors`, `desks`, `reservations`, `policies`)
- Index names: `ix_<table>_<column>` pattern for SQLAlchemy-generated; custom: `idx_<table>_<col>`
- Column names: snake_case matching schema field names exactly

### Files Created
- `backend/app/database.py` — engine, SessionLocal, Base, get_db
- `backend/app/models.py` — all SQLAlchemy ORM models
- `backend/app/config.py` — pydantic-settings BaseSettings
- `.env.example` — template env file
- `.env` — local docker-compose env file

### Dependencies Added to requirements.txt
- `sqlalchemy` (2.x)
- `psycopg2-binary`
- `pydantic-settings`

### User Table Note
- `User` model exists in DB but auth is currently header-based (`X-Role: admin`).
- The `users` table is forward-looking for JWT auth integration.
- `username` column is indexed and unique; matches the string used in `user_id` / `assigned_to`.
