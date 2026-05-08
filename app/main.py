import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.v1.endpoints import router as v1_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    yield
    logger.info("Shutting down Sovereign Brain")


app = FastAPI(
    title="AI Automation Systems (PTY) LTD — Sovereign Brain",
    description=(
        "Secure backend API connecting the Lovable frontend to the Groq AI engine "
        "with POPIA-compliant data privacy, RAG via Supabase pgvector, "
        "and n8n/Evolution API webhook orchestration."
    ),
    version=settings.app_version,
    lifespan=lifespan,
    contact={
        "name": "AI Automation Systems (PTY) LTD",
        "url": "https://ai-automationsystems.co.za",
    },
)

cors_kwargs = dict(
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
if settings.cors_origin_list:
    cors_kwargs["allow_origins"] = settings.cors_origin_list
if settings.cors_origin_regex:
    cors_kwargs["allow_origin_regex"] = settings.cors_origin_regex

app.add_middleware(CORSMiddleware, **cors_kwargs)


@app.middleware("http")
async def aigos_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-AIGOS-Version"] = settings.app_version
    response.headers["X-AIGOS-Provider"] = "AI Automation Systems (PTY) LTD"
    response.headers["X-POPIA-Compliant"] = "true"
    return response


app.include_router(v1_router)


@app.get("/")
async def root():
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "operational",
    }
