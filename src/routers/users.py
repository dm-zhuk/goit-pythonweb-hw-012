# src/routers/users.py
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
