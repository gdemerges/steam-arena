from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, extract
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging

from app.database import get_db
from app.models import (
    SteamUser, UserGame, Game, PlaytimeHistory, UserYearlyStats, UserMonthlyStats
)

router = APIRouter(prefix="/playtime-tracking", tags=["playtime-tracking"])
logger = logging.getLogger(__name__)


@router.post("/snapshot")
async def create_playtime_snapshot(db: Session = Depends(get_db)):
    """
    Crée un snapshot du playtime actuel pour tous les utilisateurs.
    À exécuter régulièrement (quotidien recommandé) pour construire l'historique.
    """
    try:
        now = datetime.utcnow()
        year = now.year
        month = now.month
        
        # Récupérer tous les user_games
        user_games = db.query(UserGame).all()
        
        snapshots_created = 0
        for ug in user_games:
            # Créer un snapshot pour ce jeu/user
            snapshot = PlaytimeHistory(
                steam_user_id=ug.steam_user_id,
                game_id=ug.game_id,
                playtime_forever=ug.playtime_forever,
                recorded_at=now,
                year=year,
                month=month
            )
            db.add(snapshot)
            snapshots_created += 1
        
        db.commit()
        
        logger.info(f"Created {snapshots_created} playtime snapshots")
        
        return {
            "status": "success",
            "snapshots_created": snapshots_created,
            "timestamp": now.isoformat()
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create snapshots: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Snapshot creation failed: {str(e)}")


@router.post("/calculate-yearly-stats/{year}")
async def calculate_yearly_stats(year: int, db: Session = Depends(get_db)):
    """
    Calcule les stats annuelles pour une année donnée.
    Compare les snapshots de début/fin d'année pour chaque utilisateur.
    """
    try:
        # Dates limites de l'année
        year_start = datetime(year, 1, 1)
        year_end = datetime(year, 12, 31, 23, 59, 59)
        
        # Récupérer tous les utilisateurs
        users = db.query(SteamUser).all()
        
        stats_created = 0
        for user in users:
            # Trouver le snapshot le plus proche du début de l'année
            start_snapshot = db.query(PlaytimeHistory).filter(
                and_(
                    PlaytimeHistory.steam_user_id == user.id,
                    PlaytimeHistory.recorded_at <= year_start
                )
            ).order_by(PlaytimeHistory.recorded_at.desc()).first()
            
            # Trouver le snapshot le plus récent de l'année
            end_snapshot = db.query(PlaytimeHistory).filter(
                and_(
                    PlaytimeHistory.steam_user_id == user.id,
                    PlaytimeHistory.recorded_at <= year_end
                )
            ).order_by(PlaytimeHistory.recorded_at.desc()).first()
            
            if not end_snapshot:
                logger.warning(f"No snapshots found for user {user.steam_id} in year {year}")
                continue
            
            # Calculer le playtime de l'année
            # Grouper par jeu pour calculer les différences
            games_playtime = {}
            
            # Snapshots de fin d'année
            end_snapshots = db.query(PlaytimeHistory).filter(
                and_(
                    PlaytimeHistory.steam_user_id == user.id,
                    PlaytimeHistory.year == year
                )
            ).all()
            
            for end_snap in end_snapshots:
                # Trouver le snapshot de début d'année pour ce jeu
                start_snap = db.query(PlaytimeHistory).filter(
                    and_(
                        PlaytimeHistory.steam_user_id == user.id,
                        PlaytimeHistory.game_id == end_snap.game_id,
                        PlaytimeHistory.recorded_at < year_start
                    )
                ).order_by(PlaytimeHistory.recorded_at.desc()).first()
                
                start_playtime = start_snap.playtime_forever if start_snap else 0
                playtime_this_year = end_snap.playtime_forever - start_playtime
                
                if playtime_this_year > 0:
                    games_playtime[end_snap.game_id] = playtime_this_year
            
            if not games_playtime:
                continue
            
            # Calculer les stats
            total_playtime_minutes = sum(games_playtime.values())
            total_playtime_hours = total_playtime_minutes / 60.0
            games_played_count = len(games_playtime)
            
            # Trouver le jeu le plus joué
            most_played_game_id = max(games_playtime, key=games_playtime.get)
            most_played_playtime = games_playtime[most_played_game_id]
            
            # Compter les nouveaux jeux (première apparition dans l'historique cette année)
            new_games = db.query(PlaytimeHistory.game_id).filter(
                and_(
                    PlaytimeHistory.steam_user_id == user.id,
                    PlaytimeHistory.year == year
                )
            ).distinct().all()
            
            # Vérifier si ces jeux apparaissent avant cette année
            new_games_count = 0
            for (game_id,) in new_games:
                prior_snapshot = db.query(PlaytimeHistory).filter(
                    and_(
                        PlaytimeHistory.steam_user_id == user.id,
                        PlaytimeHistory.game_id == game_id,
                        PlaytimeHistory.year < year
                    )
                ).first()
                if not prior_snapshot:
                    new_games_count += 1
            
            # Vérifier si une stat existe déjà
            existing_stat = db.query(UserYearlyStats).filter(
                and_(
                    UserYearlyStats.steam_user_id == user.id,
                    UserYearlyStats.year == year
                )
            ).first()
            
            if existing_stat:
                # Mettre à jour
                existing_stat.total_playtime_minutes = total_playtime_minutes
                existing_stat.total_playtime_hours = total_playtime_hours
                existing_stat.games_played_count = games_played_count
                existing_stat.new_games_count = new_games_count
                existing_stat.most_played_game_id = most_played_game_id
                existing_stat.most_played_playtime = most_played_playtime
                existing_stat.updated_at = datetime.utcnow()
            else:
                # Créer nouvelle stat
                yearly_stat = UserYearlyStats(
                    steam_user_id=user.id,
                    year=year,
                    total_playtime_minutes=total_playtime_minutes,
                    total_playtime_hours=total_playtime_hours,
                    games_played_count=games_played_count,
                    new_games_count=new_games_count,
                    most_played_game_id=most_played_game_id,
                    most_played_playtime=most_played_playtime
                )
                db.add(yearly_stat)
            
            stats_created += 1
        
        db.commit()
        
        logger.info(f"Calculated yearly stats for {stats_created} users for year {year}")
        
        return {
            "status": "success",
            "year": year,
            "users_processed": stats_created
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to calculate yearly stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Stats calculation failed: {str(e)}")


@router.get("/users/{steam_id}/yearly-stats")
async def get_user_yearly_stats(steam_id: str, db: Session = Depends(get_db)):
    """
    Récupère les stats annuelles pour un utilisateur.
    Retourne les données pour toutes les années disponibles.
    """
    try:
        # Trouver l'utilisateur
        user = db.query(SteamUser).filter(SteamUser.steam_id == steam_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Récupérer toutes les stats annuelles
        yearly_stats = db.query(UserYearlyStats).filter(
            UserYearlyStats.steam_user_id == user.id
        ).order_by(UserYearlyStats.year.desc()).all()
        
        # Formatter les résultats
        result = []
        for stat in yearly_stats:
            most_played_game = None
            if stat.most_played_game_id:
                game = db.query(Game).filter(Game.id == stat.most_played_game_id).first()
                if game:
                    most_played_game = {
                        "app_id": game.app_id,
                        "name": game.name,
                        "playtime_minutes": stat.most_played_playtime,
                        "playtime_hours": round(stat.most_played_playtime / 60.0, 1)
                    }
            
            result.append({
                "year": stat.year,
                "total_playtime_minutes": stat.total_playtime_minutes,
                "total_playtime_hours": round(stat.total_playtime_hours, 1),
                "games_played_count": stat.games_played_count,
                "new_games_count": stat.new_games_count,
                "most_played_game": most_played_game,
                "achievements_unlocked": stat.achievements_unlocked
            })
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get yearly stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve stats: {str(e)}")


@router.get("/snapshot-history")
async def get_snapshot_history(limit: int = 10, db: Session = Depends(get_db)):
    """
    Récupère l'historique des snapshots créés.
    Utile pour l'admin pour voir si les snapshots sont bien enregistrés.
    """
    try:
        # Grouper par date et compter
        snapshots = db.query(
            func.date(PlaytimeHistory.recorded_at).label('date'),
            func.count(PlaytimeHistory.id).label('count')
        ).group_by(
            func.date(PlaytimeHistory.recorded_at)
        ).order_by(
            func.date(PlaytimeHistory.recorded_at).desc()
        ).limit(limit).all()
        
        result = [
            {
                "date": snap.date.isoformat() if snap.date else None,
                "snapshots_count": snap.count
            }
            for snap in snapshots
        ]
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get snapshot history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve snapshot history: {str(e)}")


@router.post("/calculate-monthly-stats/{year}/{month}")
async def calculate_monthly_stats(year: int, month: int, db: Session = Depends(get_db)):
    """
    Calcule les statistiques mensuelles pour tous les utilisateurs.
    Compare les snapshots du début et de la fin du mois.
    """
    try:
        # Validation
        if month < 1 or month > 12:
            raise HTTPException(status_code=400, detail="Month must be between 1 and 12")
        
        # Dates du mois
        from calendar import monthrange
        _, last_day = monthrange(year, month)
        month_start = datetime(year, month, 1)
        month_end = datetime(year, month, last_day, 23, 59, 59)
        
        # Récupérer tous les utilisateurs
        users = db.query(SteamUser).all()
        users_processed = 0
        
        for user in users:
            # Snapshot du début du mois (ou le plus proche après)
            start_snapshot = db.query(PlaytimeHistory).filter(
                PlaytimeHistory.steam_user_id == user.id,
                PlaytimeHistory.recorded_at >= month_start - timedelta(days=7),
                PlaytimeHistory.recorded_at <= month_start + timedelta(days=7)
            ).order_by(
                func.abs(extract('epoch', PlaytimeHistory.recorded_at - month_start))
            ).first()
            
            # Snapshot de fin de mois (ou le plus proche avant)
            end_snapshot = db.query(PlaytimeHistory).filter(
                PlaytimeHistory.steam_user_id == user.id,
                PlaytimeHistory.recorded_at >= month_end - timedelta(days=7),
                PlaytimeHistory.recorded_at <= month_end + timedelta(days=7)
            ).order_by(
                func.abs(extract('epoch', PlaytimeHistory.recorded_at - month_end))
            ).first()
            
            if not start_snapshot or not end_snapshot:
                logger.warning(f"Missing snapshots for user {user.steam_id} in {year}-{month:02d}")
                continue
            
            # Calculer les différences de playtime par jeu
            start_times = {}
            for snapshot in db.query(PlaytimeHistory).filter(
                PlaytimeHistory.steam_user_id == user.id,
                PlaytimeHistory.recorded_at == start_snapshot.recorded_at
            ).all():
                start_times[snapshot.game_id] = snapshot.playtime_forever
            
            end_times = {}
            for snapshot in db.query(PlaytimeHistory).filter(
                PlaytimeHistory.steam_user_id == user.id,
                PlaytimeHistory.recorded_at == end_snapshot.recorded_at
            ).all():
                end_times[snapshot.game_id] = snapshot.playtime_forever
            
            # Calculer les stats
            total_playtime = 0
            games_played = set()
            new_games = set()
            game_playtimes = {}
            
            for game_id, end_time in end_times.items():
                start_time = start_times.get(game_id, 0)
                playtime_diff = end_time - start_time
                
                if playtime_diff > 0:
                    total_playtime += playtime_diff
                    games_played.add(game_id)
                    game_playtimes[game_id] = playtime_diff
                
                # Nouveau jeu ce mois
                if game_id not in start_times:
                    new_games.add(game_id)
            
            # Jeu le plus joué
            most_played_game_id = None
            most_played_playtime = 0
            if game_playtimes:
                most_played_game_id = max(game_playtimes, key=game_playtimes.get)
                most_played_playtime = game_playtimes[most_played_game_id]
            
            # Créer ou mettre à jour les stats mensuelles
            monthly_stat = db.query(UserMonthlyStats).filter(
                and_(
                    UserMonthlyStats.steam_user_id == user.id,
                    UserMonthlyStats.year == year,
                    UserMonthlyStats.month == month
                )
            ).first()
            
            if monthly_stat:
                # Mise à jour
                monthly_stat.total_playtime_minutes = total_playtime
                monthly_stat.total_playtime_hours = round(total_playtime / 60.0, 2)
                monthly_stat.games_played_count = len(games_played)
                monthly_stat.new_games_count = len(new_games)
                monthly_stat.most_played_game_id = most_played_game_id
                monthly_stat.most_played_playtime = most_played_playtime
                monthly_stat.updated_at = datetime.utcnow()
            else:
                # Création
                monthly_stat = UserMonthlyStats(
                    steam_user_id=user.id,
                    year=year,
                    month=month,
                    total_playtime_minutes=total_playtime,
                    total_playtime_hours=round(total_playtime / 60.0, 2),
                    games_played_count=len(games_played),
                    new_games_count=len(new_games),
                    most_played_game_id=most_played_game_id,
                    most_played_playtime=most_played_playtime
                )
                db.add(monthly_stat)
            
            users_processed += 1
        
        db.commit()
        
        logger.info(f"Calculated monthly stats for {year}-{month:02d}: {users_processed} users")
        
        return {
            "status": "success",
            "year": year,
            "month": month,
            "users_processed": users_processed,
            "message": f"Monthly stats calculated for {year}-{month:02d}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to calculate monthly stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Stats calculation failed: {str(e)}")


@router.get("/users/{steam_id}/monthly-stats")
async def get_user_monthly_stats(
    steam_id: str,
    year: int = None,
    db: Session = Depends(get_db)
):
    """
    Récupère les stats mensuelles pour un utilisateur.
    Si year est fourni, retourne seulement cette année, sinon toutes les années.
    """
    try:
        # Trouver l'utilisateur
        user = db.query(SteamUser).filter(SteamUser.steam_id == steam_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Requête de base
        query = db.query(UserMonthlyStats).filter(
            UserMonthlyStats.steam_user_id == user.id
        )
        
        # Filtrer par année si fourni
        if year:
            query = query.filter(UserMonthlyStats.year == year)
        
        # Ordonner par année et mois
        monthly_stats = query.order_by(
            UserMonthlyStats.year.desc(),
            UserMonthlyStats.month.desc()
        ).all()
        
        # Formatter les résultats
        result = []
        for stat in monthly_stats:
            most_played_game = None
            if stat.most_played_game_id:
                game = db.query(Game).filter(Game.id == stat.most_played_game_id).first()
                if game:
                    most_played_game = {
                        "app_id": game.app_id,
                        "name": game.name,
                        "playtime_minutes": stat.most_played_playtime,
                        "playtime_hours": round(stat.most_played_playtime / 60.0, 1)
                    }
            
            result.append({
                "year": stat.year,
                "month": stat.month,
                "month_name": datetime(stat.year, stat.month, 1).strftime("%B"),
                "total_playtime_minutes": stat.total_playtime_minutes,
                "total_playtime_hours": round(stat.total_playtime_hours, 1),
                "games_played_count": stat.games_played_count,
                "new_games_count": stat.new_games_count,
                "most_played_game": most_played_game,
                "achievements_unlocked": stat.achievements_unlocked
            })
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get monthly stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve stats: {str(e)}")

