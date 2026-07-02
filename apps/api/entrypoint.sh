#!/bin/sh
# Container startup: apply migrations, seed the attorney (idempotent), then serve.
# Runs at startup (not image build) because the database is only reachable now.
set -e

echo "==> Applying database migrations (alembic upgrade head)"
alembic upgrade head

echo "==> Seeding attorney user (idempotent)"
python -m app.db.seed

echo "==> Starting API (uvicorn)"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
