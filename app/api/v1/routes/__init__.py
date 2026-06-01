"""v1 routes package exports."""

from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.chat import router as legal_router
from app.api.v1.routes.document import router as document_router
from app.api.v1.routes.tools import router as analysis_router
from app.api.v1.routes.legal_tools import router as legal_tools_router
from app.api.v1.routes.auth import router as auth_router

__all__ = [
    "auth_router",
    "health_router",
    "legal_router",
    "document_router",
    "analysis_router",
    "legal_tools_router",
]
