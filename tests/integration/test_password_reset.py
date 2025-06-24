# tests/integration/test_password_reset.py

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.services.auth import auth_service
from src.repository.users import create_user
from src.schemas.schemas import UserCreate

TEST_EMAIL = "reset_test@example.com"
TEST_PASSWORD = "initial_password"
NEW_PASSWORD = "new_secure_password"


@pytest.mark.integration
async def test_password_reset_flow(db_session: AsyncSession, redis_client):
    # Create test user
    user_data = UserCreate(email=TEST_EMAIL, password=TEST_PASSWORD)
    await create_user(user_data, db_session)

    # Request reset: should store token in Redis
    await auth_service.request_password_reset(TEST_EMAIL, db_session)

    # Find the reset token from Redis keys
    keys = await redis_client.keys("reset_token:*")
    assert keys, "No reset token found in Redis"
    token_key = keys[0]
    token = token_key.split("reset_token:")[1]

    # Simulate resetting password
    await auth_service.reset_password(token, NEW_PASSWORD, db_session)

    # Redis token should be deleted
    value = await redis_client.get(token_key)
    assert value is None, "Token should be deleted from Redis after reset"

    # Check new password works
    updated_user = await auth_service.get_current_user(
        token=await auth_service.create_access_token({"sub": TEST_EMAIL}), db=db_session
    )
    assert auth_service.verify_password(NEW_PASSWORD, updated_user.hashed_password)
