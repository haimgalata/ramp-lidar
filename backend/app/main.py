"""FastAPI application entrypoint.

Run with:  uvicorn app.main:app --reload
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import algorithms, experiments, processing, results
from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("Ramp Point Cloud Analysis API starting up (viz_max_points=%d)", settings.viz_max_points)
    yield


app = FastAPI(
    title="Ramp Point Cloud Analysis API",
    description="Upload, visualize, process, and compare ramp point clouds.",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(experiments.router)
app.include_router(algorithms.router)
app.include_router(processing.router)
app.include_router(results.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
