
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.api.documents import router as documents_router
from app.core.config import settings
from app.db.database import initialize_database
from fastapi.middleware.cors import CORSMiddleware

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

# --------------------------------------------------
# Frontend cross-origin access
# --------------------------------------------------

# Allow the configured frontend origins to communicate
# with this backend during development and deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)
