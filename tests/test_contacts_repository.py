import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select
from fastapi import HTTPException
from datetime import date

from src.database.models import Contact, User, Role
from src.repository.contacts import (
    create_contact,
    get_contacts,
    get_contact,
    update_contact,
    delete_contact,
    search_contacts,
    get_upcoming_birthdays,
)
from src.schemas.schemas import ContactCreate, ContactUpdate


@pytest.fixture
def mock_session():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def user():
    return User(id=1, email="test@example.com", roles=Role.user)


@pytest.fixture
def contact_data():
    return ContactCreate(
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        phone_number="1234567890",
        birthday=date(2000, 1, 1),
    )


@pytest.fixture
def mock_contact(user):
    return Contact(
        id=1,
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        phone_number="1234567890",
        birthday=date(2000, 1, 1),
        user_id=user.id,
    )


@pytest.mark.asyncio
async def test_create_contact_success(mock_session, contact_data, user):
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = Contact(
        id=1, **contact_data.model_dump(), user_id=user.id
    )
    mock_session.execute = AsyncMock(return_value=mock_result)

    result = await create_contact(db=mock_session, contact=contact_data, user=user)

    assert isinstance(result, Contact)
    assert result.first_name == contact_data.first_name
    assert result.email == contact_data.email
    assert result.user_id == user.id
    mock_session.add.assert_awaited_once()
    mock_session.commit.assert_awaited_once()
    mock_session.refresh.assert_awaited_once_with(result)


@pytest.mark.asyncio
async def test_get_contacts_success(mock_session, user, mock_contact):
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_contact]
    mock_session.execute = AsyncMock(return_value=mock_result)

    result = await get_contacts(db=mock_session, user=user, skip=0, limit=10)

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].first_name == "John"
    mock_session.execute.assert_awaited_once()
    called_args = mock_session.execute.call_args[0][0]
    assert isinstance(called_args, Select)


@pytest.mark.asyncio
async def test_get_contact_success(mock_session, user, mock_contact):
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = mock_contact
    mock_session.execute = AsyncMock(return_value=mock_result)

    result = await get_contact(db=mock_session, contact_id=1, user=user)

    assert isinstance(result, Contact)
    assert result.id == 1
    assert result.first_name == "John"
    mock_session.execute.assert_awaited_once()
    called_args = mock_session.execute.call_args[0][0]
    assert isinstance(called_args, Select)


@pytest.mark.asyncio
async def test_get_contact_not_found(mock_session, user):
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)

    result = await get_contact(db=mock_session, contact_id=999, user=user)

    assert result is None
    mock_session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_contact_success(mock_session, user, mock_contact):
    update_data = ContactUpdate(first_name="Jane", email="jane.doe@example.com")
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = mock_contact
    mock_session.execute = AsyncMock(return_value=mock_result)

    result = await update_contact(
        db=mock_session, contact_id=1, contact=update_data, user=user
    )

    assert isinstance(result, Contact)
    assert result.first_name == "Jane"
    assert result.email == "jane.doe@example.com"
    mock_session.commit.assert_awaited_once()
    mock_session.refresh.assert_awaited_once_with(mock_contact)


@pytest.mark.asyncio
async def test_update_contact_not_found(mock_session, user):
    update_data = ContactUpdate(first_name="Jane")
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)

    result = await update_contact(
        db=mock_session, contact_id=999, contact=update_data, user=user
    )

    assert result is None
    mock_session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_contact_success(mock_session, user, mock_contact):
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = mock_contact
    mock_session.execute = AsyncMock(return_value=mock_result)

    result = await delete_contact(db=mock_session, contact_id=1, user=user)

    assert isinstance(result, Contact)
    assert result.id == 1
    mock_session.delete.assert_awaited_once_with(mock_contact)
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_contact_not_found(mock_session, user):
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)

    result = await delete_contact(db=mock_session, contact_id=999, user=user)

    assert result is None
    mock_session.delete.assert_not_awaited()
    mock_session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_search_contacts_success(mock_session, user, mock_contact):
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_contact]
    mock_session.execute = AsyncMock(return_value=mock_result)

    result = await search_contacts(db=mock_session, query="John", user=user)

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].first_name == "John"
    mock_session.execute.assert_awaited_once()
    called_args = mock_session.execute.call_args[0][0]
    assert isinstance(called_args, Select)


@pytest.mark.asyncio
async def test_get_upcoming_birthdays_success(mock_session, user):
    start_date = date(2025, 6, 20)
    mock_contact = {
        "id": 1,
        "first_name": "John",
        "last_name": "Doe",
        "birthday_formatted": "JUN-21",
    }
    mock_result = MagicMock()
    mock_result.all.return_value = [mock_contact]
    mock_session.execute = AsyncMock(return_value=mock_result)

    with patch("src.repository.contacts.date") as mock_date:
        mock_date.today.return_value = start_date
        mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)

        result = await get_upcoming_birthdays(db=mock_session, user=user, days=7)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["message"] == "John Doe - birthday on JUN-21 (ID: 1)"
        mock_session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_upcoming_birthdays_invalid_days(mock_session, user):
    with pytest.raises(HTTPException) as exc_info:
        await get_upcoming_birthdays(db=mock_session, user=user, days=0)
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Days must be positive"
    mock_session.execute.assert_not_awaited()
