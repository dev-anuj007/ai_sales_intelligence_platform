from contextlib import asynccontextmanager

import logfire
from fastapi import FastAPI

from services.logger.middleware import TraceMiddleware
from services.logger.factory import get_logger_sync
from services.common.errors import RetriableError, NonRetriableError
from services.common.error_handler import error_handler
from services.aggregation.api import router as aggregation_router
from services.pipeline.api import router as pipeline_router
from services.scoring.api import router as scoring_router
from services.enrichment.api import router as enrichment_router
from services.storage.accounts_api import router as accounts_router
from services.storage import init_pool, close_pool
from services.storage.migrate import apply_schema

logfire.configure()
logger = get_logger_sync()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_pool()
    apply_schema()
    logger.info("Storage connection pool initialized and schema applied")
    yield
    close_pool()
    logger.info("Storage connection pool closed")


app = FastAPI(
    title="AI Sales Intelligence Platform",
    description="Cybersecurity sales intelligence backend",
    version="0.1.0",
    lifespan=lifespan,
)

# Add trace middleware FIRST (before other middleware) for proper context propagation
app.add_middleware(TraceMiddleware)

# Add error handlers for structured error responses
app.add_exception_handler(RetriableError, error_handler)  # type: ignore
app.add_exception_handler(NonRetriableError, error_handler)  # type: ignore

logfire.instrument_system_metrics()
logfire.instrument_fastapi(app)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


app.include_router(accounts_router)
app.include_router(pipeline_router)
app.include_router(aggregation_router)
app.include_router(scoring_router)
app.include_router(enrichment_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8001)
