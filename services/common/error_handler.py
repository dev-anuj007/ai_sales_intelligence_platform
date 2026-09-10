from typing import Any
from fastapi import Request
from starlette.responses import JSONResponse

from services.common.errors import RetriableError, NonRetriableError
from services.logger.factory import get_logger_sync

logger = get_logger_sync()


class ErrorResponseHandler:
    RETRIABLE_STATUS_CODE = 429
    NON_RETRIABLE_STATUS_CODE = 400
    INTERNAL_ERROR_STATUS_CODE = 500

    async def handle(self, request: Request, exc: Exception) -> JSONResponse:
        if isinstance(exc, RetriableError):
            return self._handle_retriable(request, exc)
        elif isinstance(exc, NonRetriableError):
            return self._handle_non_retriable(request, exc)
        else:
            return self._handle_unhandled(request, exc)

    def _handle_retriable(self, request: Request, exc: RetriableError) -> JSONResponse:
        logger.warning(
            "error.retriable",
            error=exc,
            code=exc.code,
            path=request.url.path,
            method=request.method,
        )
        return JSONResponse(
            status_code=self.RETRIABLE_STATUS_CODE,
            content=exc.to_dict(),
        )

    def _handle_non_retriable(
        self, request: Request, exc: NonRetriableError
    ) -> JSONResponse:
        logger.warning(
            "error.non_retriable",
            error=exc,
            code=exc.code,
            path=request.url.path,
            method=request.method,
        )
        return JSONResponse(
            status_code=self.NON_RETRIABLE_STATUS_CODE,
            content=exc.to_dict(),
        )

    def _handle_unhandled(
        self, request: Request, exc: Exception
    ) -> JSONResponse:
        logger.error(
            "error.unhandled",
            error=exc,
            path=request.url.path,
            method=request.method,
        )
        return JSONResponse(
            status_code=self.INTERNAL_ERROR_STATUS_CODE,
            content={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
            },
        )


_handler = ErrorResponseHandler()


async def error_handler(request: Request, exc: Exception) -> JSONResponse:
    return await _handler.handle(request, exc)
