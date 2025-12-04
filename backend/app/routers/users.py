from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.database import get_db
from app.models import SteamUser, UserGame, Game
from app.schemas import (
    SteamUserCreate, SteamUserResponse, SteamUserWithStats,
    UserGameResponse, SyncHistoryResponse
)
from app.services.data_service import DataSyncService

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/", response_model=SteamUserResponse)
async def create_or_sync_user(
    user_data: SteamUserCreate,
    db: Session = Depends(get_db)
):
    """Create a new user or sync existing user from Steam."""
    sync_service = DataSyncService(db)
    user = await sync_service.sync_user_profile(user_data.steam_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="Steam user not found")
    
    return user


@router.get("/", response_model=List[SteamUserWithStats])
def get_all_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all users with their stats."""
    from sqlalchemy import func
    from app.models import UserAchievement
    
    users = db.query(SteamUser).offset(skip).limit(limit).all()
    
    result = []
    for user in users:
        # Calculate stats for each user
        stats = db.query(
            func.count(UserGame.id).label("total_games"),
            func.sum(UserGame.playtime_forever).label("total_playtime"),
            func.count(UserGame.id).filter(UserGame.playtime_forever > 0).label("games_played")
        ).filter(UserGame.steam_user_id == user.id).first()
        
        achievement_count = db.query(func.count(UserAchievement.id)).filter(
            UserAchievement.steam_user_id == user.id,
            UserAchievement.achieved == True
        ).scalar()
        
        result.append(SteamUserWithStats(
            **{c.name: getattr(user, c.name) for c in user.__table__.columns},
            total_games=stats.total_games or 0,
            total_playtime=stats.total_playtime or 0,
            total_achievements=achievement_count or 0,
            games_played=stats.games_played or 0
        ))
    
    return result


@router.get("/{user_id}", response_model=SteamUserWithStats)
def get_user(user_id: UUID, db: Session = Depends(get_db)):
    """Get user by ID with stats."""
    user = db.query(SteamUser).filter(SteamUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Calculate stats
    from sqlalchemy import func
    stats = db.query(
        func.count(UserGame.id).label("total_games"),
        func.sum(UserGame.playtime_forever).label("total_playtime"),
        func.count(UserGame.id).filter(UserGame.playtime_forever > 0).label("games_played")
    ).filter(UserGame.steam_user_id == user_id).first()
    
    from app.models import UserAchievement
    achievement_count = db.query(func.count(UserAchievement.id)).filter(
        UserAchievement.steam_user_id == user_id,
        UserAchievement.achieved == True
    ).scalar()
    
    return SteamUserWithStats(
        **{c.name: getattr(user, c.name) for c in user.__table__.columns},
        total_games=stats.total_games or 0,
        total_playtime=stats.total_playtime or 0,
        total_achievements=achievement_count or 0,
        games_played=stats.games_played or 0
    )


@router.get("/steam/{steam_id}", response_model=SteamUserResponse)
def get_user_by_steam_id(steam_id: str, db: Session = Depends(get_db)):
    """Get user by Steam ID."""
    user = db.query(SteamUser).filter(SteamUser.steam_id == steam_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/{user_id}/sync/profile", response_model=SteamUserResponse)
async def sync_user_profile(user_id: UUID, db: Session = Depends(get_db)):
    """Sync user profile from Steam API."""
    user = db.query(SteamUser).filter(SteamUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    sync_service = DataSyncService(db)
    updated_user = await sync_service.sync_user_profile(user.steam_id)
    return updated_user


@router.post("/{user_id}/sync/games")
async def sync_user_games(user_id: UUID, db: Session = Depends(get_db)):
    """Sync user's game library from Steam API."""
    user = db.query(SteamUser).filter(SteamUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    sync_service = DataSyncService(db)
    games_synced, playtime_updated = await sync_service.sync_user_games(user.steam_id)
    
    return {
        "message": "Games synced successfully",
        "games_synced": games_synced,
        "playtime_updated": playtime_updated
    }


@router.post("/{user_id}/sync/achievements")
async def sync_user_all_achievements(
    user_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Sync all achievements for user (runs in background)."""
    user = db.query(SteamUser).filter(SteamUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    sync_service = DataSyncService(db)
    
    # Run in background due to potentially long duration
    background_tasks.add_task(sync_service.sync_all_user_achievements, user.steam_id)
    
    return {"message": "Achievement sync started in background"}


@router.get("/{user_id}/games", response_model=List[UserGameResponse])
def get_user_games(
    user_id: UUID,
    skip: int = 0,
    limit: int = 100,
    sort_by: str = Query("playtime_forever", enum=["playtime_forever", "name", "rtime_last_played"]),
    db: Session = Depends(get_db)
):
    """Get user's games."""
    query = db.query(UserGame).filter(UserGame.steam_user_id == user_id)
    
    if sort_by == "playtime_forever":
        query = query.order_by(UserGame.playtime_forever.desc())
    elif sort_by == "rtime_last_played":
        query = query.order_by(UserGame.rtime_last_played.desc())
    
    user_games = query.offset(skip).limit(limit).all()
    
    # Load game info
    results = []
    for ug in user_games:
        game = db.query(Game).filter(Game.id == ug.game_id).first()
        if game:
            results.append(UserGameResponse(
                id=ug.id,
                playtime_forever=ug.playtime_forever,
                playtime_2weeks=ug.playtime_2weeks,
                rtime_last_played=ug.rtime_last_played,
                created_at=ug.created_at,
                game=game
            ))
    
    return results


@router.get("/{user_id}/sync-history", response_model=List[SyncHistoryResponse])
def get_sync_history(
    user_id: UUID,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Get user's sync history."""
    from app.models import SyncHistory
    
    history = db.query(SyncHistory).filter(
        SyncHistory.steam_user_id == user_id
    ).order_by(SyncHistory.created_at.desc()).limit(limit).all()
    
    return history


@router.delete("/{user_id}")
def delete_user(user_id: UUID, db: Session = Depends(get_db)):
    """Delete a user."""
    user = db.query(SteamUser).filter(SteamUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.delete(user)
    db.commit()
    
    return {"message": "User deleted successfully"}
