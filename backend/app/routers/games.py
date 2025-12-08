from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from uuid import UUID

from app.database import get_db
from app.models import Game, Genre, GameGenre, UserGame
from app.schemas import GameResponse, GameWithGenres, GenreResponse
from app.services.data_service import DataSyncService

router = APIRouter(prefix="/games", tags=["Games"])


@router.get("/", response_model=List[GameResponse])
def get_games(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    genre: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get games with optional filtering."""
    query = db.query(Game)
    
    if search:
        query = query.filter(Game.name.ilike(f"%{search}%"))
    
    if genre:
        genre_obj = db.query(Genre).filter(Genre.name.ilike(f"%{genre}%")).first()
        if genre_obj:
            query = query.join(GameGenre).filter(GameGenre.genre_id == genre_obj.id)
    
    games = query.order_by(Game.name).offset(skip).limit(limit).all()
    return games


@router.get("/popular", response_model=List[GameResponse])
def get_popular_games(
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Get most owned games."""
    popular = db.query(
        Game,
        func.count(UserGame.id).label("owner_count")
    ).join(
        UserGame, Game.id == UserGame.game_id
    ).group_by(Game.id).order_by(
        desc("owner_count")
    ).limit(limit).all()
    
    return [g[0] for g in popular]


@router.get("/most-played", response_model=List[GameResponse])
def get_most_played_games(
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Get games with most total playtime across all users."""
    most_played = db.query(
        Game,
        func.sum(UserGame.playtime_forever).label("total_playtime")
    ).join(
        UserGame, Game.id == UserGame.game_id
    ).group_by(Game.id).order_by(
        desc("total_playtime")
    ).limit(limit).all()
    
    return [g[0] for g in most_played]


@router.get("/{game_id}", response_model=GameWithGenres)
def get_game(game_id: UUID, db: Session = Depends(get_db)):
    """Get game by ID with genres."""
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Get genres
    genres = db.query(Genre.name).join(
        GameGenre, Genre.id == GameGenre.genre_id
    ).filter(GameGenre.game_id == game_id).all()
    
    # Get categories
    from app.models import Category, GameCategory
    categories = db.query(Category.name).join(
        GameCategory, Category.id == GameCategory.category_id
    ).filter(GameCategory.game_id == game_id).all()
    
    return GameWithGenres(
        **{c.name: getattr(game, c.name) for c in game.__table__.columns},
        genres=[g.name for g in genres],
        categories=[c.name for c in categories]
    )


@router.get("/app/{app_id}", response_model=GameResponse)
def get_game_by_app_id(app_id: int, db: Session = Depends(get_db)):
    """Get game by Steam App ID."""
    game = db.query(Game).filter(Game.app_id == app_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game


@router.post("/app/{app_id}/sync", response_model=GameWithGenres)
async def sync_game_details(app_id: int, db: Session = Depends(get_db)):
    """Sync detailed game information from Steam Store API."""
    sync_service = DataSyncService(db)
    game = await sync_service.sync_game_details(app_id)
    
    if not game:
        raise HTTPException(status_code=404, detail="Game not found on Steam")
    
    # Get genres
    genres = db.query(Genre.name).join(
        GameGenre, Genre.id == GameGenre.genre_id
    ).filter(GameGenre.game_id == game.id).all()
    
    # Get categories
    from app.models import Category, GameCategory
    categories = db.query(Category.name).join(
        GameCategory, Category.id == GameCategory.category_id
    ).filter(GameCategory.game_id == game.id).all()
    
    return GameWithGenres(
        **{c.name: getattr(game, c.name) for c in game.__table__.columns},
        genres=[g.name for g in genres],
        categories=[c.name for c in categories]
    )


@router.post("/sync-popular-genres")
async def sync_popular_game_genres(
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Sync genres for the most popular games to populate genre data."""
    import asyncio
    
    try:
        # Get most popular games (most owned)
        popular_games = db.query(
            Game,
            func.count(UserGame.id).label("owner_count")
        ).join(
            UserGame, Game.id == UserGame.game_id
        ).group_by(Game.id).order_by(
            desc("owner_count")
        ).limit(limit).all()
        
        if not popular_games:
            return {
                "synced": 0,
                "failed": 0,
                "skipped": 0,
                "total_checked": 0,
                "message": "No games found"
            }
        
        synced = 0
        failed = 0
        skipped = 0
        
        for game_row in popular_games:
            game = game_row[0]
            
            # Check if game already has genres
            has_genres = db.query(GameGenre).filter(
                GameGenre.game_id == game.id
            ).first() is not None
            
            if has_genres:
                skipped += 1
                continue
            
            try:
                sync_service = DataSyncService(db)
                await sync_service.sync_game_details(game.app_id)
                synced += 1
                # Rate limiting to avoid Steam API throttling
                await asyncio.sleep(1.5)
            except Exception as e:
                failed += 1
                print(f"Failed to sync {game.name} ({game.app_id}): {str(e)}")
                import traceback
                traceback.print_exc()
        
        return {
            "synced": synced,
            "failed": failed,
            "skipped": skipped,
            "total_checked": len(popular_games)
        }
    except Exception as e:
        print(f"Error in sync_popular_game_genres: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.post("/sync-all-genres")
async def sync_all_game_genres(
    batch_size: int = Query(100, ge=1, le=500),
    delay_seconds: float = Query(1.5, ge=0.5, le=5.0),
    db: Session = Depends(get_db)
):
    """Sync genres for ALL games in the database. This may take a long time!"""
    import asyncio
    
    try:
        # Get all games that have users (are in someone's library)
        all_games = db.query(Game).join(
            UserGame, Game.id == UserGame.game_id
        ).group_by(Game.id).all()
        
        total_games = len(all_games)
        
        if total_games == 0:
            return {
                "synced": 0,
                "failed": 0,
                "skipped": 0,
                "total_games": 0,
                "message": "No games found in user libraries"
            }
        
        synced = 0
        failed = 0
        skipped = 0
        
        for i, game in enumerate(all_games, 1):
            # Check if game already has genres
            has_genres = db.query(GameGenre).filter(
                GameGenre.game_id == game.id
            ).first() is not None
            
            if has_genres:
                skipped += 1
                continue
            
            try:
                sync_service = DataSyncService(db)
                await sync_service.sync_game_details(game.app_id)
                synced += 1
                
                # Progress logging every 10 games
                if i % 10 == 0:
                    print(f"Progress: {i}/{total_games} - Synced: {synced}, Skipped: {skipped}, Failed: {failed}")
                
                # Rate limiting to avoid Steam API throttling
                await asyncio.sleep(delay_seconds)
            except Exception as e:
                failed += 1
                print(f"Failed to sync {game.name} ({game.app_id}): {str(e)}")
        
        return {
            "synced": synced,
            "failed": failed,
            "skipped": skipped,
            "total_games": total_games,
            "estimated_time_minutes": round(total_games * delay_seconds / 60, 1)
        }
    except Exception as e:
        print(f"Error in sync_all_game_genres: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.get("/{game_id}/owners")
def get_game_owners(
    game_id: UUID,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get users who own a specific game."""
    from app.models import SteamUser
    
    owners = db.query(SteamUser, UserGame.playtime_forever).join(
        UserGame, SteamUser.id == UserGame.steam_user_id
    ).filter(
        UserGame.game_id == game_id
    ).order_by(
        desc(UserGame.playtime_forever)
    ).offset(skip).limit(limit).all()
    
    return [
        {
            "user": owner[0],
            "playtime_forever": owner[1]
        }
        for owner in owners
    ]


# Genres
@router.get("/genres/", response_model=List[GenreResponse])
def get_genres(db: Session = Depends(get_db)):
    """Get all genres."""
    genres = db.query(Genre).order_by(Genre.name).all()
    return genres


@router.get("/genres/{genre_id}/games", response_model=List[GameResponse])
def get_games_by_genre(
    genre_id: UUID,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get games by genre."""
    games = db.query(Game).join(
        GameGenre, Game.id == GameGenre.game_id
    ).filter(
        GameGenre.genre_id == genre_id
    ).offset(skip).limit(limit).all()
    
    return games
