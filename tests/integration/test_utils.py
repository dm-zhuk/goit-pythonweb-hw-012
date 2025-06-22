import pytest
from httpx import AsyncClient
from unittest.mock import patch


@pytest.mark.asyncio
async def test_healthchecker_success(test_client: AsyncClient):
    response = await test_client.get("/healthchecker")
    assert response.status_code == 200
    assert response.json()["message"].startswith("All services healthy")


@pytest.mark.asyncio
async def test_healthchecker_db_failure(test_client: AsyncClient):
    with patch("src.database.db.get_db", side_effect=Exception("DB failure")):
        response = await test_client.get("/healthchecker")
        assert response.status_code == 500
        assert response.json()["detail"] == "Service health check failed"


@pytest.mark.asyncio
async def test_healthchecker_redis_failure(test_client: AsyncClient):
    with patch("src.database.db.rc.ping", side_effect=Exception("Redis failure")):
        response = await test_client.get("/healthchecker")
        assert response.status_code == 500
        assert response.json()["detail"] == "Service health check failed"
