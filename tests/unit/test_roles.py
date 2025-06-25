import pytest

from fastapi import HTTPException, status

from src.services.roles import RoleAccess
from src.database.models import Role


class DummyRequest:
    def __init__(self, method="GET", url="http://testserver/api/resource"):
        self.method = method
        self.url = url

    def __str__(self):
        return self.url


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "user_role, allowed_roles, should_pass",
    [
        (Role.admin.value, [Role.admin, Role.user], True),
        (Role.user.value, [Role.admin, Role.user], True),
        (Role.user.value, [Role.admin], False),
    ],
)
async def test_role_access(user_role, allowed_roles, should_pass):
    role_access = RoleAccess(allowed_roles)

    current_user = {"roles": user_role}
    request = DummyRequest()

    if should_pass:
        result = await role_access(request, current_user=current_user)
        assert result == current_user
    else:
        with pytest.raises(HTTPException) as exc:
            await role_access(request, current_user=current_user)
        assert exc.value.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_role_access_invalid_role():
    role_access = RoleAccess([Role.admin])

    current_user = {"roles": "not_a_valid_role"}
    request = DummyRequest()

    with pytest.raises(HTTPException) as exc:
        await role_access(request, current_user=current_user)

    assert exc.value.status_code == status.HTTP_403_FORBIDDEN
    assert "Invalid user role" in exc.value.detail
