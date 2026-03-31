"""Application error handling."""

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from src.schemas.common import ErrorEnvelope


class AppError(Exception):
    """Base application exception with a stable API error shape."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class AuthenticationError(AppError):
    def __init__(self, message: str = "Authentication is required") -> None:
        super().__init__(
            code="authentication_required",
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class AuthorizationError(AppError):
    def __init__(self, message: str = "You are not allowed to access this resource") -> None:
        super().__init__(
            code="forbidden",
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
        )


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(
            code="not_found",
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
        )


class ValidationError(AppError):
    def __init__(self, message: str = "Invalid input") -> None:
        super().__init__(
            code="validation_error",
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class ConfigurationError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(
            code="configuration_error",
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorEnvelope(
            error=exc.message,
            code=exc.code,
            details=exc.details,
        ).model_dump(mode="json"),
    )


async def unexpected_error_handler(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorEnvelope(
            error="An unexpected error occurred",
            code="internal_error",
            details={"exception_type": exc.__class__.__name__},
        ).model_dump(mode="json"),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(Exception, unexpected_error_handler)
