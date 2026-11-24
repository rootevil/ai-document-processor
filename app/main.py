
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.api.documents import router as documents_router
from app.core.config import settings
from app.db.database import initialize_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered document processing application",
    debug=settings.debug,
    lifespan=lifespan,
)

app.include_router(
    router,
    prefix=settings.api_v1_prefix,
)

app.include_router(
    documents_router,
    prefix=settings.api_v1_prefix,
)
