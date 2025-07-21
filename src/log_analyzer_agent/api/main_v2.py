"""FastAPI application for log analyzer agent with multi-tenant support."""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ..services.better_auth import BetterAuth
from ..model_pool import get_model_pool, cleanup_model_pool
from .middleware import TenantMiddleware
from .routes import router
from .auth_routes import auth_router
try:
    from .streaming_routes_fixed import router as streaming_router
except ImportError:
    try:
        from .streaming_routes_enhanced import router as streaming_router
    except ImportError:
        from .streaming_routes import router as streaming_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI app."""
    # Initialize model pool on startup
    try:
        model_pool = await get_model_pool()
        print("✅ Model pool initialized successfully")
    except Exception as e:
        print(f"❌ Error initializing model pool: {e}")
    
    # Setup database tables on startup
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL environment variable is required. Please set it in your .env file.")
    auth_service = BetterAuth(db_url)

    try:
        await auth_service.setup_database()
        print("✅ Database tables set up successfully")
    except Exception as e:
        print(f"❌ Error setting up database tables: {e}")

    yield

    # Cleanup on shutdown
    print("🧹 Cleaning up...")
    
    try:
        await cleanup_model_pool()
        print("✅ Model pool cleaned up successfully")
    except Exception as e:
        print(f"❌ Error cleaning up model pool: {e}")


# Create FastAPI app
app = FastAPI(
    title="Log Analyzer Agent API",
    description="Multi-tenant API for analyzing log files using LangGraph",
    version="2.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add tenant middleware
app.add_middleware(TenantMiddleware)

# Include routes
app.include_router(auth_router, prefix="/api/v2/auth", tags=["Authentication"])
app.include_router(router, prefix="/api/v2", tags=["Log Analysis"])
app.include_router(streaming_router, prefix="/api/v2", tags=["Streaming"])


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "HTTP_ERROR", "message": str(exc.detail)},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    import traceback
    print(f"Unhandled exception: {exc}")
    traceback.print_exc()
    
    return JSONResponse(
        status_code=500,
        content={"error": "INTERNAL_ERROR", "message": "An internal error occurred"},
    )


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Log Analyzer Agent API", 
        "version": "2.0.0", 
        "docs": "/docs",
        "features": ["multi-tenant", "better-auth", "api-keys"]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "log-analyzer-api"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)