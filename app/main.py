
from fastapi import FastAPI

app = FastAPI(
    title="Document AI",
    description="AI-powered document processing application",
    version="0.1.0",
)


@app.get("/")
def root():
    return {
        "message": "Welcome to Document AI!",
        "status": "running",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
    }
