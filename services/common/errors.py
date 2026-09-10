from typing import Any


class SalesIntelligenceError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        context: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.context = context or {}
        self.cause = cause
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": self.code,
            "message": self.message,
            "context": self.context,
        }


class RetriableError(SalesIntelligenceError):
    pass


class NonRetriableError(SalesIntelligenceError):
    pass
