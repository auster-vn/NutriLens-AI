from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from app.core.database import get_session
from app.core.models import Base, ProductCache
from app.main import app
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture
async def isolated_app(
    tmp_path: Path,
) -> AsyncIterator[tuple[AsyncClient, async_sessionmaker[AsyncSession]]]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async def override_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client, session_factory
    app.dependency_overrides.clear()
    await engine.dispose()


async def _register(client: AsyncClient, email: str, name: str = "Test User") -> dict:
    response = await client.post(
        "/api/auth/register",
        json={"email": email, "display_name": name, "password": "strong-password"},
    )
    assert response.status_code == 201
    return response.json()["user"]


@pytest.mark.asyncio
async def test_root_health_endpoint_is_available_for_platform_health_checks(isolated_app):
    client, _ = isolated_app

    response = await client.get("/")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_registration_creates_cookie_session_and_profile(isolated_app):
    client, _ = isolated_app
    user = await _register(client, "first@example.com")

    assert (await client.get("/api/auth/me")).json()["id"] == user["id"]
    assert (await client.get("/api/profile")).json()["goal"] == "general"
    assert (await client.get("/api/admin/session")).status_code == 403
    assert (await client.get("/api/admin/session", headers={"X-Admin-Key": "dev-admin-key"})).status_code == 200

    logout = await client.post("/api/auth/logout")
    assert logout.status_code == 204
    assert (await client.get("/api/profile")).status_code == 401


@pytest.mark.asyncio
async def test_personal_data_is_isolated_and_dashboard_aggregates(isolated_app):
    first_client, session_factory = isolated_app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as second_client:
        await _register(first_client, "one@example.com", "User One")
        await _register(second_client, "two@example.com", "User Two")

        async with session_factory() as session:
            session.add(
                ProductCache(
                    barcode="12345678",
                    name="Portfolio Oats",
                    nutriments={"sugars_100g": 2, "proteins_100g": 12},
                )
            )
            await session.commit()

        add_response = await first_client.post(
            "/api/pantry",
            json={"barcode": "12345678", "quantity": 1, "unit": "pack", "storage_location": "pantry"},
        )
        assert add_response.status_code == 200
        assert len((await first_client.get("/api/pantry")).json()) == 1
        assert (await second_client.get("/api/pantry")).json() == []

        dashboard = await first_client.get("/api/dashboard")
        assert dashboard.status_code == 200
        metrics = {row["label"]: row["value"] for row in dashboard.json()["metrics"]}
        assert metrics["Pantry items"] == 1
