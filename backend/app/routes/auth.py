from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_current_user, hash_password, verify_password
from app.database.session import get_db
from app.models.user import Role, User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.core.auth_limit import limit_authentication

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=user.role.name,
        is_active=user.is_active,
    )


@router.post("/register", response_model=UserResponse, status_code=201,
             dependencies=[Depends(limit_authentication)], responses={429: {"description": "Too many attempts; Retry-After specifies seconds"}})
def register(data: RegisterRequest, db: Session = Depends(get_db)) -> UserResponse:
    email = str(data.email).strip().lower()
    if db.scalar(select(User.id).where(User.email == email)) is not None:
        raise HTTPException(status_code=409, detail="Email already registered")
    farmer = db.scalar(select(Role).where(Role.name == "farmer"))
    if farmer is None:
        farmer = Role(name="farmer")
        db.add(farmer)
        db.flush()
    user = User(
        email=email,
        password_hash=hash_password(data.password),
        display_name=data.display_name.strip(),
        role_id=farmer.id,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email already registered") from exc
    db.refresh(user)
    return user_response(user)


@router.post("/login", response_model=TokenResponse,
             dependencies=[Depends(limit_authentication)], responses={429: {"description": "Too many attempts; Retry-After specifies seconds"}})
def login(data: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == str(data.email).strip().lower()))
    if user is None or not verify_password(data.password, user.password_hash) or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)) -> UserResponse:
    return user_response(user)
