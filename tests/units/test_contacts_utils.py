import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from src.main import app
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import text

client = TestClient(app)


@pytest.mark.asyncio
async def test_healthchecker_success():
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none.return_value = 1
    with patch(
        "src.routers.utils.db.execute", return_value=mock_result
    ) as mock_execute:
        response = client.get("/healthchecker")
        assert response.status_code == 200
        assert (
            response.json()["message"]
            == "Database configured correctly. Welcome to the Contacts FAST API v2.0!"
        )
        mock_execute.assert_awaited_once_with(text("SELECT 1"))


@pytest.mark.asyncio
async def test_healthchecker_db_unreachable():
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none.return_value = None
    with patch("src.routers.utils.db.execute", return_value=mock_result):
        response = client.get("/healthchecker")
        assert response.status_code == 500
        assert response.json()["detail"] == "Database is not reachable"


@pytest.mark.asyncio
async def test_healthchecker_db_error():
    with patch("src.routers.utils.db.execute", side_effect=SQLAlchemyError("DB error")):
        response = client.get("/healthchecker")
        assert response.status_code == 500
        assert response.json()["detail"] == "Error connecting to the database"
