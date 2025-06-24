import pytest
from httpx import AsyncClient
from fastapi import status
from unittest.mock import AsyncMock, patch
from src.main import app


@pytest.mark.asyncio
async def test_healthchecker_success(monkeypatch):
    class DummyResult:
        async def scalar_one_or_none(self):
            return 1

    async def dummy_execute(*args, **kwargs):
        return DummyResult()

    # Patch the AsyncSession execute method to simulate DB returning 1
    with patch("src.routers.utils.AsyncSession.execute", new=dummy_execute):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get("/healthchecker")
    assert response.status_code == status.HTTP_200_OK
    assert "Database configured correctly" in response.json().get("message", "")


@pytest.mark.asyncio
async def test_healthchecker_failure(monkeypatch):
    async def dummy_execute(*args, **kwargs):
        raise Exception("DB down")

    with patch("src.routers.utils.AsyncSession.execute", new=dummy_execute):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get("/healthchecker")
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json()["detail"] == "Error connecting to the database"
