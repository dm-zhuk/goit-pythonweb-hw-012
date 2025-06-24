import pytest
from fastapi import HTTPException
from unittest.mock import AsyncMock, patch

from src.repository import users
from src.database.models import User
from src.schemas.schemas import UserCreate


@pytest.mark.asyncio
async def test_create_user_success(mocker):
    mock_db = AsyncMock()
    # Simulate no existing user
    mocker.patch("src.repository.users.get_user_by_email", return_value=None)
    # Mock password hash function
    mocker.patch.object(
        users.auth_service, "get_password_hash", return_value="hashed_pw"
    )
    # Mock Gravatar to avoid network call
    mocker.patch("src.repository.users.Gravatar.get_image", return_value="avatar_url")

    user_create = UserCreate(email="test@example.com", password="secret")

    # The add/commit/refresh methods on the session
    mock_db.add = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    new_user = await users.create_user(user_create, db=mock_db)

    assert isinstance(new_user, User)
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_create_user_duplicate_email(mocker):
    mock_db = AsyncMock()
    existing_user = User(email="test@example.com")
    mocker.patch("src.repository.users.get_user_by_email", return_value=existing_user)

    user_create = UserCreate(email="test@example.com", password="secret")

    with pytest.raises(HTTPException) as exc:
        await users.create_user(user_create, db=mock_db)
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_get_user_by_email_return_response(mocker):
    mock_db = AsyncMock()
    fake_user = User(id=1, email="a@b.com", is_verified=True, avatar_url="url")
    mock_result = AsyncMock()
    mock_result.scalars.return_value.first.return_value = fake_user
    mock_db.execute = AsyncMock(return_value=mock_result)

    user = await users.get_user_by_email("a@b.com", db=mock_db, response=True)

    assert user.email == "a@b.com"
    assert hasattr(user, "model_config")


@pytest.mark.asyncio
async def test_get_user_by_email_return_orm(mocker):
    mock_db = AsyncMock()
    fake_user = User(id=1, email="a@b.com", is_verified=True)
    mock_result = AsyncMock()
    mock_result.scalars.return_value.first.return_value = fake_user
    mock_db.execute = AsyncMock(return_value=mock_result)

    user = await users.get_user_by_email("a@b.com", db=mock_db, response=False)

    assert isinstance(user, User)


@pytest.mark.asyncio
async def test_get_user_by_email_none(mocker):
    mock_db = AsyncMock()
    mock_result = AsyncMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)

    user = await users.get_user_by_email("missing@user.com", db=mock_db)

    assert user is None


@pytest.mark.asyncio
async def test_confirm_email_success(mocker):
    mock_db = AsyncMock()
    fake_user = User(email="test@example.com", is_verified=False)
    mocker.patch("src.repository.users.get_user_by_email", return_value=fake_user)

    mock_db.add = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    await users.confirm_email("test@example.com", db=mock_db)

    assert fake_user.is_verified is True
    mock_db.add.assert_called_once_with(fake_user)
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_confirm_email_already_verified(mocker):
    fake_user = User(email="test@example.com", is_verified=True)
    mocker.patch("src.repository.users.get_user_by_email", return_value=fake_user)

    # No db calls should happen
    mock_db = AsyncMock()

    await users.confirm_email("test@example.com", db=mock_db)

    assert fake_user.is_verified is True
    mock_db.add.assert_not_called()
    mock_db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_confirm_email_user_not_found(mocker):
    mocker.patch("src.repository.users.get_user_by_email", return_value=None)

    mock_db = AsyncMock()

    with pytest.raises(HTTPException) as exc:
        await users.confirm_email("missing@example.com", db=mock_db)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_confirm_email_commit_fail(mocker):
    mock_db = AsyncMock()
    fake_user = User(email="fail@example.com", is_verified=False)
    mocker.patch("src.repository.users.get_user_by_email", return_value=fake_user)

    mock_db.add = AsyncMock()
    mock_db.commit = AsyncMock(side_effect=Exception("DB commit failed"))
    mock_db.refresh = AsyncMock()
    mock_db.rollback = AsyncMock()

    with pytest.raises(HTTPException) as exc:
        await users.confirm_email("fail@example.com", db=mock_db)
    assert exc.value.status_code == 500
    mock_db.rollback.assert_called_once()
