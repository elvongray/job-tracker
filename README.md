# Job Hunt Tracker

A multi-user productivity suite for organizing job searches end-to-end. The platform combines rich application tracking, Kanban-style workflows, reminder automation, analytics, and offline support to help candidates stay on top of every opportunity.

---

## Table of Contents

- [Product Overview](#product-overview)
- [Architecture](#architecture)
- [Backend](#backend)
- [Frontend](#frontend)
- [Getting Started](#getting-started)
  - [Backend Setup](#backend-setup)
  - [Frontend Setup](#frontend-setup)
- [Environment Configuration](#environment-configuration)
- [Key Workflows](#key-workflows)
- [Testing](#testing)
- [Roadmap](#roadmap)

---

## Product Overview

Job Hunt Tracker centralizes every aspect of a candidate’s pipeline:

- **Applications**: Capture company, role, source, salary expectations, notes, tags, and attachments. Track status transitions from Draft to Offer and beyond with optimistic concurrency controls.
- **Activities**: Log interviews, follow-ups, calls, and emails. Include scheduling details, interview stages, prep checklists, and outcomes tied to each application.
- **Reminders & Notifications**: Automate nudges via in-app, email, or calendar channels. Support custom reminders, default rules, quiet hours, and `.ics` calendar links.
- **Kanban & Filters**: Visualize applications by stage with drag-and-drop updates. Filter by status, tags, priority, source, date ranges, and more.
- **Analytics**: Summaries, trends, conversion rates, and time-in-stage metrics help candidates prioritize efforts.
- **Offline-first**: The React app uses IndexedDB with an encrypted outbox to queue mutations when offline.

Designed for security from day one: per-user data isolation, JWT + CSRF protections, encrypted caches, and optimistic concurrency across all mutating routes.

---

## Architecture

| Layer               | Tech Stack                                                       | Highlights                                                                                   |
| ------------------- | ---------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| **Frontend**        | Next.js, TypeScript, Tailwind CSS, TanStack React Query, Zustand | Offline cache with IndexedDB, optimistic UI, Kanban board, analytics dashboards              |
| **Backend**         | FastAPI, SQLAlchemy, PostgreSQL                                  | Modular service layer, cursor-based pagination, RFC 7807 error responses, optimistic locking |
| **Background Jobs** | Celery, Redis, APScheduler                                       | Reminder dispatch, quiet-hours deferral, email/calendar integrations                         |
| **Auth**            | Passwordless magic links + Google OAuth (planned), JWT sessions  | Token rotation, session timeout controls                                                     |

Supporting tooling: Alembic migrations, Sentry for monitoring, structured logging, and pluggable email/calendar providers.

---

## Backend

Located in [`backend/`](backend), the FastAPI service is organized by domain:

- `applications/`: SQLAlchemy models, Pydantic schemas, services, and routers for application CRUD, filtering, cursor pagination, and status transitions.
- `activities/`: Manage interview/follow-up activities per application with optimistic concurrency, scheduling constraints, and reminder relationships.
- `reminders/`: Custom and automated reminder management, including channel arrays, due date filters, and concurrency-safe updates.
- `auth/`: Signup/login (JWT-based today), token utilities, and security dependencies. Planned upgrades include passwordless flows and OAuth.
- `core/`: Configuration (`pydantic-settings`), exception handling, logging utilities, and shared helpers.
- `db/`: SQLAlchemy engine/session management, base declarative class with UTC timestamps, and DB dependencies for FastAPI.

### API Features

- RESTful endpoints under `/applications`, `/activities`, and `/reminders` with ETag/If-Match headers for safe concurrent updates.
- RFC 7807 “Problem Details” error contract with request metadata and correlation IDs.
- Cursor-based pagination for scalable listing of applications.
- Query filters for reminders (due ranges, sent status) and activities by parent application.

### Logging & Observability

- Structured JSON logs with `user_id`, `application_id`, `activity_id`, or `reminder_id` context where applicable.
- Hooks for Sentry and OpenTelemetry (enable via environment settings).

---

## Frontend

Located in [`frontend/`](frontend), the Next.js app (App Router) plans to deliver:

- **Kanban Dashboard**: Draggable columns for each application status with sidebar details.
- **Application Forms**: Guided creation with sensible defaults (status, source, dates).
- **Activity Timelines**: Inline editing and scheduling helpers.
- **Reminder Center**: Manage upcoming nudges, channels, and quiet hours.
- **Analytics Views**: Stage conversion charts, source breakdowns, and response time metrics.

State management uses Zustand for UI state and TanStack React Query for server cache synchronization. IndexedDB maintains an encrypted offline cache with conflict resolution on reconnect.

---

## Getting Started

### Backend Setup

```bash
cd backend

# Create virtual environment
uv venv --python 3.11
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
uv sync

# Run database migrations (placeholder)
alembic upgrade head

# Start API
uvicorn src.app:app --reload
```

### Frontend Setup

```bash
cd frontend

npm install
npm run dev
```

The frontend expects a backend at `http://localhost:8000` by default. Configure `NEXT_PUBLIC_API_BASE_URL` if you change ports/hosts.

---

## Environment Configuration

Create `.env` files at the root of each app:

### `backend/.env`

```env
APP_NAME="Job Hunt Tracker"
DATABASE_URL="postgresql://user:password@host:5432/job_hunt_tracker"
JWT_SECRET_KEY="replace-me"
JWT_ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=30
BACKEND_CORS_ORIGINS=["http://localhost:3000"]
FRONTEND_HOST="http://localhost:3000"
```

### `frontend/.env.local`

```env
NEXT_PUBLIC_API_BASE_URL="http://localhost:8000"
```

Other services (email providers, Redis, S3, etc.) will require additional keys as those integrations come online.

---

## Key Workflows

- **Applications**: `GET/POST/PATCH/DELETE /applications` with cursor pagination and filters.
- **Activities**: `GET/POST /activities` with query param `application_id`; `PATCH/DELETE /activities/detail` with `activity_id`.
- **Reminders**: `GET/POST /reminders`; `PATCH/DELETE /reminders/detail` with `reminder_id`. Filtering by due date and sent status supported.
- **Auth**: `POST /auth/signup`, `/auth/login`; token verification handled via dependency injection for secure routes.

All mutating endpoints require an `If-Match` header carrying the current entity version.

---

## Testing

### Backend

- `pytest` (async-ready) with httpx for integration tests.
- Targeted unit tests for schema validation, default reminder scheduling, and concurrency error handling.
- Celery workers and APScheduler jobs mocked for deterministic reminder tests.

### Frontend

- Playwright for E2E flows: application creation, Kanban drag/drop, reminder scheduling, offline mutation replay.
- Vitest/React Testing Library for component-level validation.
