import pytest
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.database.models import User
from src.repository.users import create_user, get_user_by_email, confirm_email
from src.schemas.schemas import UserCreate
from src.services.auth import auth_service


@pytest.mark.asyncio
async def test_create_user_and_get_user_by_email(async_session: AsyncSession):
    # Arrange: create a user DTO
    user_data = UserCreate(email="testuser@example.com", password="securepassword")

    # Act: create user in db
    created_user = await create_user(user_data, async_session)

    # Assert: user returned has expected fields and password hashed
    assert created_user.email == user_data.email
    assert created_user.hashed_password != user_data.password
    assert auth_service.verify_password(
        user_data.password, created_user.hashed_password
    )

    # Act: get user by email (ORM)
    fetched_user = await get_user_by_email(user_data.email, async_session)
    assert fetched_user is not None
    assert fetched_user.email == user_data.email

    # Act: get user by email (response DTO)
    fetched_user_resp = await get_user_by_email(
        user_data.email, async_session, response=True
    )
    assert fetched_user_resp.email == user_data.email
    assert hasattr(fetched_user_resp, "is_verified")
    assert hasattr(fetched_user_resp, "avatar_url")


@pytest.mark.asyncio
async def test_confirm_email_changes_user_verification_status(
    async_session: AsyncSession,
):
    # Arrange: create user with unverified email
    user_data = UserCreate(email="verifyme@example.com", password="test1234")
    user = await create_user(user_data, async_session)

    # Initially user is not verified
    assert not user.is_verified

    # Act: confirm email
    await confirm_email(user.email, async_session)

    # Reload user from DB
    refreshed_user = await get_user_by_email(user.email, async_session)
    assert refreshed_user.is_verified is True

    # Act & Assert: confirm_email again does not fail for already verified email
    await confirm_email(user.email, async_session)


@pytest.mark.asyncio
async def test_minimal_base_and_idormmodel_classes():
    # Just a simple sanity check for the base classes
    from src.database import metadata

    # Subclass MinimalBase and IDOrmModel
    class DummyModel(metadata.MinimalBase):
        __tablename__ = "dummy"
        id = 1

    class DummyID(metadata.IDOrmModel):
        __tablename__ = "dummy_id"
        pass

    dummy = DummyModel()
    dummy_id = DummyID()

    assert dummy.metadata is metadata.metadata_
    assert hasattr(dummy_id, "id")
