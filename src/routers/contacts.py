from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import date

from src.database.connect import get_db
from src.schemas.schemas import (
    ContactCreate,
    ContactResponse,
    ContactUpdate,
    BirthdayResponse,
)
from src.repository.contacts import (
    create_contact,
    get_contacts,
    get_contact,
    update_contact,
    delete_contact,
    search_contacts,
    get_upcoming_birthdays,
)
from src.database.models import User
from src.services.auth import auth_service

import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.post("/", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
async def create_new_contact(
    contact: ContactCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_user),
):
    """
    Create a new contact

    Args:
        contact: Contact to create
        db: Database session
        current_user: The current user

    Returns:
        The newly created contact
    """
    try:
        return await create_contact(db, contact, current_user)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/", response_model=List[ContactResponse])
async def read_contacts(
    skip: int = 0,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_user),
):
    """
    Retrieve a list of contacts for the current user.

    Args:
        skip: Number of contacts to skip before starting to collect the result set.
        limit: Maximum number of contacts to return.
        db: Database session for executing queries.
        current_user: The user whose contacts are to be retrieved.

    Returns:
        A list of contacts associated with the current user.

    Raises:
        HTTPException: If an error occurs while retrieving contacts.
    """

    try:
        return await get_contacts(db, current_user, skip, limit)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/{contact_id}", response_model=ContactResponse)
async def read_contact(
    contact_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_user),
):
    """
    Retrieve a contact by its id.

    Args:
        contact_id: The id of the contact to retrieve.
        db: Database session for executing queries.
        current_user: The current user.

    Returns:
        The contact associated with the given id.

    Raises:
        HTTPException: If the contact is not found, or if there is an error
            while retrieving the contact.
    """
    try:
        contact = await get_contact(db, contact_id, current_user)
        if not contact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found"
            )
        return contact
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error retrieving contact: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get("/search/", response_model=List[ContactResponse])
async def search_contacts_by_query(
    query: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_user),
):
    """
    Search for contacts by query string.

    Args:
        query: The query string to search for.
        db: Database session for executing queries.
        current_user: The current user.

    Returns:
        A list of contacts associated with the current user that match the search query.

    Raises:
        HTTPException: If an error occurs while searching for contacts.
    """
    try:
        return await search_contacts(db, query, current_user)
    except Exception as e:
        logger.error(f"Error searching contacts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.put("/{contact_id}", response_model=ContactResponse)
async def update_existing_contact(
    contact_id: int,
    contact: ContactUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_user),
):
    """
    Update an existing contact.

    Args:
        contact_id: The ID of the contact to update.
        contact: The updated contact details.
        db: Database session for executing queries.
        current_user: The current user.

    Returns:
        The updated contact if it exists and belongs to the given user, or None if not found.

    Raises:
        HTTPException: If the contact is not found, or if there is an error
            while updating the contact.
    """
    updated_contact = await update_contact(db, contact_id, contact, current_user)
    if not updated_contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found"
        )
    return updated_contact


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_contact(
    contact_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_user),
):
    """
    Deletes an existing contact.

    Args:
        contact_id: The ID of the contact to delete.
        db: Database session for executing queries.
        current_user: The current user.

    Returns:
        None

    Raises:
        HTTPException: If the contact is not found.
    """

    contact = await delete_contact(db, contact_id, current_user)
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found"
        )
    return None


@router.get("/birthdays/", response_model=List[BirthdayResponse])
async def get_contacts_with_upcoming_birthdays(
    days: int = 7,
    start_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_user),
):
    """
    Retrieves a list of contacts with upcoming birthdays.

    Args:
        days: The number of days to check for upcoming birthdays, starting from today.
        start_date: The start date of the range to check for birthdays. If None, defaults to today.

    Returns:
        A list of contacts with upcoming birthdays, along with a message describing the birthday.

    Raises:
        HTTPException: If there is an error while retrieving the list of contacts.
    """
    try:
        return await get_upcoming_birthdays(db, current_user, days, start_date)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
