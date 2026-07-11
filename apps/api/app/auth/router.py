from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import AuthSession, LoginRequest, RegisterRequest, UserOut
from app.auth.security import create_access_token, get_current_user, hash_password, verify_password
from app.core.config import get_settings
from app.core.database import get_session
from app.core.models import User, UserProfile

router = APIRouter(prefix="/api/auth", tags=["auth"])
DEMO_EMAIL = "demo@nutrilens.app"
DEMO_PASSWORD = "nutrilens-demo"


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        is_active=user.is_active,
    )


def _set_session_cookie(response: Response, user: User) -> AuthSession:
    settings = get_settings()
    max_age = settings.access_token_minutes * 60
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=create_access_token(user.id),
        max_age=max_age,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        path="/",
    )
    return AuthSession(user=_user_out(user), expires_in=max_age)


@router.post("/register", response_model=AuthSession, status_code=201)
async def register(
    request: RegisterRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> AuthSession:
    email = str(request.email).lower()
    existing = await session.scalar(select(User).where(User.email == email))
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    user = User(
        email=email,
        display_name=request.display_name.strip(),
        password_hash=hash_password(request.password),
    )
    session.add(user)
    await session.flush()
    session.add(UserProfile(user_id=user.id))
    await session.commit()
    await session.refresh(user)
    return _set_session_cookie(response, user)


@router.post("/login", response_model=AuthSession)
async def login(
    request: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> AuthSession:
    email = str(request.email).lower()
    user = await session.scalar(select(User).where(User.email == email))
    if user is None or not user.is_active or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    return _set_session_cookie(response, user)


@router.post("/demo", response_model=AuthSession)
async def demo_session(
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> AuthSession:
    user = await session.scalar(select(User).where(User.email == DEMO_EMAIL))
    if user is None:
        user = User(
            email=DEMO_EMAIL,
            display_name="Portfolio Demo",
            password_hash=hash_password(DEMO_PASSWORD),
        )
        session.add(user)
        await session.flush()
        session.add(UserProfile(user_id=user.id, goal="low_sugar"))
        await session.commit()
        await session.refresh(user)
    return _set_session_cookie(response, user)


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)) -> UserOut:
    return _user_out(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(settings.auth_cookie_name, path="/")
