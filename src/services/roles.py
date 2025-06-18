from fastapi import Depends, HTTPException, status, Request
from src.services.auth import auth_service
from src.database.models import Role
from typing import List
import logging

logger = logging.getLogger(__name__)


class RoleAccess:
    def __init__(self, allowed_roles: List[Role]):
        self.allowed_roles = allowed_roles

    async def __call__(
        self,
        request: Request,
        current_user: dict = Depends(auth_service.get_current_user),
    ) -> dict:
        try:
            user_role = Role(current_user.get("roles"))
        except ValueError:
            logger.error(f"Invalid role: {current_user.get('roles')}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid user role",
            )
        if user_role not in self.allowed_roles:
            logger.debug(
                "Access check",
                extra={
                    "method": request.method,
                    "url": str(request.url),
                    "user_role": user_role,
                    "allowed_roles": self.allowed_roles,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: {user_role} not in {self.allowed_roles}",
            )
        return current_user
