"""Authentication service."""

import jwt as pyjwt
from sqlalchemy.orm import Session

from app.core.exceptions import AuthenticationError, ConflictError
from app.core.security import (
    create_access_token, create_refresh_token, decode_token, hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories.user_repository import UserRepository


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)

    def register(self, email: str, password: str, full_name: str) -> User:
        email = email.lower().strip()
        if self.users.get_by_email(email):
            raise ConflictError("An account with this email already exists.")
        user = self.users.create(
            email=email,
            password_hash=hash_password(password),
            full_name=full_name.strip(),
            is_active=True,
        )
        self.db.commit()
        return user

    def login(self, email: str, password: str) -> User:
        user = self.users.get_by_email(email.lower().strip())
        if user is None or not user.is_active:
            raise AuthenticationError("Invalid email or password.")
        if not verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid email or password.")
        return user

    def issue_tokens(self, user: User) -> dict:
        return {
            "access_token": create_access_token(user.id),
            "refresh_token": create_refresh_token(user.id),
        }

    def refresh(self, refresh_token: str) -> tuple[User, dict]:
        try:
            payload = decode_token(refresh_token, expected_type="refresh")
            user_id = int(payload["sub"])
        except (pyjwt.PyJWTError, KeyError, ValueError):
            raise AuthenticationError("Invalid or expired refresh token.") from None
        user = self.users.get_by_id(user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("User not found or inactive.")
        return user, self.issue_tokens(user)
