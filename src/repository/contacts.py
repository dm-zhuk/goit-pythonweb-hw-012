from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, extract, func
from datetime import date, timedelta

from src.database.models import Contact, User
from src.schemas.schemas import ContactCreate, ContactUpdate


async def create_contact(db: AsyncSession, contact: ContactCreate, user: User):
    """
    Creates a new contact and returns the newly created contact.

    Args:
        db: The database session to use.
        contact: The new contact's details.
        user: The user who is creating the contact.

    Returns:
        The newly created contact.

    Raises:
        HTTPException: If there is an error while creating the contact.
    """
    db_contact = Contact(**contact.model_dump(), user_id=user.id)
    db.add(db_contact)
    await db.commit()
    await db.refresh(db_contact)
    return db_contact


async def get_contacts(db: AsyncSession, user: User, skip: int = 0, limit: int = 10):
    """
    Retrieves a list of contacts associated with the given user.

    Args:
        db: The database session to use.
        user: The user whose contacts to retrieve.
        skip: The number of contacts to skip before returning the results.
        limit: The number of contacts to return.

    Returns:
        A list of contacts associated with the given user.
    """
    result = await db.execute(
        select(Contact).filter(Contact.user_id == user.id).offset(skip).limit(limit)
    )
    return result.scalars().all()


async def get_contact(db: AsyncSession, contact_id: int, user: User):
    """
    Retrieves a contact by ID if it belongs to the given user.

    Args:
        db: The database session to use.
        contact_id: The ID of the contact to retrieve.
        user: The user who owns the contact.

    Returns:
        The contact if it exists and belongs to the given user, or None if not found.
    """
    result = await db.execute(
        select(Contact).filter(Contact.id == contact_id, Contact.user_id == user.id)
    )
    return result.scalars().first()


async def update_contact(
    db: AsyncSession, contact_id: int, contact: ContactUpdate, user: User
):
    """
    Updates an existing contact and returns the updated contact.

    Args:
        db: The database session to use.
        contact_id: The ID of the contact to update.
        contact: The updated contact details.
        user: The user who owns the contact.

    Returns:
        The updated contact if it exists and belongs to the given user, or None if not found.

    Raises:
        HTTPException: If there is an error while updating the contact.
    """
    result = await db.execute(
        select(Contact).filter(Contact.id == contact_id, Contact.user_id == user.id)
    )
    db_contact = result.scalars().first()
    if db_contact:
        for key, value in contact.model_dump(exclude_unset=True).items():
            setattr(db_contact, key, value)
        await db.commit()
        await db.refresh(db_contact)
        return db_contact
    return None


async def delete_contact(db: AsyncSession, contact_id: int, user: User):
    """
    Deletes a contact by ID if it belongs to the given user.

    Args:
        db: The database session to use.
        contact_id: The ID of the contact to delete.
        user: The user who owns the contact.

    Returns:
        The deleted contact if it exists and belongs to the given user, or None if not found.
    """

    result = await db.execute(
        select(Contact).filter(Contact.id == contact_id, Contact.user_id == user.id)
    )
    db_contact = result.scalars().first()
    if db_contact:
        await db.delete(db_contact)
        await db.commit()
    return db_contact


async def search_contacts(db: AsyncSession, query: str, user: User):
    """
    Searches for contacts by query.

    Args:
        db: The database session to use.
        query: The search query.
        user: The user whose contacts to search.

    Returns:
        A list of contacts that match the given query.
    """
    result = await db.execute(
        select(Contact).filter(
            Contact.user_id == user.id,
            or_(
                Contact.first_name.ilike(f"%{query}%"),
                Contact.last_name.ilike(f"%{query}%"),
                Contact.email.ilike(f"%{query}%"),
            ),
        )
    )
    return result.scalars().all()


async def get_upcoming_birthdays(
    db: AsyncSession, user: User, days: int = 7, start_date: date = None
):
    """
    Retrieves a list of contacts that have an upcoming birthday in the given time range.

    Args:
        db: The database session to use.
        user: The user whose contacts to check.
        days: The number of days to check for upcoming birthdays, starting from today.
        start_date: The start date of the range to check for birthdays. If None, defaults to today.

    Returns:
        A list of contacts with upcoming birthdays, along with a message describing the birthday.
    """
    if days < 1:
        raise HTTPException(status_code=400, detail="Days must be positive")
    start = start_date or date.today()
    end = start + timedelta(days=days)
    result = await db.execute(
        select(
            Contact.id,
            Contact.first_name,
            Contact.last_name,
            func.to_char(Contact.birthday, "MON-DD").label("birthday_formatted"),
        ).filter(
            Contact.user_id == user.id,
            or_(
                (extract("month", Contact.birthday) == extract("month", start))
                & (
                    extract("day", Contact.birthday).between(
                        extract("day", start), extract("day", end)
                    )
                ),
                (extract("month", Contact.birthday) == extract("month", end))
                & (extract("day", Contact.birthday) <= extract("day", end)),
            ),
        )
    )
    contacts = result.all()
    return [
        {
            "message": f"{contact.first_name} {contact.last_name}'s birthday is on {contact.birthday_formatted} (ID: {contact.id})"
        }
        for contact in contacts
    ]
