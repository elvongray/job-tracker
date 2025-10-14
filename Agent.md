# Job Hunt Tracker — Developer-Ready Specification (MVP v1)

## 1. Product Scope

### 1.1 Goals

A multi-user web app to track job applications end-to-end with:

- Application logging, interviews & follow-ups (activities), reminders.
- Kanban board for daily tracking.
- Analytics page for insights and trends.
- Ephemeral in-app notifications; email/calendar reminders.
- Cloud-first; later: Electron app for local/cloud sync.

### 1.2 Non-Goals (v1)

- File uploads (links only for resumes/JDs).
- Team/workspace sharing.
- Google Calendar OAuth (use `.ics` attachments/links).
- Data export/import (deferred).
- Real-time WebSockets (use polling).

---

## 2. Users & Use Cases

### 2.1 Personas

- **Individual Job Seeker** — tracks many applications across sources; needs reminders and a clear pipeline view.

### 2.2 User Stories

- Create an application quickly with minimal fields and sensible defaults.
- Move cards across Kanban columns to update status.
- Add interviews/follow-ups as activities; set custom reminders.
- Receive reminders (email/in-app/calendar) respecting quiet hours.
- View analytics (counts, conversion rates, time-in-stage, source breakdown).
- Filter, tag, and archive applications.

### 2.3 Success Metrics

- Time to create first application < **15s**.
- **90%** of reminders dispatched within **1 minute** of due time (outside quiet hours).
- **0** data-loss incidents from conflict resolution.

---

## 3. Functional Requirements

### 3.1 Applications

**Fields**

- Required: `company`, `role_title`.
- Defaults: `status=Applied`, `source=Other`, `application_date=today`, `priority=None`, `location_mode=remote`.
- Optional: `job_url`, `location_text`, `timezone`, `salary_min/max/currency`, `job_requisition_id`, `seniority_level`, `tech_keywords[]`, `resume_url`, `cover_letter_url`, `cover_letter_used`, `contacts_inline JSON`, `next_action`, `next_action_due`, `notes`, `tags[]`, `attachments_links[]`, `archived_at`.

**Status workflow**

```
Draft → Applied → Screening → Recruiter_Call → Tech_Screen → Interview_Loop → Offer
→ (Accepted | Declined) → Rejected → On_Hold
```

### 3.2 Activities (per Application)

**Common fields**

- `type (Interview|FollowUp|Call|Email|Other)`, `status (scheduled|done|canceled)`,
- `starts_at`, `duration_minutes`, `timezone`,
- `outcome`, `next_action`, `next_action_due`, `notes`, `related_contacts JSON`.

**Interview-specific**

- `interview_stage (screening|technical|loop|offer|other)`,
- `interview_medium (onsite|zoom|phone|google_meet|teams|other)`,
- `location_or_link`, `agenda`, `prep_checklist JSON`.

**Follow-up-specific**

- `followup_channel (email|linkedin|phone|other)`, `template_used`, `reply_deadline`.

### 3.3 Reminders & Notifications

- **Default rules**

  - **Applied** → remind in **7 days** if no response (in-app + email).
  - **Screening scheduled** → remind **24h** & **1h** before (in-app + calendar).
  - **Interview loop** → **48h** & **2h** before; post-interview follow-up in **2 days** (in-app + email + calendar).
  - **Offer** → remind to respond in **3 days**; then daily (in-app + email).
  - **On Hold** → ping every **14 days** (in-app).
  - **Rejected/Accepted** → no reminders.

- **Custom reminders** per application/activity.
- **Channels**: in-app (ephemeral), email, calendar via `.ics`.
- **Quiet hours** (per user, e.g., 21:00–08:00) — defer sends during the window.

### 3.4 Views

- **Kanban**: columns by status; drag-and-drop; **sidebar** detail view on card click.
- **Analytics**: totals; stage conversion %; avg time-in-stage; applications over time; source breakdown; pending responses; date range filters.

### 3.5 Organizing & Finding

- **Filters**: status, company, role, source, tags, priority, date range, location, salary, has-due-reminders.
- **Tags**: free-form; (color labels later).
- **Priority**: `None|Low|Medium|High`.
- **Saved views**: e.g., “This Week’s Follow-ups”, “Active Interviews”.
- **Archive**: set `archived_at`; excluded from board, included in analytics.

---

## 4. Non-Functional Requirements

- **Performance**: P95 API latency < **300ms** (excluding external email provider).
- **Availability**: **99.5%** target.
- **Security**: per-user hard isolation; JWT sessions; CSRF for unsafe methods; encrypted local cache.
- **Privacy**: store PII minimally (inline contacts).
- **Timezones**: store UTC; render per user’s timezone (default Africa/Lagos).

---

## 5. Architecture & Technology

- **Frontend**: Next.js, Tailwind, Zustand (UI state), TanStack React Query (server cache, polling), IndexedDB for offline cache + outbox (encrypted).
- **Backend**: FastAPI + SQLAlchemy (PostgreSQL).
- **Background**: Celery + Redis; APScheduler inside worker for periodic scans (every 5 min).
- **Email**: Resend/SendGrid provider (pluggable).
- **Calendar**: generate `.ics` files/links; attach to emails.
- **Auth**: Passwordless (magic link) + Google OAuth, email verification, session timeout.
- **Deployment**: Managed Postgres/Redis; HTTPS; env secrets (KMS).

---

## 6. Data Model (ORM summary)

Use SQLAlchemy ORM (typed, UUID PKs, enums) with the following entities:

### 6.1 Users

- `id (uuid)`, `email (unique)`, `display_name`, `timezone (default: Africa/Lagos)`,
- `email_verified_at`, `session_timeout_mins (default: 4320)`,
- `created_at`, `updated_at`.

### 6.2 UserSettings

- `user_id (pk, fk users)`, `quiet_hours_start`, `quiet_hours_end`,
- `reminder_defaults JSON`, timestamps.

### 6.3 Applications

- `id (uuid, client-generated OK)`, `user_id (fk)`,
- Required: `company`, `role_title`.
- Defaults: `status=Applied`, `source=Other`, `application_date=today`, `priority=None`, `location_mode=remote`.
- Optional fields as listed in **3.1**.
- `version BIGINT` for optimistic concurrency.
- Indexes: `(user_id,status)`, `(user_id,archived_at)`, `(user_id,next_action_due)`, `(user_id,created_at desc)`, GIN on `tags`.
- Checks: `salary_min <= salary_max` when both present.

### 6.4 Activities

- `id (uuid)`, `user_id (fk)`, `application_id (fk)`,
- Fields as in **3.2**, plus `version BIGINT`.
- Indexes: `(user_id, starts_at)`, `(user_id, next_action_due)`.
- Check: if `status='scheduled'`, `starts_at` must not be null.

### 6.5 Reminders

- `id (uuid)`, `user_id (fk)`, `application_id (nullable fk)`, `activity_id (nullable fk)`,
- `title`, `due_at`, `channels[]`, `sent bool`, `sent_at`, `dedupe_key`, `meta JSON`, timestamps, `version`.
- Check: at least one of `application_id` or `activity_id` must be present.
- Index: `(user_id, due_at)` where `sent=false`.
- Unique: `(user_id, dedupe_key)` (nullable) for idempotency.

> Enums: `AppStatus`, `PriorityLevel`, `ActivityType`, `ActivityStatus`, `InterviewStage`, `InterviewMedium`, `FollowupChannel`, `ReminderChannel`.

---

## 7. API (REST)

### 7.1 Auth

- `POST /auth/magic-link` — send sign-in link.
- `POST /auth/magic-link/verify` — verify token, issue session (JWT in HttpOnly cookie).
- `GET /auth/google` — OAuth start/callback (frontend flow).
- `POST /auth/logout`
- `GET /auth/me` — returns user + settings.

_Security_: HttpOnly JWT + SameSite=Lax; CSRF token on unsafe methods.

### 7.2 Applications

- `GET /applications?cursor=&limit=&status=&q=&tag=&priority=&archived=&sort=`

  - **Cursor pagination** (by `created_at,id`).

- `POST /applications` — create (accept client UUID).
- `GET /applications/{id}` — detail.
- `PATCH /applications/{id}` — partial update; **expects** `If-Match: <version>`.
- `DELETE /applications/{id}` — hard delete.

### 7.3 Activities

- `GET /applications/{id}/activities`
- `POST /applications/{id}/activities`
- `PATCH /activities/{id}` — with `If-Match`.
- `DELETE /activities/{id}`

### 7.4 Reminders

- `GET /reminders?due_before=&due_after=&sent=&cursor=&limit=`
- `POST /reminders` — custom reminder.
- `PATCH /reminders/{id}` — reschedule/cancel; `If-Match`.
- `DELETE /reminders/{id}`

### 7.5 Analytics

- `GET /analytics/summary?from=&to=`
- `GET /analytics/trends?group_by=day|week|month&from=&to=`
- `GET /analytics/source-breakdown?from=&to=`
- (Optional later) `GET /analytics/stage-conversion?from=&to=`

### 7.6 Settings

- `GET /settings`
- `PATCH /settings` — quiet hours, defaults.

#### Example Requests

**Create Application**

```http
POST /applications
Content-Type: application/json
Authorization: Bearer <JWT>

{
  "id": "3f6c3b7e-1f8f-476d-9b2b-5e4e2e2f5a11",
  "company": "Acme Corp",
  "role_title": "Backend Engineer",
  "source": "LinkedIn",
  "status": "Applied",
  "application_date": "2025-10-13",
  "contacts_inline": [{"name": "Jane Recruiter", "email": "jane@acme.com"}],
  "tags": ["backend", "python"]
}
```

**Optimistic Concurrency Update**

```http
PATCH /applications/3f6c3b7e-...
If-Match: 2
Content-Type: application/json

{
  "status": "Screening",
  "next_action_due": "2025-10-15T09:00:00Z"
}
```

- If server row `version != 2` → **409 Conflict** with latest row; client reconciles.

---

## 8. Background Jobs & Reminder Engine

### 8.1 Worker

- **Celery** with queues: `email`, `in_app`, `calendar`, `analytics`.
- **APScheduler** (in worker) every **5 minutes**:

  - Find `reminders` due (`due_at <= now()` and `sent=false`).
  - Respect quiet hours: delay to quiet end if necessary.
  - Enqueue channel-specific tasks.

- **Idempotency**: use `dedupe_key` to avoid duplicate sends.
- **Retries**: exponential backoff with jitter; max 10 before DLQ/alert.

### 8.2 Email & Calendar

- Email templates per reminder type (status-driven vs custom).
- Include `.ics` attachment (VEVENT) and a web link to the application/activity.

---

## 9. Offline, Sync & Local Cache

### 9.1 Client Policy

- **Hybrid**: mutate local (Zustand + IndexedDB outbox) → enqueue API mutation (React Query).
- **IDs**: client-generated UUIDs for offline-created items.
- **Sync triggers**: on mutation; on network regain; on tab focus; every **30s** when active.
- **Local cache**: Applications + Activities + Reminders (+ minimal prefs) in IndexedDB, **encrypted at rest**.
- **Hygiene**: cap **5,000** records; auto-prune locally cached archived items older than **180 days**.

### 9.2 Conflict Resolution

- **Server-authoritative** using `version` + `If-Match`.
- On **409 Conflict**: fetch latest; auto-apply server state; show non-blocking toast with “Undo local change?” (30s).

---

## 10. Security

- **Auth**: Magic link + Google OAuth; email verification; session timeout (default 3 days).
- **Transport**: HTTPS only; HSTS.
- **Data**: Always scope queries by `user_id` (hard isolation).
- **JWT**: HttpOnly + SameSite=Lax; CSRF token for writes.
- **Rate Limiting**: on `/auth/*`, reminder endpoints (IP + user-based).
- **Secrets**: Environment + KMS; never in repo.
- **Audit**: minimal event log for auth, failed jobs, reminder dispatch.

---

## 11. Error Handling

Use RFC 7807 “Problem Details” for errors:

**4xx**

- `400` ValidationError (Pydantic detail)
- `401` Unauthorized (missing/invalid token)
- `403` Forbidden (cross-tenant access — should never happen)
- `404` Not Found (resource for user not found)
- `409` Conflict (version mismatch with `If-Match`)

**5xx**

- `500` Unexpected — include correlation id.

**Problem Details JSON**

```json
{
  "type": "https://errors.jobtracker.app/conflict",
  "title": "Version conflict",
  "status": 409,
  "detail": "Row version 3 does not match If-Match 2",
  "instance": "req_01HX...W",
  "meta": { "resource": "applications", "id": "..." }
}
```

---

## 12. Testing Plan

### 12.1 Unit Tests

- **Models**: enum constraints; salary range check; scheduled activity requires `starts_at`.
- **Services**: reminder generation by status transitions; quiet-hours deferral logic.
- **Formatters**: email and `.ics` generation validity.

### 12.2 API Tests (FastAPI + httpx + pytest)

- Auth flows: magic link verify; Google OAuth callback (mock).
- CRUD: Applications/Activities/Reminders with per-user isolation.
- Filters, sorting, **cursor pagination**.
- Concurrency: `If-Match` success and **409** paths.

### 12.3 Worker/Integration

- Celery: idempotency, retry/backoff, `dedupe_key`.
- APScheduler: due-scan; quiet-hours behavior (time-freeze).
- Provider failures → DLQ & alert.

### 12.4 E2E (Playwright)

- Create application → drag across Kanban → add interview → reminders created → receives email with `.ics`.
- Offline:

  - Disable network; create/edit locally (client UUIDs).
  - Reconnect; queue flush; server reconciliation.
  - Conflict case produces toast; server state wins.

### 12.5 Performance

- With 5k applications:

  - Board initial load < **1.5s** on broadband.
  - Reminder scan handles **10k** due rows in < **60s**.

---

## 13. Implementation Patterns & Conventions

- **Dependencies**: Inject DB session and current user via FastAPI `Depends`.
- **Services layer**: business logic separate from route handlers.
- **DTOs**: Pydantic models for request/response, enums serialized as strings.
- **Pagination**: cursor-based (`created_at,id`), opaque cursor token.
- **ETag/If-Match**: expose `ETag: W/"<version>"` on GET; require `If-Match` on PATCH/DELETE.
- **Idempotency keys**: for reminders & emails (`dedupe_key`).
- **Logging**: structured logs with `request_id`, `user_id`; include latency per route.

---

## 14. DTO Sketches (Pydantic)

```python
# dto.py (illustrative)
from typing import Optional, List
from pydantic import BaseModel, AnyUrl
from datetime import date, datetime
from enums import AppStatus, PriorityLevel, ActivityType, ActivityStatus, InterviewStage, InterviewMedium, FollowupChannel, ReminderChannel

# Applications
class ApplicationCreate(BaseModel):
    id: Optional[str] = None           # client UUID allowed
    company: str
    role_title: str
    source: Optional[str] = "Other"
    status: Optional[AppStatus] = AppStatus.Applied
    application_date: Optional[date] = None
    job_url: Optional[AnyUrl] = None
    # ... other optional fields ...

class ApplicationUpdate(BaseModel):
    company: Optional[str] = None
    role_title: Optional[str] = None
    status: Optional[AppStatus] = None
    next_action: Optional[str] = None
    next_action_due: Optional[datetime] = None
    # ... partial updates ...

class ApplicationOut(BaseModel):
    id: str
    version: int
    company: str
    role_title: str
    status: AppStatus
    created_at: datetime
    updated_at: datetime
    # ... more fields as needed ...

# Activities
class ActivityCreate(BaseModel):
    type: ActivityType
    status: Optional[ActivityStatus] = ActivityStatus.scheduled
    starts_at: Optional[datetime] = None
    # ... interview/follow-up specifics ...

class ActivityUpdate(BaseModel):
    status: Optional[ActivityStatus] = None
    starts_at: Optional[datetime] = None
    # ... partials ...

# Reminders
class ReminderCreate(BaseModel):
    title: str
    due_at: datetime
    channels: Optional[List[ReminderChannel]] = [ReminderChannel.in_app]
    application_id: Optional[str] = None
    activity_id: Optional[str] = None

class ReminderUpdate(BaseModel):
    title: Optional[str] = None
    due_at: Optional[datetime] = None
    channels: Optional[List[ReminderChannel]] = None
```

---

## 15. Analytics (Server-Side)

- **Summary**: counts by status; totals (applications, interviews, offers, rejections).
- **Trends**: applications grouped by `day|week|month` in selected range.
- **Source breakdown**: histogram on `source`.
- **Avg time-in-stage**: approximate via status transition timestamps (`updated_at` diffs for v1).

---

## 16. Observability

- **Logs**: structured JSON; include `request_id`, `user_id`, error stack traces, Celery task ids.
- **Metrics**: reminder dispatch rate, provider error rate, queue depth, API latency percentiles.
- **Tracing**: optional OpenTelemetry spans for major flows (API, DB, worker).

---

## 17. Migrations & Seeding

- **Alembic** migrations for enums, tables, indexes.
- **Seed** script: demo user + ~10 applications across statuses, a couple interviews, due reminders.

---

## 18. Delivery Milestones

1. **Foundation**: Auth (magic link + Google), users/settings; Applications CRUD.
2. **Kanban + Sidebar**: DnD status updates; sidebar editor; filters/tags; archive.
3. **Activities + Reminders**: CRUD; default rules on status transitions.
4. **Worker + Email/ICS**: Celery/APScheduler; templates; quiet hours; idempotency.
5. **Offline/Sync**: IndexedDB outbox; client UUIDs; `If-Match` conflicts.
6. **Analytics + Polish**: summary/trends/source breakdown; perf pass; tests.

---

## 19. Acceptance Criteria (MVP)

- Create/edit/delete applications & activities; drag cards to change status with optimistic UI.
- Default + custom reminders; emails sent with valid `.ics`; quiet hours respected.
- Analytics reflects correct counts for chosen date range.
- Offline create/edit works; upon reconnect, sync reconciles; conflict toast shown when applicable.
- API endpoints covered by unit/integration tests; E2E happy path (incl. offline) passes.

---

### Appendix A — Implementation Notes

- Enums created as Postgres types via SQLAlchemy `PgEnum(..., create_type=True)`.
- `version` columns exposed as `ETag` and enforced via `If-Match`.
- Use **cursor pagination** for scalability (opaque token).
- Encrypt IndexedDB with AES-GCM (key derived from WebCrypto; store only a wrapped key).

---

**End of Specification**
