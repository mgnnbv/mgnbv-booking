from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError


class AppError(Exception):
    """Базовая ошибка приложения: несёт HTTP-статус и сообщение для клиента."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class NotFoundError(AppError):
    def __init__(self, detail: str = "Не найдено") -> None:
        super().__init__(404, detail)


class ForbiddenError(AppError):
    def __init__(self, detail: str = "Доступ запрещён") -> None:
        super().__init__(403, detail)


class ConflictError(AppError):
    def __init__(self, detail: str = "Конфликт данных") -> None:
        super().__init__(409, detail)


class UnauthorizedError(AppError):
    def __init__(self, detail: str = "Неверные учётные данные") -> None:
        super().__init__(401, detail)


class ValidationError(AppError):
    def __init__(self, detail: str = "Ошибка валидации") -> None:
        super().__init__(422, detail)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(IntegrityError)
    async def handle_integrity_error(request: Request, exc: IntegrityError) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={"detail": "Конфликт данных: нарушено ограничение целостности"},
        )