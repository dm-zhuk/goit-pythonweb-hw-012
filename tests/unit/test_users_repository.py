import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select
from fastapi import HTTPException

from src.database.models import User, Role
from src.repository.users import create_user, get_user_by_email, confirm_email
from src.schemas.schemas import UserCreate, UserResponse


@pytest.fixture
def mock_session():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def user_data():
    return UserCreate(email="test@example.com", password="password123")


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
async def test_create_user_success(mock_session, user_data):
    with patch(
        "src.repository.users.get_user_by_email", return_value=None
    ) as mock_get_user:
        with patch(
            "src.repository.users.auth_service.get_password_hash",
            return_value="hashed_password",
        ):
            with patch("src.repository.users.Gravatar") as mock_gravatar:
                mock_gravatar_instance = MagicMock()
                mock_gravatar_instance.get_image.return_value = "http://avatar.url"
                mock_gravatar.return_value = mock_gravatar_instance

                # Call method
                result = await create_user(body=user_data, db=mock_session)

                # Assertions
                assert isinstance(result, User)
                assert result.email == user_data.email
                assert result.hashed_password == "hashed_password"
                assert result.avatar_url == "http://avatar.url"
                assert result.roles == Role.user
                mock_session.add.assert_awaited_once()
                mock_session.commit.assert_awaited_once()
                mock_session.refresh.assert_awaited_once_with(result)
                mock_get_user.assert_awaited_once_with(user_data.email, mock_session)


@pytest.mark.asyncio
async def test_create_user_email_exists(mock_session, user_data, mock_user):
    # Setup mocks
    with patch("src.repository.users.get_user_by_email", return_value=mock_user):
        # Call method and assert exception
        with pytest.raises(HTTPException) as exc_info:
            await create_user(body=user_data, db=mock_session)
        assert exc_info.value.status_code == 409
        assert exc_info.value.detail == "Email already registered"
        mock_session.add.assert_not_awaited()
        mock_session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_user_gravatar_failure(mock_session, user_data):
    # Setup mocks
    with patch("src.repository.users.get_user_by_email", return_value=None):
        with patch(
            "src.repository.users.auth_service.get_password_hash",
            return_value="hashed_password",
        ):
            with patch(
                "src.repository.users.Gravatar", side_effect=Exception("Gravatar error")
            ):
                # Call method
                result = await create_user(body=user_data, db=mock_session)

                # Assertions
                assert isinstance(result, User)
                assert result.email == user_data.email
                assert result.avatar_url is None
                assert result.roles == Role.user
                mock_session.add.assert_awaited_once()
                mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response, expected_type",
    [
        (False, User),
        (True, UserResponse),
    ],
)
async def test_get_user_by_email_success(
    mock_session, mock_user, response, expected_type
):
    # Setup mock
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = mock_user
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Call method
    result = await get_user_by_email(
        email="test@example.com", db=mock_session, response=response
    )

    # Assertions
    assert isinstance(result, expected_type)
    assert result.email == "test@example.com"
    assert result.is_verified == mock_user.is_verified
    assert result.avatar_url == mock_user.avatar_url
    assert result.roles == Role.user
    mock_session.execute.assert_awaited_once()
    called_args = mock_session.execute.call_args[0][0]
    assert isinstance(called_args, Select)


@pytest.mark.asyncio
async def test_get_user_by_email_not_found(mock_session):
    # Setup mock
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Call method
    result = await get_user_by_email(email="notfound@example.com", db=mock_session)

    # Assertions
    assert result is None
    mock_session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_confirm_email_success(mock_session, mock_user):
    # Setup mocks
    with patch("src.repository.users.get_user_by_email", return_value=mock_user):
        # Call method
        await confirm_email(email="test@example.com", db=mock_session)

        # Assertions
        assert mock_user.is_verified is True
        mock_session.add.assert_awaited_once_with(mock_user)
        mock_session.commit.assert_awaited_once()
        mock_session.refresh.assert_awaited_once_with(mock_user)


@pytest.mark.asyncio
async def test_confirm_email_already_verified(mock_session, mock_user):
    # Setup mocks
    mock_user.is_verified = True
    with patch("src.repository.users.get_user_by_email", return_value=mock_user):
        # Call method
        await confirm_email(email="test@example.com", db=mock_session)

        # Assertions
        mock_session.add.assert_not_awaited()
        mock_session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_confirm_email_not_found(mock_session):
    # Setup mocks
    with patch("src.repository.users.get_user_by_email", return_value=None):
        # Call method and assert exception
        with pytest.raises(HTTPException) as exc_info:
            await confirm_email(email="notfound@example.com", db=mock_session)
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "User not found"


@pytest.mark.asyncio
async def test_confirm_email_database_error(mock_session, mock_user):
    # Setup mocks
    with patch("src.repository.users.get_user_by_email", return_value=mock_user):
        mock_session.commit = AsyncMock(side_effect=Exception("Database error"))
        # Call method and assert exception
        with pytest.raises(HTTPException) as exc_info:
            await confirm_email(email="test@example.com", db=mock_session)
        assert exc_info.value.status_code == 500
        assert "Failed to verify email" in exc_info.value.detail
        mock_session.rollback.assert_awaited_once()
