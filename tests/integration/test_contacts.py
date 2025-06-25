import pytest
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException

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


@pytest.mark.asyncio
@patch("src.database.db.AsyncSession")
async def test_create_contact(mock_async_session):
    # Arrange
    mock_db = AsyncMock()
    mock_async_session.return_value.__aenter__.return_value = mock_db
    contact_data = ContactCreate(
        first_name="John", last_name="Doe", email="john@example.com"
    )
    user = AsyncMock(id=1)

    # Act
    contact = await create_contact(mock_db, contact_data, user)

    # Assert
    assert contact.first_name == "John"
    assert contact.last_name == "Doe"
    mock_db.add.assert_awaited_once()
    mock_db.commit.assert_awaited_once()
    mock_db.refresh.assert_awaited_once(contact)


@pytest.mark.asyncio
@patch("src.database.db.AsyncSession")
async def test_get_contacts(mock_async_session):
    # Arrange
    mock_db = AsyncMock()
    mock_async_session.return_value.__aenter__.return_value = mock_db
    user = AsyncMock(id=1)
    mock_db.execute.return_value.scalars.return_value.all.return_value = [AsyncMock()]

    # Act
    contacts = await get_contacts(mock_db, user)

    # Assert
    assert len(contacts) == 1
    mock_db.execute.assert_awaited_once()


@pytest.mark.asyncio
@patch("src.database.db.AsyncSession")
async def test_get_contact(mock_async_session):
    # Arrange
    mock_db = AsyncMock()
    mock_async_session.return_value.__aenter__.return_value = mock_db
    user = AsyncMock(id=1)
    mock_db.execute.return_value.scalars.return_value.first.return_value = AsyncMock(
        id=1
    )

    # Act
    contact = await get_contact(mock_db, 1, user)

    # Assert
    assert contact.id == 1
    mock_db.execute.assert_awaited_once()


@pytest.mark.asyncio
@patch("src.database.db.AsyncSession")
async def test_update_contact(mock_async_session):
    # Arrange
    mock_db = AsyncMock()
    mock_async_session.return_value.__aenter__.return_value = mock_db
    user = AsyncMock(id=1)
    mock_db.execute.return_value.scalars.return_value.first.return_value = AsyncMock()

    update_data = ContactUpdate(first_name="Jane")

    # Act
    updated_contact = await update_contact(mock_db, 1, update_data, user)

    # Assert
    assert updated_contact.first_name == "Jane"
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
@patch("src.database.db.AsyncSession")
async def test_delete_contact(mock_async_session):
    # Arrange
    mock_db = AsyncMock()
    mock_async_session.return_value.__aenter__.return_value = mock_db
    user = AsyncMock(id=1)
    mock_db.execute.return_value.scalars.return_value.first.return_value = AsyncMock()

    # Act
    deleted_contact = await delete_contact(mock_db, 1, user)

    # Assert
    assert deleted_contact is not None
    mock_db.delete.assert_awaited_once()
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
@patch("src.database.db.AsyncSession")
async def test_search_contacts(mock_async_session):
    # Arrange
    mock_db = AsyncMock()
    mock_async_session.return_value.__aenter__.return_value = mock_db
    user = AsyncMock(id=1)
    mock_db.execute.return_value.scalars.return_value.all.return_value = [
        AsyncMock(first_name="John")
    ]

    # Act
    contacts = await search_contacts(mock_db, "John", user)

    # Assert
    assert len(contacts) > 0
    mock_db.execute.assert_awaited_once()


@pytest.mark.asyncio
@patch("src.database.db.AsyncSession")
async def test_get_upcoming_birthdays(mock_async_session):
    # Arrange
    mock_db = AsyncMock()
    mock_async_session.return_value.__aenter__.return_value = mock_db
    user = AsyncMock(id=1)
    mock_db.execute.return_value.all.return_value = [
        AsyncMock(first_name="John", last_name="Doe", birthday="2025-06-30")
    ]

    # Act
    birthdays = await get_upcoming_birthdays(mock_db, user)

    # Assert
    assert len(birthdays) > 0
    mock_db.execute.assert_awaited_once()
