
from fastapi import FastAPI

from app.api.routes import router
from app.core.config import settings


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered document processing application",
    debug=settings.debug,
)

app.include_router(
    router,
    prefix=settings.api_v1_prefix,
)
