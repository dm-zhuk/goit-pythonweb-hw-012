import pytest
from pydantic import ValidationError
from datetime import date
from src.schemas import schemas
from src.database.models import Role


def test_contact_create_valid():
    data = {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com",
        "phone_number": "+1234567890",
        "birthday": date(1990, 1, 1),
        "additional_data": "Some data",
    }
    contact = schemas.ContactCreate(**data)
    assert contact.first_name == "John"
    assert contact.additional_data == "Some data"


def test_contact_update_partial():
    data = {"email": "jane@example.com"}
    contact = schemas.ContactUpdate(**data)
    assert contact.email == "jane@example.com"
    assert contact.first_name is None


def test_contact_update_invalid_email():
    data = {"email": "invalid-email"}
    with pytest.raises(ValidationError):
        schemas.ContactUpdate(**data)


def test_user_create_valid():
    data = {
        "email": "user@example.com",
        "password": "securepassword123",
        "avatar": None,
    }
    user = schemas.UserCreate(**data)
    assert user.email == "user@example.com"


def test_user_response_model_config():
    class DummyUser:
        id = 1
        email = "user@example.com"
        is_verified = True
        avatar_url = "http://avatar.url/image.png"
        roles = Role.admin

    user_response = schemas.UserResponse.from_orm(DummyUser())
    assert user_response.id == 1
    assert user_response.roles == Role.admin


def test_password_reset_confirm_valid():
    data = {"token": "sometoken", "new_password": "newStrongPass1!"}
    reset_confirm = schemas.PasswordResetConfirm(**data)
    assert reset_confirm.token == "sometoken"
    assert reset_confirm.new_password == "newStrongPass1!"


def test_password_reset_confirm_missing_fields():
    with pytest.raises(ValidationError):
        schemas.PasswordResetConfirm(token="token-only")

    with pytest.raises(ValidationError):
        schemas.PasswordResetConfirm(new_password="password-only")
