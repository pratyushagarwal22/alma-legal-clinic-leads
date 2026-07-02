from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness/readiness probe used for container health gating."""
    return {"status": "ok"}
