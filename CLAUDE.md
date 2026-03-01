# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A corporate desk booking system (система бронирования рабочих мест) for office workspace reservation. Phase 1 MVP with in-memory storage — no database yet.

## Running the Project

**Backend (FastAPI):**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
API runs at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

**Frontend (static files):**
```bash
python -m http.server 5173
```
Access at `http://localhost:5173/frontend/`.

No formal test suite or linter configured yet.

## Architecture

```
backend/app/
  main.py      — FastAPI route handlers, CORS config, static file serving
  schemas.py   — Pydantic models for request/response validation
  storage.py   — In-memory data store with threading.Lock for concurrency

frontend/
  index.html   — SPA shell
  app.js       — All frontend logic (~600 lines), hardcoded API base URL (http://localhost:8000)
  styles.css   — Styling
```

The frontend and backend are fully decoupled — the frontend communicates with the backend exclusively via REST API using `fetch()`.

## Key Design Decisions

**Role-based access:** Admin vs. user roles are distinguished by the `X-Role: admin` HTTP header. No authentication system exists yet — the frontend has an "admin toggle" checkbox that sets this header.

**In-memory storage:** All data lives in `storage.py` dictionaries and is lost on restart. `threading.Lock` prevents concurrent write conflicts (e.g., double-bookings).

**Desk types:** Desks are either `flex` (bookable by anyone) or `fixed` (assigned to a specific user via `assigned_to`).

**Availability check:** `/availability` endpoint validates time overlap against existing reservations before a booking is created.

**Floor plans:** PNG images uploaded via `POST /floors/{floor_id}/plan` are stored in `backend/static/` and served at `/static/{filename}`. UUIDs prevent filename collisions.

## Core Data Models (`schemas.py`)

- `Office` — office location
- `Floor` — belongs to an office, has optional `plan_url`
- `Desk` — belongs to a floor, has `type` (flex/fixed), `zone`, `position_x/y`, optional `assigned_to`
- `Reservation` — links user + desk + date + time range, `status` is active/cancelled
- `Policy` — per-office booking rules (min/max days ahead, min/max duration, no-show timeout)

## API Conventions

- Admin-only endpoints check for `X-Role: admin` header and return `403` if absent.
- Conflict responses use `409`. Missing resources use `404`.
- Error bodies follow `{"detail": "..."}` format (FastAPI default).
- CORS allows all origins (dev config — restrict for production).

## Roadmap Context (`docs/`)

- **Phase 2:** QR code check-in, no-show auto-cancellation
- **Phase 3:** Interactive floor plan editor, analytics dashboard
- **Phase 4:** Microsoft Teams/Outlook integrations, BI export

When implementing new features, check `docs/ROADMAP.md` and `docs/NEXT_STEPS.md` for planned scope.
