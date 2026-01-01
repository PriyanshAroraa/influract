from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.routes import contracts

settings = get_settings()

# Initialize rate limiter - uses IP address for tracking
limiter = Limiter(key_func=get_remote_address)

# Create FastAPI app
app = FastAPI(
    title="Influract API",
    description="Contract analyzer for content creators - Turn legal jargon into actionable insights",
    version="1.0.0"
)

# Add limiter to app state
app.state.limiter = limiter


# Custom rate limit exceeded handler with friendly message
@app.exception_handler(RateLimitExceeded)
async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": "Whoa there, speed racer! 🏎️ Our servers are working hard. Please try again in a bit!",
            "detail": "You've hit your limit of 10 contract analyses per hour. Grab a coffee ☕ and we'll be ready for you soon!",
            "retry_after": "1 hour"
        },
        headers={
            "Access-Control-Allow-Origin": "*",
            "Retry-After": "3600"
        }
    )


# CORS middleware - allow all origins for serverless
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(contracts.router, prefix="/api/contracts", tags=["Contracts"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Influract API - Contract Analyzer for Creators",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# Handle OPTIONS preflight requests
@app.options("/{path:path}")
async def options_handler(request: Request):
    return JSONResponse(
        content={},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        }
    )

