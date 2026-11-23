
from fastapi import FastAPI

from app.api.routes import router

app = FastAPI(
    title="Document AI",
    description="AI-powered document processing application",
    version="0.1.0",
)

app.include_router(router)
