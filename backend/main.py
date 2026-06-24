"""
RESTful Prompt restructing app


"""

import os
import sys
from pathlib import Path

# Add the directory containing this file to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from redis import asyncio as aioredis
from prometheus_fastapi_instrumentator import Instrumentator

# internal imports
from routers import prompt
from core.config import settings
from core.middleware import register_middleware
from core.custom_error_handlers import register_all_errors

from utility.logger import get_logger

lg = get_logger(script_path=__file__)
SQLALCHEMY_DATABASE_URL = f"postgresql://{settings.DATABASE_USERNAME}:{settings.DATABASE_PASSWORD}@{settings.DATABASE_HOSTNAME}:{settings.DATABASE_PORT}/{settings.DATABASE_NAME}"
REDIS_URL = settings.REDIS_URL

STATIC_FRONTEND_DIR = Path(os.path.dirname(os.path.abspath(__file__))) / "static"
TEMPLATES_DIR = STATIC_FRONTEND_DIR / "sqladmin"


# our app
description = """
    A RESTful API for a AI prompt restructing system.

    ## Prompts
    * You can **create**, **read**, **update**, and **delete** prompts.

    ## Users
    * **Create** and **Login** users (JWT Auth).
    * **Password Reset** and **Email Verification**.

"""
version = settings.VERSION or "v1.1"

tags_metadata = [
    {
        "name": "prompts",
        "description": "Operations with prompts. The **CORE** logic of the app.",
    },
    {
        "name": "user",
        "description": "Manages users and their authentication.",
    },
]

app = FastAPI(
    title="PromptCrafter Backend API",
    description=description,
    version=settings.VERSION or version,
    contact={
        "name": "Fraol Bulti",
        "url": "https://github.com/FIBA00",
        "email": "fraolbulti0@gmail.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_tags=tags_metadata,
    openapi_url=f"/api/{settings.VERSION or version}/openapi.json",
    docs_url=f"/api/{settings.VERSION or version}/docs",
    redoc_url=f"/api/{settings.VERSION or version}/redoc",
)

# Use lifespan instead of deprecated startup event


@asynccontextmanager
async def lifespan(app: FastAPI):
    redis = aioredis.from_url(
        settings.REDIS_URL, encoding="utf8", decode_responses=True
    )
    # FastAPICache disabled (not installed)
    # FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")
    try:
        yield
    finally:
        try:
            await redis.close()
            await redis.wait_closed()
        except Exception:
            pass


app.router.lifespan_context = lifespan


# --- Global Exception Handling ---

register_all_errors(app=app)
register_middleware(app)

# Metrics
Instrumentator().instrument(app).expose(app)

app.include_router(
    router=prompt.router, prefix=f"/api/{settings.VERSION or version}", tags=["prompts"]
)


app.mount(
    path="/",
    app=StaticFiles(directory=STATIC_FRONTEND_DIR, html=True),
    name="frontend",
)
