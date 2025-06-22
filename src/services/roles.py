from fastapi import Depends, HTTPException, status, Request
from src.services.auth import auth_service
from src.database.models import Role
from typing import List
import logging

logger = logging.getLogger(__name__)


class RoleAccess:
    def __init__(self, allowed_roles: List[Role]):
        """
        Initialize a RoleAccess object.

        Args:
            allowed_roles: A list of allowed roles
        """
        self.allowed_roles = allowed_roles

    async def __call__(
        self,
        request: Request,
        current_user: dict = Depends(auth_service.get_current_user),
    ):
        """
        Perform a role-based access check and return the current user if
        authorized.

        Args:
            request: The current request.
            current_user: The current user as a dictionary.

        Returns:
            The current user if authorized, or raises an HTTPException with a 403
            status code and a detail message describing the authorization failure.

        Raises:
            HTTPException: If the current user does not have one of the allowed
                roles, or if the current user does not have a valid role.
        """
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
