from fastapi import APIRouter

v1_router = APIRouter(prefix="/api/v1", tags=["API v1"])

@v1_router.get("/health")
async def health_v1():
    return {"version": "1.0", "status": "healthy"}

@v1_router.get("/info")
async def info_v1():
    return {"api_version": "v1", "deprecated": False}
