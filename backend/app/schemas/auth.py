import re
from datetime import datetime

import email_validator
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from pydantic.networks import MAX_EMAIL_LENGTH, validate_email as _strict_validate_email
from pydantic_core import PydanticCustomError

_LOCAL_PART_RE = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]{1,64}$")
_DOMAIN_LABEL_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")


def _is_special_use_domain(domain: str) -> bool:
    d = domain.lower().rstrip(".")
    return any(d == s or d.endswith("." + s) for s in email_validator.SPECIAL_USE_DOMAIN_NAMES)


class AppEmail(EmailStr):
    """EmailStr that also accepts special-use domains (.local, .internal).

    Required for the demo account (demo@wiseweb-ai.local). The app never sends
    email, so accepting these addresses poses no delivery risk. Special-use
    domains bypass email_validator (which rejects them unconditionally) and
    are checked with an equivalent syntax-only validation.
    """

    @classmethod
    def _validate(cls, input_value: str, /) -> str:
        if isinstance(input_value, str):
            local, sep, domain = input_value.strip().rpartition("@")
            if sep and _is_special_use_domain(domain):
                return cls._validate_special_use(local, domain)
        return _strict_validate_email(input_value)[1]

    @classmethod
    def _validate_special_use(cls, local: str, domain: str) -> str:
        reason = None
        if not local or not _LOCAL_PART_RE.match(local):
            reason = "The part before the @-sign is not valid."
        elif len(domain) > 253 or any(not _DOMAIN_LABEL_RE.match(label) for label in domain.split(".")):
            reason = "The part after the @-sign is not valid."
        elif len(local) + 1 + len(domain) > MAX_EMAIL_LENGTH:
            reason = f"Length must not exceed {MAX_EMAIL_LENGTH} characters"
        if reason:
            raise PydanticCustomError(
                "value_error", "value is not a valid email address: {reason}", {"reason": reason}
            )
        return f"{local}@{domain.lower()}"


class RegisterRequest(BaseModel):
    email: AppEmail
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)


class LoginRequest(BaseModel):
    email: AppEmail
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: AppEmail
    full_name: str
    is_active: bool
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse
