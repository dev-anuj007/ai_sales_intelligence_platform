import asyncio
import time
from typing import TypeVar, Callable, Any
from functools import wraps

from services.common.errors import RetriableError
from services.logger.factory import get_logger_sync

logger = get_logger_sync()

F = TypeVar("F", bound=Callable[..., Any])


class ExponentialBackoffRetry:
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay_ms: int = 100,
        max_delay_ms: int = 10000,
        backoff_factor: float = 2.0,
    ) -> None:
        self.max_retries = max_retries
        self.initial_delay_ms = initial_delay_ms
        self.max_delay_ms = max_delay_ms
        self.backoff_factor = backoff_factor

    def __call__(self, func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            delay_ms = self.initial_delay_ms
            last_error: RetriableError | None = None

            for attempt in range(self.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except RetriableError as e:
                    last_error = e
                    if attempt >= self.max_retries:
                        logger.error(
                            "retry.exhausted",
                            error=e,
                            function=func.__name__,
                            total_attempts=attempt + 1,
                            max_retries=self.max_retries,
                        )
                        raise

                    logger.warning(
                        "retry.attempt",
                        error=e,
                        function=func.__name__,
                        attempt=attempt + 1,
                        max_retries=self.max_retries,
                        next_delay_ms=delay_ms,
                    )

                    time.sleep(delay_ms / 1000.0)
                    delay_ms = min(
                        int(delay_ms * self.backoff_factor), self.max_delay_ms
                    )

            assert last_error is not None
            raise last_error

        return wrapper  # type: ignore


class AsyncExponentialBackoffRetry:
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay_ms: int = 100,
        max_delay_ms: int = 10000,
        backoff_factor: float = 2.0,
    ) -> None:
        self.max_retries = max_retries
        self.initial_delay_ms = initial_delay_ms
        self.max_delay_ms = max_delay_ms
        self.backoff_factor = backoff_factor

    def __call__(self, func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            delay_ms = self.initial_delay_ms
            last_error: RetriableError | None = None

            for attempt in range(self.max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except RetriableError as e:
                    last_error = e
                    if attempt >= self.max_retries:
                        logger.error(
                            "retry.exhausted",
                            error=e,
                            function=func.__name__,
                            total_attempts=attempt + 1,
                            max_retries=self.max_retries,
                        )
                        raise

                    logger.warning(
                        "retry.attempt",
                        error=e,
                        function=func.__name__,
                        attempt=attempt + 1,
                        max_retries=self.max_retries,
                        next_delay_ms=delay_ms,
                    )

                    await asyncio.sleep(delay_ms / 1000.0)
                    delay_ms = min(
                        int(delay_ms * self.backoff_factor), self.max_delay_ms
                    )

            assert last_error is not None
            raise last_error

        return wrapper  # type: ignore


def retry_on_retriable_error(
    max_retries: int = 3,
    initial_delay_ms: int = 100,
    max_delay_ms: int = 10000,
    backoff_factor: float = 2.0,
) -> Callable[[F], F]:
    return ExponentialBackoffRetry(
        max_retries=max_retries,
        initial_delay_ms=initial_delay_ms,
        max_delay_ms=max_delay_ms,
        backoff_factor=backoff_factor,
    )


def async_retry_on_retriable_error(
    max_retries: int = 3,
    initial_delay_ms: int = 100,
    max_delay_ms: int = 10000,
    backoff_factor: float = 2.0,
) -> Callable[[F], F]:
    return AsyncExponentialBackoffRetry(
        max_retries=max_retries,
        initial_delay_ms=initial_delay_ms,
        max_delay_ms=max_delay_ms,
        backoff_factor=backoff_factor,
    )
