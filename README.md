# alma-legal-clinic-leads

Lead-intake app for a legal clinic — public resume submission form with email notifications and a secure attorney dashboard. FastAPI + Next.js.

See [docs/design.md](docs/design.md) for the system design and [docs/plan.md](docs/plan.md) for the implementation plan.

## Repository layout

```
apps/
  api/    # FastAPI backend
docs/     # design + implementation plan
```

## Running the API (local dev)

Requires Python 3.11+.

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --port 8000
```

Then check the health endpoint:

```bash
curl -s localhost:8000/health
# {"status":"ok"}
```

> More run instructions (Docker Compose, Postgres, Mailpit, and the web app) will
> be added as later tasks land.
