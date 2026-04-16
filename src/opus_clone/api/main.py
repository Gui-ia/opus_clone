from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from opus_clone.config import get_settings
from opus_clone.db import dispose_engine, get_engine
from opus_clone.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    # Eagerly create engine to verify connection params
    get_engine()
    yield
    await dispose_engine()


app = FastAPI(
    title="Opus Clone API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Routes
from opus_clone.api.channels import router as channels_router  # noqa: E402
from opus_clone.api.clips import router as clips_router  # noqa: E402
from opus_clone.api.health import router as health_router  # noqa: E402
from opus_clone.api.videos import router as videos_router  # noqa: E402
from opus_clone.api.webhooks import router as webhooks_router  # noqa: E402

app.include_router(health_router)
app.include_router(channels_router)
app.include_router(videos_router)
app.include_router(clips_router)
app.include_router(webhooks_router)
