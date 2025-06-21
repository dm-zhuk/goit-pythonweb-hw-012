from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException
from starlette import status

from src.database.models import User
from src.services.auth import auth_service
from tests.factories import UserFactory


@pytest.mark.anyio
async def test_get_current_user_wrong_access_token(test_client, test_settings) -> None:
    """Test the get_current_user dependency when access_token is invalid."""
    print("--> test_get_request_user_wrong_access_token")
    token = "783198fgv2bpf9g82gfb928gf19g0"  # Invalid token
    request = Mock()
    db = AsyncMock()

    with pytest.raises(HTTPException) as excinfo:
        await auth_service.get_current_user(
            token=token,
            request=request,
            db=db,
            settings=test_settings,
        )
    assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.anyio
async def test_get_profile(test_client) -> None:
    print("--> test_get_test_get_profilerequest_user_wrong_access_token")
    url = "/api/v1/authentication/profile"
    response = await test_client.get(url)
    assert response.status_code == status.HTTP_200_OK

    response_json = response.json()
    for key in ["id", "email", "first_name", "last_name"]:
        assert key in response_json, f"Key '{key}' not found in response"


@pytest.mark.anyio
async def test_sign_up(test_client) -> None:
    print("--> test_sign_up")

    # Positive case, user is created successfully
    url = "/api/v1/authentication/sign-up"
    response = await test_client.post(
        url,
        json={
            "email": "test_bob@example.com",
            "password": "123456",
            "first_name": "Bob",
            "last_name": "Builder",
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    response_json = response.json()
    assert response_json.get("result") == "User is created successfully."


@pytest.mark.anyio
async def test_sign_up_user_exists_use_factory(unauthenticated_client, test_db) -> None:
    print("--> test_sign_up_user_exists_use_factory")
    email = "test_bob@example.com"

    hashed_password = auth_service.get_password_hash("123456")
    await UserFactory.create_(
        db=test_db, email=email, hashed_password=hashed_password, is_confirmed=True
    )

    url = "/api/v1/authentication/sign-up"
    # Negative case, because user already exists
    response = await unauthenticated_client.post(
        url,
        json={
            "email": email,
            "password": "123456",
            "first_name": "Bob",
            "last_name": "Builder",
        },
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    response_json = response.json()
    assert response_json.get("detail") == "User with such email already exists."


@pytest.mark.anyio
async def test_sign_up_user_exists_use_test_db(unauthenticated_client, test_db) -> None:
    print("--> test_sign_up_user_exists_use_test_db")
    email = "test_bob@example.com"

    user_data = {
        "email": email,
        "hashed_password": auth_service.get_password_hash("123456"),
        "first_name": "Bob",
        "last_name": "Builder",
        "is_confirmed": True,
    }
    db_user = User(**user_data)
    test_db.add(db_user)
    await test_db.commit()
    await test_db.refresh(db_user)

    url = "/api/v1/authentication/sign-up"
    # Negative case, because user already exists
    response = await unauthenticated_client.post(
        url,
        json={
            "email": email,
            "password": "123456",
            "first_name": "Bob",
            "last_name": "Builder",
        },
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    response_json = response.json()
    assert response_json.get("detail") == "User with such email already exists."
