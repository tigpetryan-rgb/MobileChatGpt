from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.approval_routes import router as approval_router
from app.api.device_routes import router as device_router
from app.api.routes import router
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine
from app.mcp.server import project_brain_mcp


# Build the mounted transport once so the parent lifespan manages the exact
# session manager used by the ASGI app. Stateless HTTP keeps auth context
# request-scoped for both modern and legacy clients.
mcp_http_app = project_brain_mcp.streamable_http_app(stateless_http=True)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Keeps the skeleton runnable immediately. Production uses Alembic migrations.
    Base.metadata.create_all(bind=engine)
    # Mounted ASGI sub-app lifespans are not entered by FastAPI/Starlette, so the
    # parent app owns the MCP session manager lifecycle.
    async with project_brain_mcp.session_manager.run():
        yield


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="0.5.0", lifespan=lifespan)
    app.include_router(router)
    app.include_router(device_router)
    app.include_router(approval_router)

    # Mount last so the existing Project Brain HTTP API and docs routes retain
    # precedence while the MCP sub-app serves its standard /mcp endpoint.
    app.mount("/", mcp_http_app)
    return app


app = create_app()
