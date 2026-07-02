"""Pytest fixtures for a throwaway test Postgres database.

Tests run against a SEPARATE database (``<dev-db>_test`` by default, or
``TEST_DATABASE_URL`` if set) so the development data is never touched. The
database is created if missing, the schema is (re)built once per session from the
SQLAlchemy models, and each test runs inside a transaction that is rolled back for
isolation.

Requires a reachable Postgres server (``docker compose up -d db``).
"""

import os

import pytest
import sqlalchemy as sa
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Base


def _test_database_url() -> URL:
    override = os.getenv("TEST_DATABASE_URL")
    if override:
        return sa.make_url(override)
    dev_url = sa.make_url(get_settings().database_url)
    return dev_url.set(database=f"{dev_url.database or 'legal'}_test")


def _ensure_database_exists(url: URL) -> None:
    """Create the test database if it does not exist.

    Connects to the maintenance ``postgres`` database with AUTOCOMMIT because
    ``CREATE DATABASE`` cannot run inside a transaction block.
    """
    admin_engine = sa.create_engine(
        url.set(database="postgres"), isolation_level="AUTOCOMMIT"
    )
    try:
        with admin_engine.connect() as conn:
            already_exists = conn.execute(
                sa.text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": url.database},
            ).scalar()
            if not already_exists:
                conn.execute(sa.text(f'CREATE DATABASE "{url.database}"'))
    finally:
        admin_engine.dispose()


@pytest.fixture(scope="session")
def engine():
    url = _test_database_url()
    _ensure_database_exists(url)
    engine = sa.create_engine(url, pool_pre_ping=True)
    # Rebuild the schema from scratch so a crashed prior run cannot leak state.
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture()
def db_session(engine) -> Session:
    """A session wrapped in a transaction that is rolled back after each test.

    The session joins the outer transaction in ``create_savepoint`` mode so that
    code under test which commits (e.g. ``LeadService.create``) only releases a
    SAVEPOINT — the surrounding transaction is still rolled back at teardown,
    keeping every test isolated even when the service layer commits.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
