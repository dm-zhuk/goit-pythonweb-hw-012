import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI
from src.services.auth import auth_service
from src.database.models import Role
from tests.factories import UserFactory
from tests.conftest import TestSettings
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.integration
async def test_role_access_integration(
    test_client: AsyncClient, test_db: AsyncSession, test_settings: TestSettings
):
    user = await UserFactory.create_(
        db=test_db,
        email="admin@example.com",
        hashed_password=auth_service.get_password_hash("password123"),
        is_verified=True,
        roles=Role.admin.value,
    )
    access_token = await auth_service.create_access_token({"sub": user.email})
    headers = {"Authorization": f"Bearer {access_token}"}
    async with AsyncClient(
        transport=ASGITransport(app=test_client.app),
        base_url="http://test",
        headers=headers,
    ) as admin_client:
        response = await admin_client.get("/api/users/me")
        assert response.status_code == 200
        assert response.json()["email"] == "admin@example.com"


@pytest.mark.integration
async def test_role_access_denied_integration(
    test_client: AsyncClient, test_db: AsyncSession, test_settings: TestSettings
):
    user = await UserFactory.create_(
        db=test_db,
        email="user@example.com",
        hashed_password=auth_service.get_password_hash("password123"),
        is_verified=True,
        roles=Role.user.value,
    )
    access_token = await auth_service.create_access_token({"sub": user.email})
    headers = {"Authorization": f"Bearer {access_token}"}
    async with AsyncClient(
        transport=ASGITransport(app=test_client.app),
        base_url="http://test",
        headers=headers,
    ) as user_client:
        response = await user_client.get("/api/users/me")
        assert response.status_code == 200
