"""Consistent API error envelope.

Responses use the shape:

{
  "error": {
    "code": "INVALID_URL",
    "message": "The provided URL is invalid.",
    "details": {}
  }
}

Stack traces are never exposed to clients.
"""

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Base application error."""

    code = "APP_ERROR"
    http_status = status.HTTP_400_BAD_REQUEST

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class NotFoundError(AppError):
    code = "NOT_FOUND"
    http_status = status.HTTP_404_NOT_FOUND


class AuthenticationError(AppError):
    code = "UNAUTHENTICATED"
    http_status = status.HTTP_401_UNAUTHORIZED


class AuthorizationError(AppError):
    code = "FORBIDDEN"
    http_status = status.HTTP_403_FORBIDDEN


class ConflictError(AppError):
    code = "CONFLICT"
    http_status = status.HTTP_409_CONFLICT


class ValidationError(AppError):
    code = "VALIDATION_ERROR"
    http_status = 422


class UnavailableError(AppError):
    code = "UNAVAILABLE"
    http_status = status.HTTP_503_SERVICE_UNAVAILABLE


def error_response(error: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=error.http_status,
        content={
            "error": {
                "code": error.code,
                "message": error.message,
                "details": error.details,
            }
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:  # noqa: ARG001
        return error_response(exc)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:  # noqa: ARG001
        return JSONResponse(
            status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", status.HTTP_422_UNPROCESSABLE_ENTITY),
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed.",
                    "details": {"errors": exc.errors()},
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:  # noqa: ARG001
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred.",
                    "details": {},
                }
            },
        )
