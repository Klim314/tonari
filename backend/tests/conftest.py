import os
from collections.abc import Generator

# Force in-memory SQLite for all tests — never run against the real database.
# Using os.environ directly (not setdefault) so this cannot be overridden by
# the container's DATABASE_URL env var, which would cause drop_all to wipe
# live Postgres data.
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"

import pytest
from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, engine
from app.main import app


@pytest.fixture(scope="session")
def client() -> Generator[TestClient, None, None]:
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clean_db() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    with SessionLocal() as session:
        yield session
