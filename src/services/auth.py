from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from src.services.base import settings
from src.services.email import send_reset_email
from src.database.connect import get_db, get_user_from_cache, rc
from src.database.models import Role

import logging

logger = logging.getLogger(__name__)


class Auth:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/users/login")

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        return self.pwd_context.hash(password)

    async def create_access_token(
        self, data: dict, expires_delta: float = settings.JWT_EXPIRE_MINUTES
    ) -> str:
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=expires_delta)
        to_encode.update(
            {"iat": datetime.utcnow(), "exp": expire, "scope": "access_token"}
        )
        return jwt.encode(
            to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM
        )

    async def create_email_token(self, data: dict) -> str:
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
        if user.get("roles") != Role.admin.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
            )
        return user


auth_service = Auth()
