import time
import logging

from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from utility.logger import get_logger


# to disable the uvicorn logs
logger = logging.getLogger("uvicorn.access")
logger.disabled = True

lg = get_logger(__file__)


def register_middleware(app: FastAPI):
    # our middle wares
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[
            "localhost",
            "127.0.0.1",
            "testserver",
            "*.southafricanorth.cloudapp.azure.com",
            "*.promptcrafter.com",
            "www.promptcrafter.com",
        ],
    )
