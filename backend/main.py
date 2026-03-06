"""Main FastAPI application.

This module configures the FastAPI application with middleware, exception handlers,
routers, and WebSocket endpoints.

Key features:
- Automatic request/response compression
- CORS middleware for cross-origin requests
- Comprehensive exception handling
- WebSocket support for real-time updates
- Database initialization on startup

Example:
    >>> import uvicorn
    >>> uvicorn.run("backend.main:app", host="0.0.0.0", port=8000)
"""

import logging
import traceback
from fastapi import FastAPI, WebSocket, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.core.database import init_db
from backend.core.config import settings
from backend.core.exceptions import CycleMonitorException
from backend.middleware.compression import (
    setup_compression_from_config,
    CompressionMonitoringMiddleware,
)
from backend.ws.websocket import handle_websocket
from config.constants import (
    API_COMPRESSION_MIN_SIZE,
    API_COMPRESSION_LEVEL,
)


# Configure logging
logging.basicConfig(
    level=settings.log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    # Startup
    logger.info("Initializing database...")
    init_db()
    logger.info("Application started")

    yield

    # Shutdown
    logger.info("Application shutting down...")


# Create FastAPI app
app = FastAPI(
    title="Cycle Time Monitoring System",
    description="Real-time monitoring and alerting for equipment cycle times",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan
)

# Add compression middleware (MUST be first to wrap other middleware)
logger.info("Setting up compression middleware...")
setup_compression_from_config(app, config_name="balanced")

# Add compression monitoring middleware for metrics
app.add_middleware(CompressionMonitoringMiddleware)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:3000",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Global Exception Handlers
# ============================================================================

@app.exception_handler(CycleMonitorException)
async def cycle_monitor_exception_handler(request: Request, exc: CycleMonitorException):
    """Handle custom application exceptions."""
    logger.warning(
        f"CycleMonitorException: {exc.error_code} - {exc.message}",
        extra={"path": request.url.path, "details": exc.details}
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict()
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle Starlette HTTP exceptions."""
    logger.warning(
        f"HTTPException: {exc.status_code} - {exc.detail}",
        extra={"path": request.url.path}
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": "HTTP_ERROR",
                "message": str(exc.detail)
            }
        }
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle ValueError exceptions."""
    logger.error(
        f"ValueError: {str(exc)}",
        extra={"path": request.url.path, "traceback": traceback.format_exc()}
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALUE_ERROR",
                "message": "Invalid input value"
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all uncaught exceptions."""
    logger.error(
        f"Unhandled exception: {str(exc)}",
        extra={
            "path": request.url.path,
            "exception_type": type(exc).__name__,
            "traceback": traceback.format_exc()
        }
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred. Please try again later."
            }
        }
    )


# Import routers
from backend.routers import equipments, product_types, cycle_configs, timeseries, cycles, alerts

# Include routers
app.include_router(equipments.router, prefix="/api", tags=["Equipments"])
app.include_router(product_types.router, prefix="/api", tags=["Product Types"])
app.include_router(cycle_configs.router, prefix="/api", tags=["Cycle Configurations"])
app.include_router(timeseries.router, prefix="/api", tags=["Timeseries"])
app.include_router(cycles.router, prefix="/api", tags=["Cycles"])
app.include_router(alerts.router, prefix="/api", tags=["Alerts"])


@app.get("/")
def read_root():
    """Root endpoint."""
    return {
        "message": "Cycle Time Monitoring System API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running"
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.websocket("/ws/realtime")
async def websocket_realtime(websocket: WebSocket):
    """WebSocket endpoint for real-time updates (global stream)."""
    await handle_websocket(websocket, equipment_id=None)


@app.websocket("/ws/equipment/{equipment_id}")
async def websocket_equipment(websocket: WebSocket, equipment_id: int):
    """WebSocket endpoint for equipment-specific real-time updates."""
    await handle_websocket(websocket, equipment_id=equipment_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
