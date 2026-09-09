from contextlib import asynccontextmanager

import logfire
from fastapi import FastAPI

from services.aggregation.api import router as aggregation_router
from services.pipeline.api import router as pipeline_router
from services.scoring.api import router as scoring_router
from services.enrichment.api import router as enrichment_router
from services.storage import init_pool, close_pool

logfire.configure()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_pool()
    logfire.info("Storage connection pool initialized")
    yield
    close_pool()
    logfire.info("Storage connection pool closed")


app = FastAPI(
    title="AI Sales Intelligence Platform",
    description="Cybersecurity sales intelligence backend",
    version="0.1.0",
    lifespan=lifespan,
)

logfire.instrument_system_metrics()
logfire.instrument_fastapi(app)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


app.include_router(pipeline_router)
app.include_router(aggregation_router)
app.include_router(scoring_router)
app.include_router(enrichment_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8001)
