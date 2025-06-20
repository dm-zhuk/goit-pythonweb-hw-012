import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from src.main import app
from src.schemas.schemas import ContactCreate, ContactResponse, BirthdayResponse
from datetime import date

client = TestClient(app)


@pytest.fixture
def user_dict():
    return {
        "id": 1,
        "email": "test@example.com",
        "is_verified": True,
        "avatar_url": None,
        "roles": "user",
    }


@pytest.fixture
def contact_data():
    return ContactCreate(
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        phone_number="1234567890",
        birthday=date(1990, 1, 1),
    )


@pytest.fixture
def contact_response():
    return ContactResponse(
        id=1,
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        phone_number="1234567890",
        birthday=date(1990, 1, 1),
    )


@pytest.mark.asyncio
async def test_create_new_contact_success(user_dict, contact_data, contact_response):
    with patch(
        "src.repository.contacts.create_contact",
        return_value=AsyncMock(id=1, **contact_data.dict()),
    ) as mock_create:
        with patch("src.services.auth.get_current_user", return_value=user_dict):
            response = client.post("/contacts/", json=contact_data.dict())
            assert response.status_code == 201
            assert response.json() == contact_response.dict()
            mock_create.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_new_contact_error(user_dict, contact_data):
    with patch(
        "src.routers.contacts.create_contact", side_effect=Exception("DB error")
    ):
        with patch(
            "src.routers.contacts.auth_service.get_current_user", return_value=user_dict
        ):
            response = client.post("/contacts/", json=contact_data.dict())
            assert response.status_code == 500
            assert response.json()["detail"] == "DB error"


@pytest.mark.asyncio
async def test_read_contacts_success(user_dict):
    contact_list = [
        ContactResponse(
            id=i,
            first_name=f"John{i}",
            last_name="Doe",
            email=f"john{i}@example.com",
            phone_number="1234567890",
            birthday=date(1990, 1, 1),
        )
        for i in range(2)
    ]
    with patch(
        "src.routers.contacts.get_contacts", return_value=contact_list
    ) as mock_get:
        with patch(
            "src.routers.contacts.auth_service.get_current_user", return_value=user_dict
        ):
            response = client.get("/contacts/?skip=0&limit=10")
            assert response.status_code == 200
            assert len(response.json()) == 2
            mock_get.assert_awaited_once_with(AsyncMock(), user_dict, 0, 10)


@pytest.mark.asyncio
async def test_read_contact_success(user_dict, contact_response):
    with patch(
        "src.routers.contacts.get_contact", return_value=contact_response
    ) as mock_get:
        with patch(
            "src.routers.contacts.auth_service.get_current_user", return_value=user_dict
        ):
            response = client.get("/contacts/1")
            assert response.status_code == 200
            assert response.json() == contact_response.dict()
            mock_get.assert_awaited_once_with(AsyncMock(), 1, user_dict)


@pytest.mark.asyncio
async def test_read_contact_not_found(user_dict):
    with patch("src.routers.contacts.get_contact", return_value=None):
        with patch(
            "src.routers.contacts.auth_service.get_current_user", return_value=user_dict
        ):
            response = client.get("/contacts/999")
            assert response.status_code == 404
            assert response.json()["detail"] == "Contact not found"


@pytest.mark.asyncio
async def test_search_contacts_success(user_dict):
    contact_list = [
        ContactResponse(
            id=1,
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            phone_number="1234567890",
            birthday=date(1990, 1, 1),
        )
    ]
    with patch(
        "src.routers.contacts.search_contacts", return_value=contact_list
    ) as mock_search:
        with patch(
            "src.routers.contacts.auth_service.get_current_user", return_value=user_dict
        ):
            with patch("src.routers.contacts.logger.error") as mock_logger:
                response = client.get("/contacts/search/?query=John")
                assert response.status_code == 200
                assert len(response.json()) == 1
                mock_search.assert_awaited_once_with(AsyncMock(), "John", user_dict)
                mock_logger.assert_not_called()


@pytest.mark.asyncio
async def test_search_contacts_error(user_dict):
    with patch(
        "src.routers.contacts.search_contacts", side_effect=Exception("Search error")
    ):
        with patch(
            "src.routers.contacts.auth_service.get_current_user", return_value=user_dict
        ):
            with patch("src.routers.contacts.logger.error") as mock_logger:
                response = client.get("/contacts/search/?query=John")
                assert response.status_code == 500
                assert response.json()["detail"] == "Internal server error"
                mock_logger.assert_called_once_with(
                    "Error searching contacts: Search error"
                )


@pytest.mark.asyncio
async def test_update_existing_contact_success(user_dict, contact_response):
    update_data = {"first_name": "Jane"}
    with patch(
        "src.routers.contacts.update_contact", return_value=contact_response
    ) as mock_update:
        with patch(
            "src.routers.contacts.auth_service.get_current_user", return_value=user_dict
        ):
            response = client.put("/contacts/1", json=update_data)
            assert response.status_code == 200
            assert response.json() == contact_response.dict()
            mock_update.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_existing_contact_not_found(user_dict):
    update_data = {"first_name": "Jane"}
    with patch("src.routers.contacts.update_contact", return_value=None):
        with patch(
            "src.routers.contacts.auth_service.get_current_user", return_value=user_dict
        ):
            response = client.put("/contacts/999", json=update_data)
            assert response.status_code == 404
            assert response.json()["detail"] == "Contact not found"


@pytest.mark.asyncio
async def test_delete_existing_contact_success(user_dict):
    with patch("src.routers.contacts.delete_contact", return_value=True) as mock_delete:
        with patch(
            "src.routers.contacts.auth_service.get_current_user", return_value=user_dict
        ):
            response = client.delete("/contacts/1")
            assert response.status_code == 204
            assert response.text == ""
            mock_delete.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_existing_contact_not_found(user_dict):
    with patch("src.routers.contacts.delete_contact", return_value=None):
        with patch(
            "src.routers.contacts.auth_service.get_current_user", return_value=user_dict
        ):
            response = client.delete("/contacts/999")
            assert response.status_code == 404
            assert response.json()["detail"] == "Contact not found"


@pytest.mark.asyncio
async def test_get_upcoming_birthdays_success(user_dict):
    birthday_response = [
        BirthdayResponse(message="John Doe has a birthday on 1990-01-01")
    ]
    with patch(
        "src.routers.contacts.get_upcoming_birthdays", return_value=birthday_response
    ) as mock_get:
        with patch(
            "src.routers.contacts.auth_service.get_current_user", return_value=user_dict
        ):
            response = client.get("/contacts/birthdays/?days=7")
            assert response.status_code == 200
            assert response.json() == [
                {"message": "John Doe has a birthday on 1990-01-01"}
            ]
            mock_get.assert_awaited_once_with(AsyncMock(), user_dict, 7, None)
