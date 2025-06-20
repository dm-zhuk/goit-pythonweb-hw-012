let's make tests for the routers block:
src / routers / contacts.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import date

from src.database.db import get_db
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
=======
src / routers / users.py
import logging
from fastapi import (
    APIRouter,
    HTTPException,
    status,
    UploadFile,
    BackgroundTasks,
    Depends,
    File,
)
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_limiter.depends import RateLimiter
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.db import get_db, rc
from src.schemas.schemas import (
    UserCreate,
    UserResponse,
    Token,
    RequestEmail,
    PasswordResetRequest,
    PasswordResetConfirm,
)
from src.services.email import send_verification_email
from src.services.auth import auth_service
from src.services.base import settings
from src.services.get_upload import get_upload_file_service
from src.database.models import Role, User
from src.services.roles import RoleAccess
from src.repository.users import (
    create_user,
    get_user_by_email,
    confirm_email,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/users", tags=["users"])
upload_service = get_upload_file_service()

# Role-based access
allowed_get = RoleAccess([Role.admin, Role.user])
allowed_update = RoleAccess([Role.admin])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_user(
    user: UserCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Creates a new user.

    Args:
        user: The new user's details.
        background_tasks: The background task handler.
        db: The database session to use.

    Returns:
        The newly created user.

    Raises:
        HTTPException: If the email address is already registered.
    """
    db_user = await create_user(user, db)
    token = await auth_service.create_email_token({"sub": db_user.email})
    background_tasks.add_task(
        send_verification_email, db_user.email, token, str(settings.BASE_URL)
    )
    return db_user


@router.post(
    "/login",
    response_model=Token,
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticates a user using username and password.

    Args:
        form_data: The OAuth2 form data containing the username and password.
        db: The database session to use.

    Returns:
        An access token and token type.

    Raises:
        HTTPException: If the credentials are invalid.
    """
    email = form_data.username
    user_model = await get_user_by_email(email, db)

    if not user_model or not auth_service.verify_password(
        form_data.password, user_model.hashed_password
    ):
        logger.warning(f"Failed login attempt for user: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = await auth_service.create_access_token({"sub": user_model.email})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/request_email")
async def request_email(
    body: RequestEmail,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Requests a verification email for a user.

    Args:
        body: The request data containing the user's email address.
        background_tasks: The background task handler.
        db: The database session to use.

    Raises:
        HTTPException: If the user is not found, or if the email address is already verified.

    Returns:
        A message indicating that the verification email was sent successfully.
    """
    user = await get_user_by_email(body.email, db)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already verified"
        )

    token = await auth_service.create_email_token({"sub": user.email})
    background_tasks.add_task(
        send_verification_email, body.email, token, str(settings.BASE_URL)
    )
    return {"message": "Verification email sent successfully"}


@router.get("/verify")
async def verify_email(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Verifies a user's email address.

    Args:
        token: The verification token sent to the user's email address.
        db: The database session to use.

    Returns:
        A message indicating that the email was verified successfully.

    Raises:
        HTTPException: If the user is not found, or if the email address is already verified.
    """
    email = await auth_service.get_email_from_token(token)
    user = await get_user_by_email(email, db)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    if user.is_verified:
        return {"message": "Email already verified"}

    await confirm_email(email, db)
    return {"message": "Email verified successfully"}


@router.get(
    "/me",
    response_model=UserResponse,
    dependencies=[
        Depends(allowed_get),
        Depends(RateLimiter(times=5, seconds=60)),
    ],
)
async def read_users_me(
    current_user: dict = Depends(auth_service.get_current_user),
):
    """
    Retrieve the current authenticated user's information.

    Args:
        current_user: The current authenticated user obtained from the token.

    Returns:
        The user's information including id, email, verification status,
        avatar URL, and roles as a UserResponse model.

    Dependencies:
        - Role-based access control allowing 'admin' and 'user' roles.
        - Rate limiting to 5 requests per 60 seconds.
    """

    return UserResponse.model_validate(
        User(
            id=current_user["id"],
            email=current_user["email"],
            is_verified=current_user["is_verified"],
            avatar_url=current_user["avatar_url"],
            roles=Role(current_user["roles"]),
        )
    )


@router.patch(
    "/me/avatar",
    response_model=UserResponse,
    dependencies=[Depends(allowed_update), Depends(RateLimiter(times=5, seconds=60))],
)
async def update_avatar(
    file: UploadFile = File(),
    current_user: dict = Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update the avatar for the current authenticated user.

    Args:
        file: The new avatar image file to upload.
        current_user: The current authenticated user obtained from the token.
        db: The database session for updating the user's information.

    Returns:
        The updated user's information, including the new avatar URL, as a UserResponse model.

    Raises:
        HTTPException: If the avatar upload fails.
    """

    try:
        image_url = upload_service.upload_file(file, current_user["email"])
    except Exception as e:
        logger.error(f"Failed to upload avatar: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload avatar",
        )

    user = await get_user_by_email(current_user["email"], db)
    user.avatar_url = image_url
    db.add(user)
    await db.commit()
    await db.refresh(user)
    await rc.delete(f"fetch_user:{current_user['email']}")
    return UserResponse.model_validate(user)


@router.post(
    "/password-reset/request",
    dependencies=[Depends(allowed_get)],
)
async def request_password_reset(
    request: PasswordResetRequest,
    current_user: dict = Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Requests a password reset email.

    Args:
        request: The request containing the email address.

    Raises:
        HTTPException: If the request is invalid or the email address is not the current user's.
    """
    if request.email != current_user["email"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only request password reset for your own email",
        )
    try:
        await auth_service.request_password_reset(current_user["email"], db)
        return {"message": "Password reset email sent"}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in password reset request: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post(
    "/password-reset/confirm",
)
async def reset_password(
    request: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db),
):
    """
    Resets a user's password.

    Args:
        request: The request containing the new password and the verification token.

    Returns:
        A JSON response with a message indicating the password reset was successful.

    Raises:
        HTTPException: If the request is invalid or the verification token is expired.
    """
    try:
        await auth_service.reset_password(request.token, request.new_password, db)
        return {"message": "Password reset successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in password reset: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
=======
src / routers / utils.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from src.database.db import get_db

router = APIRouter(tags=["healthchecker"])


@router.get("/healthchecker")
async def healthchecker(db: AsyncSession = Depends(get_db)):
    """
    Simple health checker that verifies that the database connection is working properly.

    Returns a 200 OK response with a message if the database is reachable, and a 500 Internal Server Error
    if there is an issue with the database connection.
    """
    try:
        result = await db.execute(text("SELECT 1"))
        result = result.scalar_one_or_none()

        if result is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database is not reachable",
            )
        return {
            "message": "Database configured correctly. Welcome to the Contacts FAST API v2.0!"
        }
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error connecting to the database",
        )

^^^^^^^^^^^^^^^^^^^^^^
let's make tests for the Service block:
src.services.email - import send_verification_email, send_reset_email
from fastapi_mail import FastMail, ConnectionConfig, MessageSchema, MessageType
from pathlib import Path
from src.services.base import settings
import logging

logger = logging.getLogger(__name__)

conf = ConnectionConfig(
    MAIL_USERNAME=settings.SMTP_USER,
    MAIL_PASSWORD=settings.SMTP_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM_EMAIL,
    MAIL_PORT=settings.SMTP_PORT,
    MAIL_SERVER=settings.SMTP_SERVER,
    MAIL_FROM_NAME="Contacts Management API",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
    TEMPLATE_FOLDER=Path(__file__).parent / "templates",
)


async def send_verification_email(email: str, token: str, BASE_URL: str):
    try:
        message = MessageSchema(
            subject="Email Confirmation",
            recipients=[email],
            template_body={"host": BASE_URL, "username": email, "token": token},
            subtype=MessageType.html,
        )
        fm = FastMail(conf)
        await fm.send_message(message, template_name="email_template.html")
        logger.info(f"Verification email sent to {email}")
    except Exception as e:
        logger.error(f"Failed to send verification email to {email}: {e}")
        raise


async def send_reset_email(email: str, token: str, BASE_URL: str):
    try:
        message = MessageSchema(
            subject="Password Reset Request",
            recipients=[email],
            template_body={"host": BASE_URL, "username": email, "token": token},
            subtype=MessageType.html,
        )
        fm = FastMail(conf)
        await fm.send_message(message, template_name="email_template_reset.html")
        logger.info(f"Password reset email sent to {email}")
    except Exception as e:
        logger.error(f"Failed to send password reset email to {email}: {e}")
        raise
============
src.services.base - import Settings
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET: str
    JWT_ALGORITHM: str
    JWT_EXPIRE_MINUTES: int
    CLOUDINARY_CLOUD_NAME: str
    CLOUDINARY_API_KEY: str
    CLOUDINARY_API_SECRET: str
    SMTP_SERVER: str
    SMTP_PORT: int
    SMTP_USER: str
    SMTP_PASSWORD: str
    MAIL_FROM_EMAIL: str
    BASE_URL: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    PGADMIN_DEFAULT_EMAIL: str
    PGADMIN_DEFAULT_PASSWORD: str

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
=============
src.services.auth
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from src.services.base import settings
from src.services.email import send_reset_email
from src.database.db import get_db, get_user_from_cache, rc
from src.database.models import Role

import logging

logger = logging.getLogger(__name__)


class Auth:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/users/login")

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verifies a plain password against a hashed password.

        Args:
            plain_password (str): The plain password to verify.
            hashed_password (str): The hashed password to verify against.

        Returns:
            bool: True if the password is valid, False otherwise.
        """
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """
        Gets the hashed version of a given password.

        Args:
            password (str): The plain password to hash.

        Returns:
            str: The hashed password.
        """
        return self.pwd_context.hash(password)

    async def create_access_token(
        self, data: dict, expires_delta: float = settings.JWT_EXPIRE_MINUTES
    ) -> str:
        """
        Creates a JWT access token.

        Args:
            data (dict): The data to encode into the token.
            expires_delta (float, optional): The time in minutes after which the token
                expires. Defaults to settings.JWT_EXPIRE_MINUTES.

        Returns:
            str: The encoded JWT access token.
        """
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=expires_delta)
        to_encode.update(
            {"iat": datetime.utcnow(), "exp": expire, "scope": "access_token"}
        )
        return jwt.encode(
            to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM
        )

    async def create_email_token(self, data: dict) -> str:
        """
        Creates a JWT email token.

        Args:
            data (dict): The data to encode into the token.

        Returns:
            str: The encoded JWT email token.
        """
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(hours=1)
        to_encode.update(
            {"iat": datetime.utcnow(), "exp": expire, "scope": "email_token"}
        )
        logger.info(f"Creating email token with secret: {settings.JWT_SECRET[:4]}...")
        return jwt.encode(
            to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM
        )

    async def get_current_user(
        self, token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
    ) -> dict:
        """
        Gets the current authenticated user by verifying the JWT access token.

        Args:
            token (str, optional): The JWT access token to verify. Defaults to
                Depends(oauth2_scheme).
            db (AsyncSession, optional): The database session to use. Defaults to
                Depends(get_db).

        Returns:
            dict: The current authenticated user if the token is valid, or raises
                an HTTPException with a 401 status code otherwise.
        """
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(
                token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
            )
            email = payload.get("sub")
            if email is None:
                raise credentials_exception
        except JWTError:
            raise credentials_exception

        user = await get_user_from_cache(email, db)

        return user

    async def get_email_from_token(self, token: str) -> str:
        """
        Gets the email address associated with a JWT email token.

        Args:
            token (str): The JWT email token to verify.

        Returns:
            str: The email address associated with the token if it is valid, or raises
                an HTTPException with a 401 status code for an invalid scope or a 422
                status code for an invalid token otherwise.
        """
        try:
            payload = jwt.decode(
                token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
            )
            if payload["scope"] != "email_token":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid scope"
                )
            return payload["sub"]
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid token"
            )

    async def request_password_reset(self, email: str, db: AsyncSession) -> None:
        """
        Initiates a password reset request by generating a reset token and sending a reset email.

        Args:
            email (str): The email address of the user requesting the password reset.
            db (AsyncSession): The database session to use for retrieving the user.

        Raises:
            HTTPException: If the user is not found in the database.

        Side Effects:
            Stores a reset token with a 1-hour expiration in the cache and sends a password reset email to the user.
        """

        from src.repository.users import get_user_by_email

        user = await get_user_by_email(email, db)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        token = await self.create_email_token({"sub": email})
        try:
            await rc.setex(f"reset_token:{token}", 3600, email)
        except Exception as e:
            logger.error(f"Failed to store reset token: {str(e)}")
        await send_reset_email(email, token, str(settings.BASE_URL))

    async def reset_password(
        self, token: str, new_password: str, db: AsyncSession
    ) -> None:
        """
        Resets the user's password using a reset token.

        Args:
            token (str): The reset token that was sent to the user's email.
            new_password (str): The new password to set for the user.
            db (AsyncSession): The database session to use for updating the user's password.

        Raises:
            HTTPException: If the token is invalid or expired, if the token does not match the cached email,
                        or if the user is not found in the database.

        Side Effects:
            Updates the user's password in the database and deletes the reset token from the cache.
        """

        from src.repository.users import get_user_by_email

        cached_email = await rc.get(f"reset_token:{token}")
        if not cached_email:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        email = await self.get_email_from_token(token)
        if email != cached_email:
            raise HTTPException(status_code=401, detail="Token mismatch")
        user = await get_user_by_email(email, db)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        hashed_password = self.get_password_hash(new_password)
        user.hashed_password = hashed_password
        await db.commit()
        await rc.delete(f"reset_token:{token}")

    async def get_current_admin(self, user: dict = Depends(get_current_user)) -> dict:
        """
        Checks if the current user is an admin.

        Args:
            user: The current user as a dictionary.

        Returns:
            The current user if they are an admin.

        Raises:
            HTTPException: If the user is not an admin.
        """
        if user.get("roles") != Role.admin.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
            )
        return user


auth_service = Auth()
