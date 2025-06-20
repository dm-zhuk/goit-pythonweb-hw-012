import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
import json

from src.database.db import (
    get_user_from_db,
    get_user_from_cache,
    init_db,
    get_db,
    rc,
)
from src.database.models import User, Role


@pytest.fixture
def mock_session():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_user():
    return User(
        id=1,
        email="test@example.com",
        hashed_password="hashed_password",
        is_verified=False,
        avatar_url=None,
        roles=Role.user,
    )


@pytest.mark.asyncio
async def test_get_user_from_db_success(mock_session, mock_user):
    with patch(
        "src.database.connect.get_user_by_email", return_value=mock_user
    ) as mock_get_user:
        result = await get_user_from_db(email="test@example.com", db=mock_session)

        assert isinstance(result, dict)
        assert result["email"] == "test@example.com"
        assert result["roles"] == Role.user.value
        mock_get_user.assert_awaited_once_with("test@example.com", mock_session)


@pytest.mark.asyncio
async def test_get_user_from_db_not_found(mock_session):
    with patch("src.database.connect.get_user_by_email", return_value=None):
        with pytest.raises(HTTPException) as exc_info:
            await get_user_from_db(email="notfound@example.com", db=mock_session)
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "User not found"


@pytest.mark.asyncio
async def test_get_user_from_cache_hit(mock_session, mock_user):
    cache_key = "get_user_from_cache:test@example.com"
    user_dict = mock_user.to_dict()
    cached_data = json.dumps(user_dict)

    with patch.object(rc, "get", return_value=cached_data) as mock_redis_get:
        with patch("src.database.connect.get_user_by_email") as mock_get_user:
            result = await get_user_from_cache(
                email="test@example.com", db=mock_session
            )

            assert result == user_dict
            mock_redis_get.assert_awaited_once_with(cache_key)
            mock_get_user.assert_not_called()


@pytest.mark.asyncio
async def test_get_user_from_cache_miss(mock_session, mock_user):
    cache_key = "get_user_from_cache:test@example.com"
    user_dict = mock_user.to_dict()

    with patch.object(rc, "get", return_value=None) as mock_redis_get:
        with patch.object(rc, "setex") as mock_redis_setex:
            with patch(
                "src.database.connect.get_user_by_email", return_value=mock_user
            ):
                result = await get_user_from_cache(
                    email="test@example.com", db=mock_session
                )

                assert result == user_dict
                mock_redis_get.assert_awaited_once_with(cache_key)
                mock_redis_setex.assert_awaited_once_with(
                    cache_key, 3600, json.dumps(user_dict)
                )


@pytest.mark.asyncio
async def test_get_user_from_cache_invalid_json(mock_session, mock_user):
    cache_key = "get_user_from_cache:test@example.com"
    user_dict = mock_user.to_dict()

    with patch.object(rc, "get", return_value="invalid_json") as mock_redis_get:
        with patch.object(rc, "setex") as mock_redis_setex:
            with patch(
                "src.database.connect.get_user_by_email", return_value=mock_user
            ):
                with patch("src.database.connect.logger.warning") as mock_logger:
                    result = await get_user_from_cache(
                        email="test@example.com", db=mock_session
                    )

                    assert result == user_dict
                    mock_redis_get.assert_awaited_once_with(cache_key)
                    mock_logger.assert_called_once_with(
                        f"Invalid cached data for key {cache_key}"
                    )
                    mock_redis_setex.assert_awaited_once_with(
                        cache_key, 3600, json.dumps(user_dict)
                    )


@pytest.mark.asyncio
async def test_get_user_from_cache_redis_error(mock_session, mock_user):
    cache_key = "get_user_from_cache:test@example.com"
    user_dict = mock_user.to_dict()

    with patch.object(rc, "get", return_value=None):
        with patch.object(
            rc, "setex", side_effect=Exception("Redis error")
        ) as mock_redis_setex:
            with patch(
                "src.database.connect.get_user_by_email", return_value=mock_user
            ):
                with patch("src.database.connect.logger.error") as mock_logger:
                    result = await get_user_from_cache(
                        email="test@example.com", db=mock_session
                    )

                    assert result == user_dict
                    mock_redis_setex.assert_awaited_once_with(
                        cache_key, 3600, json.dumps(user_dict)
                    )
                    mock_logger.assert_called_once_with(
                        f"Failed to cache user test@example.com: Redis error"
                    )


@pytest.mark.asyncio
async def test_init_db():
    mock_conn = AsyncMock()
    mock_engine = MagicMock()
    mock_engine.begin().__enter__.return_value = mock_conn

    with patch("src.database.connect.engine", mock_engine):
        with patch("src.database.connect.Base.metadata.create_all") as mock_create_all:
            await init_db()

            mock_create_all.assert_called()
            mock_conn.run_sync.assert_awaited_with(mock_create_all)


@pytest.mark.asyncio
async def test_get_db_success():
    with patch(
        "src.database.connect.async_session", return_value=mock_session
    ) as mock_session_maker:
        async with get_db() as db:
            assert isinstance(db, AsyncSession)
            assert db == mock_session
        mock_session_maker.assert_called_once()
        mock_session.close.assert_await()


@pytest.mark.asyncio
async def test_get_db_error(mock_session):
    with patch("src.database.connect.async_session", return_value=mock_session):
        with patch("src.database.connect.logger.error") as mock_logger:
            try:
                async with get_db():
                    raise Exception("Test error")
            except Exception as e:
                assert str(e) == "Test error"
                mock_logger.assert_called_once_with("Database error: Test error")
                mock_session.rollback.assert_awaited_once()
                mock_session.close.assert_awaited_once()
