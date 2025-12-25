from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes import contracts

settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title="Influract API",
    description="Contract analyzer for content creators - Turn legal jargon into actionable insights",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:3000",
        "http://localhost:3001",
    ],
    allow_credentials=True,
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
