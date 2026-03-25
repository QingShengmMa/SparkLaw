"""v1 route compatibility exports."""

from app.routers.health import router as health_router
from app.routers.legal import router as legal_router
from app.routers.document import router as document_router
from app.routers.analysis import router as analysis_router

__all__ = ["health_router", "legal_router", "document_router", "analysis_router"]
