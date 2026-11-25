from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.modules.auth_rbac.router import router as auth_router
from app.modules.auth_rbac.seed import seed_auth_data
from app.modules.simulation.engine import seed_simulation_data
from app.modules.simulation.router import router as simulation_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncSessionLocal() as session:
        await seed_auth_data(session)
        await seed_simulation_data(session)
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["System"])
async def health_check() -> dict[str, str | bool]:
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.app_env,
        "simulation_mode": settings.simulation_mode,
    }


app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(simulation_router, prefix=settings.api_prefix)