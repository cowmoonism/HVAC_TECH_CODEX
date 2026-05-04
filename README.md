# HVAC Operations Platform Backend

Production-ready Django backend foundation for the HVAC Operations Platform.

## Tech Stack

- Django
- Django REST Framework
- PostgreSQL
- Google Calendar API integration hooks
- Telegram notification hooks
- Render deployment target

## Local Setup

Docker Compose is the recommended local development path because it starts PostgreSQL without installing it on the host machine.

Create a local environment file:

```powershell
Copy-Item .env.example .env
```

Start the backend and database:

```powershell
docker compose up --build
```

If you change `POSTGRES_USER`, `POSTGRES_PASSWORD`, or `POSTGRES_DB`, reset the local database volume before starting again:

```powershell
docker compose down -v
docker compose up --build
```

PostgreSQL only applies those initialization variables when its data directory is first created. Keeping an old volume with new credentials can cause startup errors such as `role "postgres" does not exist`.

The `web` service waits for PostgreSQL readiness, runs migrations, then starts Django with:

```powershell
python manage.py migrate && python manage.py runserver 0.0.0.0:8000
```

Health check:

```text
GET http://127.0.0.1:8000/api/health/
```

Expected response:

```json
{
  "status": "ok"
}
```

Useful Docker commands:

```powershell
docker compose config
docker compose build
docker compose up
docker compose down
```

## Host Python Setup

Use this path only if you already have PostgreSQL available separately.

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Create a local environment file:

```powershell
Copy-Item .env.example .env
```

For host-based development, update `DATABASE_URL` to use `localhost` instead of Docker's `db` hostname:

```text
DATABASE_URL=postgres://postgres:postgres@localhost:5432/hvac_ops
```

Run Django checks:

```powershell
python manage.py check
```

Run deployment checks with production-like settings:

```powershell
python manage.py check --deploy
```

Run automated tests:

```powershell
python manage.py test
```

Run migrations:

```powershell
python manage.py migrate
```

Start the local development server:

```powershell
python manage.py runserver
```

Health check:

```text
GET http://127.0.0.1:8000/api/health/
```

Expected response:

```json
{
  "status": "ok"
}
```

## Authentication

The backend uses JWT authentication through Django REST Framework SimpleJWT.

Auth endpoints:

```text
POST /api/auth/login/
POST /api/auth/refresh/
GET /api/auth/me/
```

Login request:

```json
{
  "username": "manager",
  "password": "password"
}
```

Login response:

```json
{
  "access": "...",
  "refresh": "...",
  "user": {
    "id": 1,
    "username": "manager",
    "email": "manager@example.com",
    "role": "MANAGER"
  }
}
```

Authenticated API requests should send:

```text
Authorization: Bearer <access>
```

`GET /api/auth/me/` returns the same user object. The React dashboard stores the access token, refresh token, and role in `localStorage` for now.

## Technician Telegram Registration

Technician onboarding supports a Telegram-first registration flow so managers do not have to collect Telegram IDs manually.

Recommended flow:

1. Create the technician in the dashboard with status `ONBOARDING`
2. Open the technician detail page and click `Start Telegram Registration`
3. The dashboard returns a registration token and, when `TECHNICIAN_BOT_USERNAME` is configured, a direct bot deep link
4. The technician opens that link in a private chat with the technician bot, which claims the registration token against their `telegram_user_id`
5. The manager creates the work Telegram group and adds:
   - the technician
   - the technician bot
   - the backend notification bot
6. The technician runs `/register` or taps `Complete Registration` inside the work group
7. Backend stores:
   - `telegram_user_id`
   - `telegram_username`
   - `telegram_group_chat_id`
   - `telegram_group_title`

After Telegram registration and `google_calendar_id` are present, the technician can be activated.

Technician form access:

- In the technician's work group, the bot posts a pinned technician panel. Group buttons use short-lived signed links because Telegram does not allow WebApp inline buttons in group/supergroup chats.
- In the technician's private chat with the bot, the bot configures Telegram's persistent menu/Play button to open the technician Mini App at `/technician/forms/app/`.
- The Mini App links to the report, expense, and receipt/contract forms. Private-chat submissions use Telegram WebApp `initData`; group-opened links use signed form tokens.

Environment for this flow:

- `TECHNICIAN_BOT_TOKEN`
- `TECHNICIAN_BOT_USERNAME`
- `TECHNICIAN_API_SHARED_SECRET`

Manager-facing endpoints:

```text
POST /api/technicians/<id>/start-telegram-registration/
GET /api/technicians/<id>/telegram-registration/
```

Internal bot endpoints:

```text
POST /api/technician-bot/claim-registration/
POST /api/technician-bot/complete-registration/
```

Schedule title conventions:

- `cancel`, `canceled`, `cancelled` in title are treated as current cancellation markers
- `reschedule`, `rescheduled` in title are treated as current reschedule markers
- `fake` in title is treated as a fake/test marker
- `didn't buy`, `didnt buy`, `refuse`, and `refused` are context-only notes and should not hide work from technician schedule delivery

## Frontend Setup

The first dashboard UI lives in `frontend/` and uses Vite, React, and TypeScript.

Create a frontend environment file:

```powershell
Copy-Item frontend/.env.example frontend/.env
```

Install dependencies:

```powershell
cd frontend
npm install
```

Run the local frontend:

```powershell
npm run dev
```

Build the frontend:

```powershell
npm run build
```

## GitHub CI

The repository includes a GitHub Actions workflow at [.github/workflows/ci.yml](/C:/HVAC_TECH_CODEX/.github/workflows/ci.yml) that runs on pushes and pull requests to `main`.

It currently checks:

- backend dependency install
- `python manage.py check`
- `python manage.py test`
- frontend dependency install
- `npm run build`

A pull request template is also included at [.github/pull_request_template.md](/C:/HVAC_TECH_CODEX/.github/pull_request_template.md) to keep validation and rollout notes consistent.

## Security Checklist

- Set a strong `DJANGO_SECRET_KEY`
- Set `DEBUG=False`
- Set `ALLOWED_HOSTS`
- Set `CSRF_TRUSTED_ORIGINS`
- Set `CORS_ALLOWED_ORIGINS`
- Set `DATABASE_URL`
- Set `SECURE_SSL_REDIRECT=True`
- Set `SESSION_COOKIE_SECURE=True`
- Set `CSRF_COOKIE_SECURE=True`
- Set `SECURE_HSTS_SECONDS` to a production value such as `31536000`
- Set `SECURE_HSTS_INCLUDE_SUBDOMAINS=True` only if every subdomain is HTTPS-only
- Set `SECURE_HSTS_PRELOAD=True` only if you intend to meet browser preload requirements
- Set `PUBLIC_BASE_URL` to the deployed backend URL
- Set `TELEGRAM_BOT_TOKEN`
- Set `TECHNICIAN_BOT_TOKEN`
- Store Google service account credentials as a secret file and set `GOOGLE_SERVICE_ACCOUNT_JSON_PATH`
- Provision persistent storage for generated PDFs
- Do not store full card numbers or CSC/CVV values in the database, logs, raw submissions, or API responses
- Treat generated contract PDFs that contain card details as sensitive documents with restricted access and retention
- Run `python manage.py check --deploy` before production cutover

Frontend routes:

```text
/login
/dashboard
/technicians
/technicians/:id
/schedule
/finance
```

The login page posts username/password to `/api/auth/login/`, stores `auth_token`, `refresh_token`, and `user_role` in `localStorage`, then redirects to `/dashboard`. The Finance link is hidden when `user_role` is `CALL_CENTER`.

## Demo Data

Seed a demo manager, call center user, accountant, technician, events, reports, expenses, and contract with:

```powershell
python manage.py seed_demo_data
```

Demo credentials:

- `manager` / `password`
- `callcenter` / `password`
- `accountant` / `password`

## Environment Variables

Required for production:

- `DJANGO_SECRET_KEY`
- `DEBUG`
- `ALLOWED_HOSTS`
- `DATABASE_URL`
- `DATABASE_CONNECT_TIMEOUT`
- `TECHNICIAN_API_SHARED_SECRET`
- `TECHNICIAN_BOT_TOKEN`
- `BACKEND_API_BASE_URL`
- `BACKEND_PUBLIC_BASE_URL`
- `PUBLIC_BASE_URL`

Local Docker database variables:

- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_PORT`
- `WEB_PORT`

Planned integration variables:

- `GOOGLE_CALENDAR_CREDENTIALS_JSON`
- `GOOGLE_CALENDAR_ID`
- `TELEGRAM_BOT_TOKEN`

Local frontend integration variables:

- `CORS_ALLOWED_ORIGINS`

## Local Media

Generated development files are stored under:

```text
media/
```

In `DEBUG=True`, Django serves local media at:

```text
/media/
```

Production deployments should use persistent/public media storage. Telegram document delivery needs either a public file URL or a later direct file-upload integration; local `/media/` URLs are only suitable for development.

For local PDF URL testing, set:

```text
PUBLIC_BASE_URL=http://localhost:8000
```

When `PUBLIC_BASE_URL` is configured, generated PDF records store absolute URLs such as:

```text
http://localhost:8000/media/contracts/HVAC-20260501-ABC123.pdf
```

On Render, set `PUBLIC_BASE_URL` to the deployed service URL, for example:

```text
PUBLIC_BASE_URL=https://your-render-service.onrender.com
```

Local media is still not durable production storage. Before relying on generated PDFs long term, add S3, Cloudinary, or a Render persistent disk with a public serving strategy.

## Project Apps

- `accounts`
- `technicians`
- `calendar_sync`
- `reports`
- `expenses`
- `contracts`
- `notifications`
- `audit`

## Current Domain Models

`accounts.UserProfile` extends Django's built-in `auth.User` with platform role, phone, active staff flag, and audit timestamps. A profile is created automatically whenever a new user is created.

`technicians.Technician` stores the technician directory details needed by dispatch, call center, Telegram routing, and future Google Calendar assignment.

`calendar_sync.CalendarEvent` stores the internal source-of-truth record for synced Google Calendar job and block events. It links each event to a technician, preserves the Google calendar/event identifiers, stores scheduling details, and keeps the raw Google payload for future sync diagnostics.

`reports.WorkReport` stores submitted technician job reports. It links reports to technicians and, when available, the matching calendar event. Estimate and cancel reports automatically normalize `amount` to `0.00` so future summaries do not count them as revenue.

`expenses.ExpenseReport` stores technician expense submissions. It links expenses to technicians and optional calendar events, keeps receipt photo URLs when provided, and tracks Telegram delivery status for future notification work.

`contracts.ServiceContract` stores receipt/contract submissions. It links contracts to technicians and optional calendar events, calculates totals, assigns readable contract numbers, and tracks future PDF generation and Telegram delivery status.

## Dashboard API

The dashboard API provides read-focused endpoints for manager, dispatcher, call-center, and accountant web screens.

Endpoints:

```text
GET /api/dashboard/overview/
GET /api/dashboard/technicians/<id>/
GET /api/dashboard/schedule/
GET /api/dashboard/finance-summary/
```

Access rules:

- `OWNER`, `ADMIN`, `MANAGER`, and `DISPATCHER` can access all dashboard endpoints.
- `CALL_CENTER` can access overview, technician detail, and schedule, but money fields, expenses, and contracts are hidden.
- `CALL_CENTER` cannot access finance summary.
- `ACCOUNTANT` can access finance summary only.
- `TECHNICIAN` cannot access dashboard endpoints.

Schedule filters:

```text
GET /api/dashboard/schedule/?technician=1&start_date=2026-05-01&end_date=2026-05-07
```

Finance summary filters:

```text
GET /api/dashboard/finance-summary/?start_date=2026-05-01&end_date=2026-05-31
GET /api/dashboard/finance-summary/?start_date=2026-05-01&end_date=2026-05-31&technician=1
```

When no technician is supplied, finance summary includes totals grouped by technician.

## Technician Onboarding

Managers can add technicians from the React dashboard without touching code or spreadsheets.

Frontend routes:

```text
GET /technicians
GET /technicians/new
GET /technicians/:id
```

Backend endpoints:

```text
POST /api/technicians/
POST /api/technicians/<id>/activate/
```

Onboarding fields:

- Basic info: first name, last name, display name, phone, email, status, service state, timezone
- Telegram integration: user ID, username, group chat ID
- Google Calendar: calendar ID
- Notes

Validation rules:

- `telegram_user_id` must be unique when provided.
- `telegram_group_chat_id` must be unique when provided.
- `google_calendar_id` is required before a technician can be set to `ACTIVE`.
- Activation requires `telegram_user_id`, `telegram_group_chat_id`, and `google_calendar_id`.

The technician detail page shows an onboarding checklist and an Activate button for `OWNER`, `ADMIN`, and `MANAGER`. Call center users can view technicians but do not see create or activate controls.

## Production Checklist

- Set a strong `DJANGO_SECRET_KEY`
- Set `DEBUG=False`
- Set `ALLOWED_HOSTS`
- Set `DATABASE_URL`
- Set `TELEGRAM_BOT_TOKEN`
- Set `TECHNICIAN_BOT_TOKEN`
- Decide on `GOOGLE_SERVICE_ACCOUNT_JSON_PATH` or a Render secret-file strategy
- Set `PUBLIC_BASE_URL`
- Use persistent storage for generated PDFs in `media/`
- Review [render.yaml](C:/HVAC_TECH_CODEX/render.yaml) before deploy and replace placeholder hostnames

## Report Workflow

Technician job report submission is now represented by `ReportSubmissionService`.

Current implemented behavior:

- Validate and save a `WorkReport`.
- Normalize amount to zero for `ESTIMATE` and `CANCEL`.
- Build a readable Telegram-style report message from saved report data.
- Attempt Telegram delivery through `NotificationService` without blocking API creation.
- Call the placeholder Google Calendar description update hook without blocking API creation.

Future behavior:

- Send the formatted report to the technician's Telegram group chat.
- Append report details to the matching Google Calendar event description.
- Calculate daily and weekly summaries from saved reports.

## Technician Submission API

Telegram Bot and future Telegram WebApp submissions use a separate technician-facing API surface. These endpoints identify technicians by `telegram_user_id`, not by internal database id.

All technician submission requests must include:

```text
X-Telegram-WebApp-InitData: <Telegram WebApp initData>
```

In production, submissions must use Telegram WebApp `initData` validation with `TECHNICIAN_BOT_TOKEN`. The backend extracts `user.id` from signed initData and does not trust `telegram_user_id` from the request body when initData is present.

Local development fallback:

- When `DEBUG=True`, requests may use `X-Technician-Api-Secret: <TECHNICIAN_API_SHARED_SECRET>`.
- When `DEBUG=False`, the shared-secret fallback is disabled.
- The Django form templates do not embed `TECHNICIAN_API_SHARED_SECRET`; they send Telegram WebApp initData.

Endpoints:

```text
POST /api/technician/submit-work-report/
POST /api/technician/submit-expense/
POST /api/technician/submit-contract/
```

These endpoints save through the existing submission services, so Telegram notification attempts and Google Calendar report update hooks remain centralized in service code.

## Technician Telegram Bot

The technician bot is a thin client in `telegram_bots/technician_bot`. It does not contain business logic; submissions go through the backend technician API.

Bot environment variables:

- `TECHNICIAN_BOT_TOKEN`
- `BACKEND_API_BASE_URL`
- `BACKEND_PUBLIC_BASE_URL`
- `TECHNICIAN_API_SHARED_SECRET`

Run locally after installing requirements:

```powershell
python -m telegram_bots.technician_bot.main
```

Current bot behavior:

- `/start` shows link buttons for `Submit Report`, `Submit Expense`, `Receipt / Contract`, and `My ID`.
- `My ID` returns Telegram user ID, chat ID, and username.
- Submission buttons open Django technician form pages as Telegram WebApps with `telegram_user_id` and `telegram_group_chat_id` query parameters.

## Calendar Workflow

Google Calendar remains the external scheduling system for now. The backend can import a technician's Google Calendar events into `CalendarEvent` records without deleting events that disappear from Google.

Current implemented behavior:

- Sync one technician calendar with `sync_google_calendar_for_technician`.
- Default sync window is yesterday through 14 days ahead.
- Upsert events by `google_calendar_id + google_event_id`.
- Infer event status from title text such as canceled, rescheduled, or fake.
- Infer basic event type and job number.
- Preserve the raw Google event payload for diagnostics.

Manual sync command:

```powershell
python manage.py sync_technician_calendar --technician-id 1 --days-ahead 14
```

API sync endpoint:

```text
POST /api/calendar/sync-technician/
```

```json
{
  "technician_id": 1,
  "days_ahead": 14
}
```

The React dashboard exposes calendar sync controls on technician detail and schedule screens for `OWNER`, `ADMIN`, `MANAGER`, `DISPATCHER`, and `CALL_CENTER`. Sync results show created, updated, skipped, and any Google credentials/API error returned by the backend. `ACCOUNTANT` and `TECHNICIAN` roles do not get schedule sync controls.

## Schedule Delivery

Technician schedule delivery sends a text summary of active job events to the technician's Telegram group chat.

Manual API endpoint:

```text
POST /api/calendar/send-technician-schedule/
```

```json
{
  "technician_id": 1,
  "date": "2026-05-04"
}
```

Manual command:

```powershell
python manage.py send_technician_schedule --technician-id 1 --date 2026-05-04
```

Batch next-workday command:

```powershell
python manage.py send_next_workday_schedules
```

Next working day rules:

- Saturday sends Monday.
- Sunday sends Monday.
- Any other day sends tomorrow.

Schedule messages include active `JOB` events on the target date, exclude canceled/rescheduled/fake events, skip events before 8:00, and use each event's cleaned technician-facing title. The React technician detail page includes a Send Schedule button for `OWNER`, `ADMIN`, `MANAGER`, `DISPATCHER`, and `CALL_CENTER`.

## Report Summaries

Daily and weekly report summaries are calculated directly from PostgreSQL using saved `WorkReport` and `ExpenseReport` records.

Endpoints:

```text
GET /api/reports/daily-summary/?date=2026-05-02
GET /api/reports/daily-summary/?date=2026-05-02&technician=1
GET /api/reports/weekly-summary/?week_start=2026-04-27
GET /api/reports/weekly-summary/?week_start=2026-04-27&technician=1
```

Access rules:

- `OWNER`, `ADMIN`, `MANAGER`, `DISPATCHER`, and `ACCOUNTANT` can access summary endpoints.
- `CALL_CENTER` and `TECHNICIAN` cannot access summary endpoints.

The React dashboard includes a `/reports` page with daily and weekly filters, optional technician filtering, payment-type breakdowns, review totals, and daily report rows.

## Expense Workflow

Technician expense submission is represented by `ExpenseSubmissionService`.

Current implemented behavior:

- Validate and save an `ExpenseReport`.
- Build a readable Telegram-style expense message from saved expense data.
- Attempt Telegram delivery through `NotificationService` without blocking API creation.

Future behavior:

- Send the formatted expense report to the technician's Telegram group chat.
- Add file upload handling for receipt photos.
- Include expenses in future operational summaries.

## Contract Workflow

Receipt/contract submission is represented by `ContractSubmissionService`.

Current implemented behavior:

- Validate and save a `ServiceContract`.
- Calculate `total` from `subtotal + sales_tax`.
- Generate a readable unique contract number.
- Build a readable Telegram-style contract summary from saved contract data.
- Attempt Telegram summary delivery through `NotificationService` without blocking API creation.
- Generate a PDF receipt/contract from an HTML template.
- Accept full card number and CSC only as write-only, transient submission fields for PDF generation.
- Persist only `credit_card_last4`, expiration date, billing ZIP, and payment processing type.
- Redact full card number and CSC from `raw_submission`, API responses, and Telegram text summaries.
- Store generated PDFs under `media/contracts/`.
- Set `pdf_file_url`, `pdf_generated_at`, and move the contract to `GENERATED` unless it is already `SENT` or `SIGNED`.
- Build absolute PDF URLs from `PUBLIC_BASE_URL` when configured.
- Attempt Telegram PDF delivery without blocking API creation. Relative `/media/` URLs are logged and skipped because Telegram needs a public URL.

Future behavior:

- Use private production-grade media storage with signed URLs or short retention for PDFs containing payment details.
- Send the generated PDF back to the technician's Telegram group chat using a public URL or direct file upload.

## Roles

- `OWNER`: Full business owner access.
- `ADMIN`: Administrative access across operations.
- `MANAGER`: Operational management access.
- `DISPATCHER`: Read access to technician and job coordination data.
- `CALL_CENTER`: Limited web access for technicians and calendar/job events; no financial reports, payroll, expense totals, or technician earnings.
- `ACCOUNTANT`: Finance-oriented staff role; technician directory is read-only.
- `TECHNICIAN`: Field technician role; no access to the technician list endpoint.

Technician API permissions currently allow `OWNER`, `ADMIN`, and `MANAGER` to create, update, and delete technicians. `DISPATCHER`, `CALL_CENTER`, and `ACCOUNTANT` can read technicians only.

Calendar event API permissions currently allow `OWNER`, `ADMIN`, `MANAGER`, `DISPATCHER`, and `CALL_CENTER` to read, create, and update calendar events. `ACCOUNTANT` and `TECHNICIAN` cannot access the admin calendar endpoint.

Work report API permissions currently allow `OWNER`, `ADMIN`, `MANAGER`, and `DISPATCHER` to read, create, update, and delete reports. `CALL_CENTER` and `ACCOUNTANT` can read reports only. `TECHNICIAN` cannot access the admin report endpoint yet.

Expense report API permissions currently allow `OWNER`, `ADMIN`, `MANAGER`, and `DISPATCHER` to read, create, update, and delete expenses. `ACCOUNTANT` can read expenses only. `CALL_CENTER` and `TECHNICIAN` cannot access the admin expense endpoint.

Service contract API permissions currently allow `OWNER`, `ADMIN`, `MANAGER`, and `DISPATCHER` to read, create, update, and delete contracts. `CALL_CENTER` can read, create, and update contracts but cannot delete them. `ACCOUNTANT` can read contracts only. `TECHNICIAN` cannot access the admin contract endpoint.
