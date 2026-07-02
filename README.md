# Legal Clinic Leads

A lead-intake application for a legal clinic. Prospects submit their details and a
resume through a **public form**. On submission the system persists the lead, stores
the resume file, and sends **two emails** — a confirmation to the prospect and a
notification to the attorney. Attorneys sign in to a **guarded dashboard** to review
every lead, open its resume, and advance each lead from **`PENDING`** to
**`REACHED_OUT`** once they've made contact.

See [`docs/design.md`](docs/design.md) for the system design and
[`docs/plan.md`](docs/plan.md) for the implementation plan.

## Architecture

The backend follows strict layering with no layer-skipping:

- **Routers** (`apps/api/app/api/routers`) are thin — parse input, validate against a
  schema, call a service, map results/errors to HTTP. No business logic.
- **Services** (`apps/api/app/services`) own all business logic and orchestration
  (lead creation ordering, email dispatch, auth).
- **Repositories** (`apps/api/app/repositories`) are the only layer that touches the
  database.
- **Integrations** (email/SMTP, local file storage) are accessed through interfaces so
  implementations can be swapped without touching business logic.

**Stack:** FastAPI (API) · Next.js (web) · PostgreSQL (storage) · Mailpit (email inbox)
· Docker Compose (orchestration).

The stack runs as four Compose services: `db` (Postgres) and `mailpit` start in
parallel; `api` waits for `db` to be healthy; `web` waits for `api` to be healthy.

## Run the whole stack (one command)

Requires Docker with the Compose plugin.

```bash
docker compose up --build
```

That's it. Postgres migrations and the attorney seed run automatically at API
startup — no manual setup. Add `-d` to run detached in the background.

### Service URLs

| What | URL |
| --- | --- |
| Web app | http://localhost:3000 |
| Public application form | http://localhost:3000/apply |
| Attorney login | http://localhost:3000/login |
| Attorney dashboard | http://localhost:3000/leads |
| API | http://localhost:8000 |
| API docs (Swagger) | http://localhost:8000/docs |
| Mailpit inbox | http://localhost:8025 |

### Attorney login (seeded)

A single attorney user is seeded on startup. Use these credentials to sign in at
http://localhost:3000/login:

- **Email:** `attorney@example.com`
- **Password:** `change-me`

> These are set in `docker-compose.yml` (`SEED_ATTORNEY_EMAIL` /
> `SEED_ATTORNEY_PASSWORD`) and are intended for local review only.

## How to verify (end-to-end walkthrough)

1. **Submit a lead.** Open http://localhost:3000/apply, fill in first name, last name,
   email, and attach a resume (PDF, DOC, or DOCX). Submit — you should see a success
   confirmation.
2. **See both emails.** Open the Mailpit inbox at http://localhost:8025. You should see
   **two** new messages: a confirmation addressed to the prospect and a notification
   addressed to the attorney.
3. **Log in as the attorney.** Go to http://localhost:3000/login and sign in with the
   seeded credentials above.
4. **See the lead.** You land on the dashboard at http://localhost:3000/leads, where the
   lead you just submitted appears with its details and a `Pending` badge.
5. **Open the resume.** Click **Resume** on the lead's row. A PDF opens inline in a new
   tab; a DOC/DOCX downloads with its original filename.
6. **Mark it reached out.** Click **Mark reached out**. The badge flips to
   `Reached out` and persists across reloads (and across `docker compose restart`).

## Running the backend tests

Tests run against a throwaway test Postgres, so bring up `db` first, then run pytest
locally (Python 3.11+):

```bash
docker compose up -d db          # test DB (and the app DB) live here

cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
```

There are no frontend tests.

## Fresh start (from scratch)

To wipe all persisted data (Postgres records and uploaded resumes) and rebuild
everything cleanly:

```bash
docker compose down -v
docker compose up --build
```

`down -v` removes the named volumes; on the next start, migrations and the attorney
seed run again automatically, so you get a clean database and inbox every time.

## Viewing logs and stopping

```bash
docker compose logs -f          # follow logs for all services
docker compose logs -f web      # follow one service (web | api | db | mailpit)

docker compose ps               # show service status / health

docker compose stop             # stop containers, keep data
docker compose down             # stop and remove containers, keep data (volumes)
docker compose down -v          # stop, remove containers AND wipe all data
```

If you started in the foreground, `Ctrl+C` stops the stack.

## Troubleshooting

**Port already in use (3000, 8000, or 8025).** Another process is bound to one of the
mapped ports. Find and stop it, e.g. `lsof -i :3000` (also try `:8000`, `:8025`,
`:5432`, `:1025`), then retry. Alternatively, change the host side of the mapping in
`docker-compose.yml` (e.g. `"3001:3000"`) and use the new port.

**Containers not starting / stuck unhealthy.** Check `docker compose ps` for health and
`docker compose logs <service>` for the cause. `web` will not start until `api` is
healthy, and `api` will not start until `db` is healthy — an early failure upstream
blocks the services below it. Fix the upstream service (often shown in `api` or `db`
logs) and re-run `docker compose up --build`.

**Frontend can't reach the backend (CORS or wrong API URL).** The browser calls the API
directly at `http://localhost:8000`, so:
- The API base URL is baked into the web image at build time
  (`NEXT_PUBLIC_API_BASE_URL` build arg in `docker-compose.yml`). It must be
  `http://localhost:8000` — the compose service name `api` only resolves *inside* the
  Docker network, not from your browser. If you change it, rebuild with
  `docker compose up --build`.
- The API allows the web origin `http://localhost:3000` via CORS
  (`cors_allow_origins` in `apps/api/app/core/config.py`). If you serve the web app on a
  different origin, add it there and rebuild.

**Something's wedged — do a clean rebuild.** Wipe volumes and rebuild images from
scratch:

```bash
docker compose down -v
docker compose up --build
```
