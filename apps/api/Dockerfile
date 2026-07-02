FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install dependencies first so this layer caches across code changes.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Application code, Alembic config/migrations, and the startup entrypoint.
COPY app ./app
COPY alembic.ini ./alembic.ini
COPY entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh

EXPOSE 8000

# Migrations + seed run at container start (not build): the DB is only
# reachable at runtime. See entrypoint.sh.
ENTRYPOINT ["./entrypoint.sh"]
