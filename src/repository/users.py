import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status, Depends
from typing import Optional, Union
from libgravatar import Gravatar

from src.database.db import get_db
from src.database.models import User
from src.schemas.schemas import UserCreate, UserResponse
from src.services.auth import auth_service


logger = logging.getLogger(__name__)


async def create_user(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Creates a new user and returns the newly created user.

    Args:
        body: The new user's details.
        db: The database session to use.

    Returns:
        The newly created user.

    Raises:
        HTTPException: If the email address is already registered.
    """
    existing_user = await get_user_by_email(body.email, db)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )

    hashed_password = auth_service.get_password_hash(body.password)

    # Get avatar link from Gravatar
    try:
        g = Gravatar(body.email)
        avatar = g.get_image()
    except Exception as e:
        logger.warning(f"Failed to get Gravatar for {body.email}: {e}")
        avatar = None

    new_user = User(
        email=body.email, hashed_password=hashed_password, avatar_url=avatar
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user


async def get_user_by_email(
    email: str,
    db: AsyncSession = Depends(get_db),
    response: bool = False,
) -> Optional[Union[UserResponse, User]]:
    """
    Get a user by their email address.

    Args:
        email: The email address of the user to find.
        db: The database session to use.
        response: If True, return the user as a UserResponse object. Otherwise, return the User ORM object.

    Returns:
        The user if found, or None if not.

    """

    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if user:
        if response:
            return UserResponse(
                id=user.id,
                email=user.email,
                is_verified=user.is_verified,
                avatar_url=user.avatar_url,
            )
        return user

    return None


async def confirm_email(
    email: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Verify a user's email address.

    Args:
        email: The email address of the user to verify.
        db: The database session to use.

    Returns:
        None

    Raises:
        HTTPException: If the user is not found, or if there is an error
            while updating the database.
    """
    user = await get_user_by_email(email, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    if user.is_verified:
        logger.info(f"Email {email} is already verified")
        return
    user.is_verified = True
    try:
        db.add(user)
        await db.commit()
        await db.refresh(user)
        logger.info(
            f"Email {email} verified successfully, is_verified={user.is_verified}"
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to verify email {email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify email: {str(e)}",
        )
