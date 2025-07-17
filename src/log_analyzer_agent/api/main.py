"""FastAPI application for log analyzer agent."""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ..services.auth_service import AuthService
from .routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI app."""
    # Setup database tables on startup
    db_url = os.getenv("DATABASE_URL", "postgresql://loganalyzer:password@localhost:5432/loganalyzer")
    auth_service = AuthService(db_url)
    
    try:
        await auth_service.setup_tables()
        print("Database tables set up successfully")
    except Exception as e:
        print(f"Error setting up database tables: {e}")
    
    yield
    
    # Cleanup on shutdown
    try:
        await auth_service.cleanup_expired_sessions()
        print("Cleaned up expired sessions")
    except Exception as e:
        print(f"Error cleaning up expired sessions: {e}")


# Create FastAPI app
app = FastAPI(
    title="Log Analyzer Agent API",
    description="API for analyzing log files using LangGraph with memory",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router, prefix="/api/v1")


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "HTTP_ERROR", "message": str(exc.detail)}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    return JSONResponse(
        status_code=500,
        content={"error": "INTERNAL_ERROR", "message": "An internal error occurred"}
    )


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Log Analyzer Agent API",
        "version": "1.0.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)