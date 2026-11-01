import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Test env before app imports settings cache
os.environ["APP_ENV"] = "test"
os.environ["JWT_SECRET"] = "m1-test-jwt-secret-not-for-production"
os.environ["DEMO_USERNAME"] = "demo@health.local"
os.environ["DEMO_PASSWORD"] = "demo-password-change-me"
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_type, compiler, **_kw):  # type: ignore[no-untyped-def]
    return "JSON"


from app.core.config import get_settings  # noqa: E402
from app.core.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.organization import Organization, OrganizationType  # noqa: E402

get_settings.cache_clear()


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as conn:
        conn.execute(text("PRAGMA foreign_keys=ON"))

    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    # Seed demo hospitals (mirrors migration seed)
    session.add_all(
        [
            Organization(
                id=uuid.uuid4(),
                name="Demo Hospital A",
                org_type=OrganizationType.hospital,
            ),
            Organization(
                id=uuid.uuid4(),
                name="Demo Hospital B",
                org_type=OrganizationType.hospital,
            ),
        ]
    )
    session.commit()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def client(db_session):
    def _override_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def auth_header(client: TestClient) -> dict[str, str]:
    r = client.post(
        "/api/v1/auth/session",
        json={"username": "demo@health.local", "password": "demo-password-change-me"},
    )
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
