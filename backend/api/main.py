"""Main FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import get_settings
from api.db.database import init_db

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown."""
    # Startup
    print("Starting Jira Feedback API...")
    init_db()
    print("Database initialized")

    # Setup Telegram bot webhook if configured
    if settings.telegram_bot_token and settings.telegram_webhook_url:
        try:
            from api.telegram.bot import setup_webhook, get_bot
            await setup_webhook()
            # Initialize the bot application for webhook mode
            bot = get_bot()
            await bot.initialize()
            print("Telegram webhook configured and application initialized")
        except Exception as e:
            print(f"Failed to setup Telegram webhook: {e}")

    yield

    # Shutdown
    print("Shutting down Jira Feedback API...")

    # Cleanup Telegram bot application
    if settings.telegram_bot_token:
        try:
            from api.telegram.bot import get_bot
            bot = get_bot()
            if bot.bot:
                await bot.bot.shutdown()
            if bot.application:
                await bot.application.shutdown()
            print("Telegram bot application shutdown complete")
        except Exception as e:
            print(f"Error during Telegram bot shutdown: {e}")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="API for DSPy-powered Jira issue analysis and feedback",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": settings.app_name}


# Include routers
from api.auth.router import router as auth_router
from api.issues.router import router as issues_router
from api.feedback.router import router as feedback_router
from api.rubrics.router import router as rubrics_router

app.include_router(auth_router, prefix="/api/v1")
app.include_router(issues_router, prefix="/api/v1")
app.include_router(feedback_router, prefix="/api/v1")
app.include_router(rubrics_router, prefix="/api/v1")

# Telegram and WebSocket routers
from api.telegram.router import router as telegram_router
from api.websocket.router import router as ws_router

app.include_router(telegram_router, prefix="/api/v1")
app.include_router(ws_router, prefix="/api/v1")


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }
