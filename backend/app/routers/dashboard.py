from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from uuid import UUID

from app.database import get_db
from app.models import (
    SteamUser, UserGame, Game, UserBacklog, 
    UserAchievement, Achievement, Genre, GameGenre
)
from app.schemas import (
    UserDashboard, UserGameResponse, UserAchievementResponse,
    BacklogCreate, BacklogUpdate, BacklogResponse, GameResponse
)
from app.services.data_service import ComparisonService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats")
def get_global_stats(db: Session = Depends(get_db)):
    """Get global statistics for the platform."""
    total_users = db.query(func.count(SteamUser.id)).scalar()
    total_games = db.query(func.count(Game.id)).scalar()
    total_playtime = db.query(func.sum(UserGame.playtime_forever)).scalar() or 0
    total_achievements = db.query(func.count(UserAchievement.id)).filter(
        UserAchievement.achieved == True
    ).scalar()
    
    from app.models import UserGroup
    total_groups = db.query(func.count(UserGroup.id)).scalar()
    
    return {
        "total_users": total_users,
        "total_groups": total_groups,
        "total_games_tracked": total_games,
        "total_playtime_hours": total_playtime // 60,
        "total_achievements_unlocked": total_achievements
    }


@router.get("/user/{user_id}")
def get_user_dashboard(user_id: UUID, db: Session = Depends(get_db)):
    """Get comprehensive dashboard data for a user."""
    user = db.query(SteamUser).filter(SteamUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get basic stats
    game_stats = db.query(
        func.count(UserGame.id).label("total_games"),
        func.sum(UserGame.playtime_forever).label("total_playtime"),
        func.count(UserGame.id).filter(UserGame.playtime_forever > 0).label("games_played")
    ).filter(UserGame.steam_user_id == user_id).first()
    
    achievement_stats = db.query(
        func.count(UserAchievement.id).label("total"),
        func.count(UserAchievement.id).filter(UserAchievement.achieved == True).label("unlocked")
    ).filter(UserAchievement.steam_user_id == user_id).first()
    
    # Get recent games (last 10 played)
    recent_games = db.query(UserGame).filter(
        UserGame.steam_user_id == user_id,
        UserGame.rtime_last_played.isnot(None)
    ).order_by(
        UserGame.rtime_last_played.desc()
    ).limit(10).all()
    
    recent_game_data = []
    for ug in recent_games:
        game = db.query(Game).filter(Game.id == ug.game_id).first()
        if game:
            recent_game_data.append({
                "game": game,
                "playtime_forever": ug.playtime_forever,
                "playtime_2weeks": ug.playtime_2weeks,
                "last_played": ug.rtime_last_played
            })
    
    # Get top played games
    top_games = db.query(UserGame).filter(
        UserGame.steam_user_id == user_id
    ).order_by(
        UserGame.playtime_forever.desc()
    ).limit(10).all()
    
    top_game_data = []
    for ug in top_games:
        game = db.query(Game).filter(Game.id == ug.game_id).first()
        if game:
            top_game_data.append({
                "game": game,
                "playtime_forever": ug.playtime_forever,
                "playtime_hours": ug.playtime_forever // 60
            })
    
    # Get recent achievements
    recent_achievements = db.query(UserAchievement).filter(
        UserAchievement.steam_user_id == user_id,
        UserAchievement.achieved == True,
        UserAchievement.unlock_time.isnot(None)
    ).order_by(
        UserAchievement.unlock_time.desc()
    ).limit(10).all()
    
    achievement_data = []
    for ua in recent_achievements:
        achievement = db.query(Achievement).filter(
            Achievement.id == ua.achievement_id
        ).first()
        if achievement:
            game = db.query(Game).filter(Game.id == achievement.game_id).first()
            achievement_data.append({
                "achievement": achievement,
                "game": game,
                "unlock_time": ua.unlock_time
            })
    
    # Get genre distribution
    genre_distribution = db.query(
        Genre.name,
        func.sum(UserGame.playtime_forever).label("total_playtime"),
        func.count(UserGame.id).label("game_count")
    ).join(
        GameGenre, Genre.id == GameGenre.genre_id
    ).join(
        Game, GameGenre.game_id == Game.id
    ).join(
        UserGame, Game.id == UserGame.game_id
    ).filter(
        UserGame.steam_user_id == user_id
    ).group_by(Genre.name).order_by(
        desc("total_playtime")
    ).limit(10).all()
    
    # Get backlog summary
    backlog_summary = db.query(
        UserBacklog.status,
        func.count(UserBacklog.id)
    ).filter(
        UserBacklog.steam_user_id == user_id
    ).group_by(UserBacklog.status).all()
    
    return {
        "user": user,
        "stats": {
            "total_games": game_stats.total_games or 0,
            "total_playtime": game_stats.total_playtime or 0,
            "total_playtime_hours": (game_stats.total_playtime or 0) // 60,
            "games_played": game_stats.games_played or 0,
            "games_never_played": (game_stats.total_games or 0) - (game_stats.games_played or 0),
            "total_achievements": achievement_stats.total or 0,
            "achievements_unlocked": achievement_stats.unlocked or 0,
            "completion_rate": (
                (achievement_stats.unlocked / achievement_stats.total * 100) 
                if achievement_stats.total else 0
            )
        },
        "recent_games": recent_game_data,
        "top_played_games": top_game_data,
        "recent_achievements": achievement_data,
        "genre_distribution": [
            {
                "genre": g.name,
                "total_playtime": g.total_playtime or 0,
                "playtime_hours": (g.total_playtime or 0) // 60,
                "game_count": g.game_count
            }
            for g in genre_distribution
        ],
        "backlog_summary": dict(backlog_summary)
    }


@router.get("/user/{user_id}/playtime-by-genre")
def get_playtime_by_genre(user_id: UUID, db: Session = Depends(get_db)):
    """Get detailed playtime breakdown by genre."""
    results = db.query(
        Genre.name,
        func.sum(UserGame.playtime_forever).label("total_playtime"),
        func.count(UserGame.id).label("game_count"),
        func.avg(UserGame.playtime_forever).label("avg_playtime")
    ).join(
        GameGenre, Genre.id == GameGenre.genre_id
    ).join(
        Game, GameGenre.game_id == Game.id
    ).join(
        UserGame, Game.id == UserGame.game_id
    ).filter(
        UserGame.steam_user_id == user_id
    ).group_by(Genre.name).order_by(
        desc("total_playtime")
    ).all()
    
    total_playtime = sum(r.total_playtime or 0 for r in results)
    
    return [
        {
            "genre": r.name,
            "total_playtime_minutes": r.total_playtime or 0,
            "total_playtime_hours": (r.total_playtime or 0) // 60,
            "game_count": r.game_count,
            "avg_playtime_minutes": round(r.avg_playtime or 0, 2),
            "percentage": round((r.total_playtime or 0) / total_playtime * 100, 2) if total_playtime else 0
        }
        for r in results
    ]


@router.get("/compare")
def compare_users(
    user_ids: str = Query(..., description="Comma-separated user IDs"),
    db: Session = Depends(get_db)
):
    """Compare multiple users."""
    ids = [UUID(uid.strip()) for uid in user_ids.split(",")]
    
    if len(ids) < 2:
        raise HTTPException(status_code=400, detail="At least 2 users required for comparison")
    
    comparison_service = ComparisonService(db)
    return comparison_service.compare_users(ids)


# Backlog Management
@router.get("/user/{user_id}/backlog", response_model=List[BacklogResponse])
def get_user_backlog(
    user_id: UUID,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get user's backlog."""
    query = db.query(UserBacklog).filter(UserBacklog.steam_user_id == user_id)
    
    if status:
        query = query.filter(UserBacklog.status == status)
    
    backlog_entries = query.order_by(
        UserBacklog.priority.desc(),
        UserBacklog.created_at.desc()
    ).all()
    
    results = []
    for entry in backlog_entries:
        game = db.query(Game).filter(Game.id == entry.game_id).first()
        if game:
            results.append(BacklogResponse(
                id=entry.id,
                game=game,
                status=entry.status,
                priority=entry.priority,
                notes=entry.notes,
                started_at=entry.started_at,
                completed_at=entry.completed_at,
                created_at=entry.created_at
            ))
    
    return results


@router.post("/user/{user_id}/backlog", response_model=BacklogResponse)
def add_to_backlog(
    user_id: UUID,
    backlog_data: BacklogCreate,
    db: Session = Depends(get_db)
):
    """Add a game to user's backlog."""
    # Check if already in backlog
    existing = db.query(UserBacklog).filter(
        UserBacklog.steam_user_id == user_id,
        UserBacklog.game_id == backlog_data.game_id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Game already in backlog")
    
    game = db.query(Game).filter(Game.id == backlog_data.game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    backlog_entry = UserBacklog(
        steam_user_id=user_id,
        game_id=backlog_data.game_id,
        status=backlog_data.status.value,
        priority=backlog_data.priority,
        notes=backlog_data.notes
    )
    
    db.add(backlog_entry)
    db.commit()
    db.refresh(backlog_entry)
    
    return BacklogResponse(
        id=backlog_entry.id,
        game=game,
        status=backlog_entry.status,
        priority=backlog_entry.priority,
        notes=backlog_entry.notes,
        started_at=backlog_entry.started_at,
        completed_at=backlog_entry.completed_at,
        created_at=backlog_entry.created_at
    )


@router.put("/user/{user_id}/backlog/{backlog_id}", response_model=BacklogResponse)
def update_backlog_entry(
    user_id: UUID,
    backlog_id: UUID,
    backlog_data: BacklogUpdate,
    db: Session = Depends(get_db)
):
    """Update a backlog entry."""
    from datetime import datetime
    
    entry = db.query(UserBacklog).filter(
        UserBacklog.id == backlog_id,
        UserBacklog.steam_user_id == user_id
    ).first()
    
    if not entry:
        raise HTTPException(status_code=404, detail="Backlog entry not found")
    
    if backlog_data.status:
        old_status = entry.status
        entry.status = backlog_data.status.value
        
        # Track status changes
        if backlog_data.status.value == "playing" and old_status != "playing":
            entry.started_at = datetime.utcnow()
        elif backlog_data.status.value == "completed":
            entry.completed_at = datetime.utcnow()
    
    if backlog_data.priority is not None:
        entry.priority = backlog_data.priority
    
    if backlog_data.notes is not None:
        entry.notes = backlog_data.notes
    
    db.commit()
    db.refresh(entry)
    
    game = db.query(Game).filter(Game.id == entry.game_id).first()
    
    return BacklogResponse(
        id=entry.id,
        game=game,
        status=entry.status,
        priority=entry.priority,
        notes=entry.notes,
        started_at=entry.started_at,
        completed_at=entry.completed_at,
        created_at=entry.created_at
    )


@router.delete("/user/{user_id}/backlog/{backlog_id}")
def remove_from_backlog(
    user_id: UUID,
    backlog_id: UUID,
    db: Session = Depends(get_db)
):
    """Remove a game from backlog."""
    entry = db.query(UserBacklog).filter(
        UserBacklog.id == backlog_id,
        UserBacklog.steam_user_id == user_id
    ).first()
    
    if not entry:
        raise HTTPException(status_code=404, detail="Backlog entry not found")
    
    db.delete(entry)
    db.commit()
    
    return {"message": "Removed from backlog"}
