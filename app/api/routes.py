
from fastapi import APIRouter

router = APIRouter(
    prefix="/api/v1",
    tags=["General"],
)


@router.get("/")
def root():
    return {
        "message": "Welcome to Document AI!",
        "status": "running",
    }


@router.get("/health")
def health_check():
    return {
        "status": "healthy",
    }
