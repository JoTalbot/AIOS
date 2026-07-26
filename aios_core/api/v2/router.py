from fastapi import APIRouter

v2_router = APIRouter(prefix="/api/v2", tags=["API v2"])

@v2_router.get("/health")
async def health_v2():
    return {"version": "2.0", "status": "healthy", "features": ["graphql", "ab_testing"]}

@v2_router.get("/info")
async def info_v2():
    return {"api_version": "v2", "deprecated": False, "changelog": "Added GraphQL, A/B testing"}
