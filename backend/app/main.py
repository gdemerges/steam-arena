from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.database import engine, Base
from app.routers import users, groups, games, dashboard, ml, playtime_tracking


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting Steam Arena API...")
    # Create tables if they don't exist (for development)
    # In production, use Alembic migrations
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown
    print("Shutting down Steam Arena API...")


app = FastAPI(
    title="Steam Arena API",
    description="""
    Steam Arena - Social Gaming Analytics Platform
    
    ## Features
    
    - **User Management**: Add and sync Steam users
    - **Group Management**: Create groups of Steam friends for comparison
    - **Dashboard**: Social comparison of gaming stats
    - **Game Analytics**: Track playtime, achievements, and backlog
    - **ML Features**: Player clustering and game recommendations
    
    ## Steam API
    
    This API integrates with the Steam Web API to fetch:
    - Player profiles
    - Game libraries
    - Achievements
    - Playtime statistics
    """,
    version="1.0.0",
    lifespan=lifespan,
    redirect_slashes=False
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)

# Include routers
app.include_router(users.router, prefix="/api/v1")
app.include_router(groups.router, prefix="/api/v1")
app.include_router(games.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(ml.router, prefix="/api/v1")
app.include_router(playtime_tracking.router, prefix="/api/v1")


@app.get("/")
def root():
    return {
        "name": "Steam Arena API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/api/v1")
def api_info():
    return {
        "version": "1.0.0",
        "endpoints": {
            "users": "/api/v1/users",
            "groups": "/api/v1/groups",
            "games": "/api/v1/games",
            "dashboard": "/api/v1/dashboard",
            "ml": "/api/v1/ml",
            "playtime_tracking": "/api/v1/playtime-tracking"
        }
    }
