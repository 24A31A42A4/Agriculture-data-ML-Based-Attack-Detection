"""
FastAPI application factory with lifespan management.

Creates the main application instance with:
- Startup: Database connection, Redis pool, ML model loading, logging
- Shutdown: Graceful cleanup of all connections
- Exception handlers for custom exceptions
- CORS middleware
- API router mounting
"""

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.models.base import Base
from app.database.session import engine

from app.config import get_settings
from app.core.exceptions import (
    AgriIoTError,
    AuthenticationError,
    AuthorizationError,
    DeviceBlockedError,
    DeviceNotFoundError,
    DeviceNotWhitelistedError,
    RateLimitExceededError,
    ReplayAttackError,
    SecurityGatewayError,
    SignatureVerificationError,
    TimestampExpiredError,
)
from app.core.logging import get_logger, setup_logging
from app.database.redis import close_redis_pool

logger = get_logger(__name__)


# ─── Lifespan ────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown lifecycle."""
    settings = get_settings()

    # ── Startup ──
    setup_logging()
    logger.info(
        "Starting %s v%s",
        settings.app_name,
        settings.app_version,
        extra={"debug": settings.debug},
    )

    # Ensure key vault directory exists
    settings.key_vault_dir.mkdir(parents=True, exist_ok=True)

    # Ensure ML models directory exists
    settings.ml_models_dir.mkdir(parents=True, exist_ok=True)

    # Create tables
    import app.models  # Ensure models are loaded
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Application startup complete")

    yield

    # ── Shutdown ──
    logger.info("Shutting down application...")
    await close_redis_pool()
    logger.info("Application shutdown complete")


# ─── App Factory ─────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Blockchain-Enabled Lightweight Security Framework with Machine "
            "Learning for Smart Agriculture IoT Networks.\n\n"
            "Research-grade API providing multi-layer IoT security, "
            "ML-based intrusion detection (13 models), lightweight blockchain "
            "audit trail, dynamic trust scoring, and comprehensive evaluation."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── CORS ──
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.debug else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── API Router ──
    from app.api.v1.router import router as api_v1_router
    app.include_router(api_v1_router)

    # ── Exception Handlers ──
    _register_exception_handlers(app)

    # ── Root Health Check ──
    @app.get("/health", tags=["System"])
    async def health_check():
        """Application health check endpoint."""
        return {
            "status": "healthy",
            "app": settings.app_name,
            "version": settings.app_version,
        }

    return app


# ─── Exception Handlers ─────────────────────────────────────────────────────

def _register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers for custom exceptions."""

    @app.exception_handler(AuthenticationError)
    async def auth_error_handler(request: Request, exc: AuthenticationError):
        return JSONResponse(
            status_code=401,
            content={"error": "authentication_error", "message": exc.message},
        )

    @app.exception_handler(AuthorizationError)
    async def authz_error_handler(request: Request, exc: AuthorizationError):
        return JSONResponse(
            status_code=403,
            content={"error": "authorization_error", "message": exc.message},
        )

    @app.exception_handler(DeviceNotFoundError)
    async def device_not_found_handler(request: Request, exc: DeviceNotFoundError):
        return JSONResponse(
            status_code=404,
            content={"error": "device_not_found", "message": exc.message},
        )

    @app.exception_handler(DeviceNotWhitelistedError)
    async def device_not_whitelisted_handler(
        request: Request, exc: DeviceNotWhitelistedError
    ):
        return JSONResponse(
            status_code=403,
            content={"error": "device_not_whitelisted", "message": exc.message},
        )

    @app.exception_handler(DeviceBlockedError)
    async def device_blocked_handler(request: Request, exc: DeviceBlockedError):
        return JSONResponse(
            status_code=403,
            content={"error": "device_blocked", "message": exc.message},
        )

    @app.exception_handler(ReplayAttackError)
    async def replay_attack_handler(request: Request, exc: ReplayAttackError):
        return JSONResponse(
            status_code=409,
            content={"error": "replay_attack", "message": exc.message},
        )

    @app.exception_handler(TimestampExpiredError)
    async def timestamp_expired_handler(request: Request, exc: TimestampExpiredError):
        return JSONResponse(
            status_code=408,
            content={"error": "timestamp_expired", "message": exc.message},
        )

    @app.exception_handler(RateLimitExceededError)
    async def rate_limit_handler(request: Request, exc: RateLimitExceededError):
        return JSONResponse(
            status_code=429,
            content={"error": "rate_limit_exceeded", "message": exc.message},
        )

    @app.exception_handler(SignatureVerificationError)
    async def signature_error_handler(
        request: Request, exc: SignatureVerificationError
    ):
        return JSONResponse(
            status_code=401,
            content={"error": "signature_invalid", "message": exc.message},
        )

    @app.exception_handler(SecurityGatewayError)
    async def gateway_error_handler(request: Request, exc: SecurityGatewayError):
        return JSONResponse(
            status_code=400,
            content={"error": "security_gateway_error", "message": exc.message},
        )

    @app.exception_handler(AgriIoTError)
    async def generic_error_handler(request: Request, exc: AgriIoTError):
        logger.error("Unhandled AgriIoTError: %s", exc.message, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "internal_error", "message": exc.message},
        )


# ─── Application Instance ───────────────────────────────────────────────────

app = create_app()
