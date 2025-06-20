import pytest
from fastapi.testclient import TestClient
from src.main import app
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.db import get_db
from src.repository.contacts import create_contact
from src.schemas.schemas import ContactCreate

client = TestClient(app)


@pytest.fixture(scope="module")
def db_session():
    # Setup database connection (using a test database)
    session = get_db()  # Ensure this points to your test database
    yield session
    # Teardown logic (if needed)


@pytest.fixture
def user_token():
    # Mock the user authentication and return a valid token
    return "Bearer validtoken"  # Replace with actual token generation if necessary


@pytest.fixture
def valid_contact_data():
    return {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "phone_number": "1234567890",
        "birthday": "1990-01-01",  # ISO format for dates
    }


@pytest.mark.asyncio
async def test_create_contact(db_session, user_token, valid_contact_data):
    response = client.post(
        "/contacts/", json=valid_contact_data, headers={"Authorization": user_token}
    )

    assert response.status_code == 201
    assert response.json()["first_name"] == valid_contact_data["first_name"]


@pytest.mark.asyncio
async def test_read_contacts(db_session, user_token):
    response = client.get("/contacts/", headers={"Authorization": user_token})

    assert response.status_code == 200
    assert isinstance(response.json(), list)  # Expect a list of contacts


@pytest.mark.asyncio
async def test_update_contact(db_session, user_token):
    update_data = {"first_name": "Jane"}
    response = client.put(
        "/contacts/1", json=update_data, headers={"Authorization": user_token}
    )

    assert response.status_code == 200
    assert response.json()["first_name"] == "Jane"


@pytest.mark.asyncio
async def test_delete_contact(db_session, user_token):
    response = client.delete("/contacts/1", headers={"Authorization": user_token})

    assert response.status_code == 204
