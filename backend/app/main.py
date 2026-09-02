from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.device_routes import router as device_router
from app.api.routes import router
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Keeps the skeleton runnable immediately. Production uses Alembic migrations.
    Base.metadata.create_all(bind=engine)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="0.4.0", lifespan=lifespan)
    app.include_router(router)
    app.include_router(device_router)
    return app


app = create_app()
