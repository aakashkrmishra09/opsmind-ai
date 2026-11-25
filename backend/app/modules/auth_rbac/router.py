from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.modules.auth_rbac.dependencies import get_current_user, require_roles
from app.modules.auth_rbac.models import AuditLog, Role, User
from app.modules.auth_rbac.schemas import LoginRequest, TokenResponse, UserCreate, UserRead

router = APIRouter(tags=["Auth & Users"])


@router.post("/auth/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == payload.email.lower()))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    db.add(
        AuditLog(
            actor_user_id=user.id,
            action="auth.login",
            resource_type="user",
            resource_id=str(user.id),
            metadata_json={"email": user.email},
        )
    )
    await db.commit()

    token = create_access_token(subject=str(user.id), roles=user.role_names)
    return TokenResponse(access_token=token)


@router.get("/auth/me", response_model=UserRead)
async def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.get("/users", response_model=list[UserRead])
async def list_users(
    _: User = Depends(require_roles("Admin")),
    db: AsyncSession = Depends(get_db),
) -> list[User]:
    result = await db.execute(select(User).order_by(User.created_at.asc()))
    return list(result.scalars().all())


@router.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    admin_user: User = Depends(require_roles("Admin")),
    db: AsyncSession = Depends(get_db),
) -> User:
    existing = await db.execute(select(User).where(User.email == payload.email.lower()))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    role_result = await db.execute(select(Role).where(Role.name.in_(payload.roles)))
    roles = list(role_result.scalars().all())
    if len(roles) != len(set(payload.roles)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more specified roles do not exist",
        )

    new_user = User(
        email=payload.email.lower(),
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        roles=roles,
    )
    db.add(new_user)
    await db.flush()

    db.add(
        AuditLog(
            actor_user_id=admin_user.id,
            action="user.create",
            resource_type="user",
            resource_id=str(new_user.id),
            metadata_json={"created_email": new_user.email, "roles": payload.roles},
        )
    )
    await db.commit()
    await db.refresh(new_user)
    return new_user