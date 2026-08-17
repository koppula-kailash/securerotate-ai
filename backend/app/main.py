"""
SecureRotate AI - FastAPI Main Application Entry Point
Phase 1 Foundation: MySQL Connection, Modular API Routing, CORS, Health Checks, and Static React SPA Hosting.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import settings
from app.db.init_db import init_db
from app.scheduler.jobs import start_scheduler, shutdown_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI application lifespan managing database initialization and background scheduler."""
    await init_db()
    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure CORS for local React development (http://localhost:5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# Global Exception Handler - Sanitizes all uncaught errors to prevent secret leakage
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred."},
    )


# Serve Static React Application at Root '/' and '/app'
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "static"))
index_html_path = os.path.join(static_dir, "index.html")

if os.path.exists(index_html_path):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/", include_in_schema=False)
    @app.get("/app", include_in_schema=False)
    async def serve_spa():
        response = FileResponse(index_html_path)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response


@app.get("/health", tags=["Health"], include_in_schema=False)
async def root_health():
    return {"status": "healthy", "service": settings.PROJECT_NAME}


# Include API v1 Router (/api/v1)
app.include_router(api_router, prefix=settings.API_V1_STR)

