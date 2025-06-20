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
        logger.info(f"Generated token: {token}")
        try:
            await rc.setex(f"reset_token:{token}", 3600, email)
            logger.info(f"Stored reset token for {email}")
        except Exception as e:
            logger.info(f"Failed to store reset token: {e}")

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
