from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.routes import contracts

settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title="Influract API",
    description="Contract analyzer for content creators - Turn legal jargon into actionable insights",
    version="1.0.0"
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
