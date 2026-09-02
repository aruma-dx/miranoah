from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers.auth import router as auth_router
from app.routers.dashboard import router as dashboard_router
from app.routers.health import router as health_router
from app.routers.permissions import router as permissions_router
from app.routers.projects import router as projects_router
from app.routers.slack import router as slack_router
from app.routers.tasks import router as tasks_router


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.app_base_url
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    health_router
)

app.include_router(
    auth_router
)

app.include_router(
    slack_router
)

app.include_router(
    projects_router
)

app.include_router(
    tasks_router
)

app.include_router(
    dashboard_router
)

app.include_router(
    permissions_router
)


@app.get("/")
def root():
    return {
        "name": "MIRANOAH",
        "tagline": (
            "すべてを見渡し、"
            "一つも取りこぼさない。"
        ),
    }
