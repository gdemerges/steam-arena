from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
from typing import List, Optional, Dict, Tuple
from uuid import UUID
from datetime import datetime
import asyncio

from app.models import (
    SteamUser, Game, UserGame, Genre, GameGenre, Category, GameCategory,
    Achievement, UserAchievement, UserGroup, GroupMember, UserBacklog,
    SyncHistory, MLPlayerFeatures, Recommendation
)
from app.services.steam_api import steam_client


class DataSyncService:
    """Service for synchronizing data from Steam API to database."""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def sync_user_profile(self, steam_id: str) -> Optional[SteamUser]:
        """Sync user profile from Steam API."""
        # Fetch from Steam API
        player_data = await steam_client.get_player_summary(steam_id)
        if not player_data:
            return None
        
        parsed_data = steam_client.parse_player_data(player_data)
        
        # Check if user exists
        user = self.db.query(SteamUser).filter(
            SteamUser.steam_id == steam_id
        ).first()
        
        if user:
            # Update existing user
            for key, value in parsed_data.items():
                if value is not None:
                    setattr(user, key, value)
        else:
            # Create new user
            user = SteamUser(**parsed_data)
            self.db.add(user)
        
        self.db.commit()
        self.db.refresh(user)
        
        # Log sync history
        self._log_sync(user.id, "profile", "completed", 1)
        
        return user
    
    async def sync_user_games(self, steam_id: str) -> Tuple[int, int]:
        """Sync user's game library from Steam API. Returns (games_synced, playtime_updated)."""
        user = self.db.query(SteamUser).filter(
            SteamUser.steam_id == steam_id
        ).first()
        
        if not user:
            user = await self.sync_user_profile(steam_id)
            if not user:
                return (0, 0)
        
        # Fetch owned games
        games_data = await steam_client.get_owned_games(steam_id)
        if not games_data or "games" not in games_data:
            return (0, 0)
        
        games_synced = 0
        playtime_updated = 0
        
        for game_data in games_data["games"]:
            parsed_game = steam_client.parse_game_data(game_data)
            
            # Get or create game
            game = self.db.query(Game).filter(
                Game.app_id == parsed_game["app_id"]
            ).first()
            
            if not game:
                game = Game(
                    app_id=parsed_game["app_id"],
                    name=parsed_game["name"],
                    img_icon_url=parsed_game.get("img_icon_url")
                )
                self.db.add(game)
                self.db.flush()
                games_synced += 1
            
            # Get or create user_game relationship
            user_game = self.db.query(UserGame).filter(
                and_(
                    UserGame.steam_user_id == user.id,
                    UserGame.game_id == game.id
                )
            ).first()
            
            if user_game:
                # Update playtime
                user_game.playtime_forever = parsed_game["playtime_forever"]
                user_game.playtime_2weeks = parsed_game["playtime_2weeks"]
                user_game.playtime_windows = parsed_game["playtime_windows"]
                user_game.playtime_mac = parsed_game["playtime_mac"]
                user_game.playtime_linux = parsed_game["playtime_linux"]
                user_game.rtime_last_played = parsed_game["rtime_last_played"]
                playtime_updated += 1
            else:
                user_game = UserGame(
                    steam_user_id=user.id,
                    game_id=game.id,
                    playtime_forever=parsed_game["playtime_forever"],
                    playtime_2weeks=parsed_game["playtime_2weeks"],
                    playtime_windows=parsed_game["playtime_windows"],
                    playtime_mac=parsed_game["playtime_mac"],
                    playtime_linux=parsed_game["playtime_linux"],
                    rtime_last_played=parsed_game["rtime_last_played"]
                )
                self.db.add(user_game)
                games_synced += 1
        
        self.db.commit()
        
        # Log sync history
        total_synced = games_synced + playtime_updated
        self._log_sync(user.id, "games", "completed", total_synced)
        
        return (games_synced, playtime_updated)
    
    async def sync_game_details(self, app_id: int) -> Optional[Game]:
        """Sync detailed game information from Steam Store API."""
        try:
            app_details = await steam_client.get_app_details(app_id)
            if not app_details:
                return None
            
            parsed_details = steam_client.parse_app_details(app_details)
            
            game = self.db.query(Game).filter(Game.app_id == app_id).first()
            if not game:
                game = Game(app_id=app_id, name=parsed_details.get("name", f"Game {app_id}"))
                self.db.add(game)
                self.db.flush()
            
            # Update game details
            for key, value in parsed_details.items():
                if key not in ["genres", "categories"] and value is not None:
                    setattr(game, key, value)
            
            self.db.flush()
            
            # Sync genres - use merge approach to avoid duplicates
            for genre_name in parsed_details.get("genres", []):
                genre = self.db.query(Genre).filter(Genre.name == genre_name).first()
                if not genre:
                    genre = Genre(name=genre_name)
                    self.db.add(genre)
                    self.db.flush()
                
                # Check if relationship exists (refresh query to get latest state)
                self.db.expire_all()
                existing = self.db.query(GameGenre).filter(
                    and_(GameGenre.game_id == game.id, GameGenre.genre_id == genre.id)
                ).first()
                
                if not existing:
                    game_genre = GameGenre(game_id=game.id, genre_id=genre.id)
                    self.db.merge(game_genre)
            
            # Sync categories - use merge approach to avoid duplicates
            for cat_name in parsed_details.get("categories", []):
                category = self.db.query(Category).filter(Category.name == cat_name).first()
                if not category:
                    category = Category(name=cat_name)
                    self.db.add(category)
                    self.db.flush()
                
                # Check if relationship exists (refresh query to get latest state)
                self.db.expire_all()
                existing = self.db.query(GameCategory).filter(
                    and_(GameCategory.game_id == game.id, GameCategory.category_id == category.id)
                ).first()
                
                if not existing:
                    game_category = GameCategory(game_id=game.id, category_id=category.id)
                    self.db.merge(game_category)
            
            self.db.commit()
            self.db.refresh(game)
            return game
        except Exception as e:
            self.db.rollback()
            print(f"Error syncing game {app_id}: {str(e)}")
            # Don't raise, just return None to continue with other games
            return None
    
    async def sync_user_achievements(
        self, 
        steam_id: str, 
        app_id: int
    ) -> Tuple[int, int]:
        """Sync user achievements for a specific game. Returns (total_achievements, unlocked)."""
        user = self.db.query(SteamUser).filter(
            SteamUser.steam_id == steam_id
        ).first()
        if not user:
            return (0, 0)
        
        game = self.db.query(Game).filter(Game.app_id == app_id).first()
        if not game:
            return (0, 0)
        
        # Get game schema for achievement definitions
        schema = await steam_client.get_game_schema(app_id)
        if not schema or "availableGameStats" not in schema:
            return (0, 0)
        
        achievements_def = schema["availableGameStats"].get("achievements", [])
        
        # Get global percentages
        global_percentages = await steam_client.get_global_achievement_percentages(app_id)
        percent_map = {}
        if global_percentages:
            percent_map = {a["name"]: a["percent"] for a in global_percentages}
        
        # Sync achievement definitions
        for ach_def in achievements_def:
            achievement = self.db.query(Achievement).filter(
                and_(
                    Achievement.game_id == game.id,
                    Achievement.api_name == ach_def["name"]
                )
            ).first()
            
            if not achievement:
                achievement = Achievement(
                    game_id=game.id,
                    api_name=ach_def["name"],
                    display_name=ach_def.get("displayName"),
                    description=ach_def.get("description"),
                    icon_url=ach_def.get("icon"),
                    icon_gray_url=ach_def.get("icongray"),
                    hidden=ach_def.get("hidden", 0) == 1,
                    global_percent=percent_map.get(ach_def["name"])
                )
                self.db.add(achievement)
        
        self.db.flush()
        
        # Get user achievements
        player_achievements = await steam_client.get_player_achievements(steam_id, app_id)
        if not player_achievements or "achievements" not in player_achievements:
            self.db.commit()
            return (len(achievements_def), 0)
        
        unlocked = 0
        for ach_data in player_achievements["achievements"]:
            achievement = self.db.query(Achievement).filter(
                and_(
                    Achievement.game_id == game.id,
                    Achievement.api_name == ach_data["apiname"]
                )
            ).first()
            
            if achievement:
                user_ach = self.db.query(UserAchievement).filter(
                    and_(
                        UserAchievement.steam_user_id == user.id,
                        UserAchievement.achievement_id == achievement.id
                    )
                ).first()
                
                achieved = ach_data.get("achieved", 0) == 1
                unlock_time = datetime.fromtimestamp(ach_data["unlocktime"]) if ach_data.get("unlocktime") else None
                
                if user_ach:
                    user_ach.achieved = achieved
                    user_ach.unlock_time = unlock_time
                else:
                    user_ach = UserAchievement(
                        steam_user_id=user.id,
                        achievement_id=achievement.id,
                        achieved=achieved,
                        unlock_time=unlock_time
                    )
                    self.db.add(user_ach)
                
                if achieved:
                    unlocked += 1
        
        self.db.commit()
        
        # Log sync
        self._log_sync(user.id, "achievements", "completed", len(achievements_def))
        
        return (len(achievements_def), unlocked)
    
    async def sync_all_user_achievements(self, steam_id: str) -> Dict:
        """Sync achievements for all games owned by user."""
        user = self.db.query(SteamUser).filter(
            SteamUser.steam_id == steam_id
        ).first()
        if not user:
            return {"error": "User not found"}
        
        # Get user's games
        user_games = self.db.query(UserGame).filter(
            UserGame.steam_user_id == user.id
        ).all()
        
        results = {
            "total_games": len(user_games),
            "games_with_achievements": 0,
            "total_achievements": 0,
            "total_unlocked": 0
        }
        
        for user_game in user_games:
            game = self.db.query(Game).filter(Game.id == user_game.game_id).first()
            if game:
                total, unlocked = await self.sync_user_achievements(steam_id, game.app_id)
                if total > 0:
                    results["games_with_achievements"] += 1
                    results["total_achievements"] += total
                    results["total_unlocked"] += unlocked
        
        return results
    
    def _log_sync(
        self, 
        user_id: UUID, 
        sync_type: str, 
        status: str, 
        items_synced: int,
        error_message: str = None
    ):
        """Log sync history."""
        sync_record = SyncHistory(
            steam_user_id=user_id,
            sync_type=sync_type,
            status=status,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow() if status in ["completed", "failed"] else None,
            items_synced=items_synced,
            error_message=error_message
        )
        self.db.add(sync_record)
        self.db.commit()


class GroupService:
    """Service for managing user groups."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_group(
        self, 
        name: str, 
        description: str = None, 
        created_by: UUID = None
    ) -> UserGroup:
        """Create a new group."""
        group = UserGroup(
            name=name,
            description=description,
            created_by=created_by
        )
        self.db.add(group)
        self.db.commit()
        self.db.refresh(group)
        return group
    
    def get_group(self, group_id: UUID) -> Optional[UserGroup]:
        """Get group by ID."""
        return self.db.query(UserGroup).filter(UserGroup.id == group_id).first()
    
    def get_all_groups(self) -> List[UserGroup]:
        """Get all groups."""
        return self.db.query(UserGroup).all()
    
    def update_group(
        self, 
        group_id: UUID, 
        name: str = None, 
        description: str = None
    ) -> Optional[UserGroup]:
        """Update group."""
        group = self.get_group(group_id)
        if not group:
            return None
        
        if name:
            group.name = name
        if description is not None:
            group.description = description
        
        self.db.commit()
        self.db.refresh(group)
        return group
    
    def delete_group(self, group_id: UUID) -> bool:
        """Delete group."""
        group = self.get_group(group_id)
        if not group:
            return False
        
        self.db.delete(group)
        self.db.commit()
        return True
    
    async def add_members(
        self, 
        group_id: UUID, 
        steam_ids: List[str]
    ) -> List[GroupMember]:
        """Add members to group by Steam IDs."""
        group = self.get_group(group_id)
        if not group:
            return []
        
        added_members = []
        sync_service = DataSyncService(self.db)
        
        for steam_id in steam_ids:
            # Get or create user
            user = self.db.query(SteamUser).filter(
                SteamUser.steam_id == steam_id
            ).first()
            
            if not user:
                user = await sync_service.sync_user_profile(steam_id)
                if not user:
                    continue
            
            # Check if already a member
            existing = self.db.query(GroupMember).filter(
                and_(
                    GroupMember.group_id == group_id,
                    GroupMember.steam_user_id == user.id
                )
            ).first()
            
            if not existing:
                member = GroupMember(
                    group_id=group_id,
                    steam_user_id=user.id
                )
                self.db.add(member)
                added_members.append(member)
        
        self.db.commit()
        return added_members
    
    def remove_member(self, group_id: UUID, user_id: UUID) -> bool:
        """Remove member from group."""
        member = self.db.query(GroupMember).filter(
            and_(
                GroupMember.group_id == group_id,
                GroupMember.steam_user_id == user_id
            )
        ).first()
        
        if not member:
            return False
        
        self.db.delete(member)
        self.db.commit()
        return True
    
    def get_group_members(self, group_id: UUID) -> List[SteamUser]:
        """Get all members of a group."""
        members = self.db.query(GroupMember).filter(
            GroupMember.group_id == group_id
        ).all()
        
        return [
            self.db.query(SteamUser).filter(
                SteamUser.id == m.steam_user_id
            ).first() 
            for m in members
        ]


class ComparisonService:
    """Service for comparing users and groups."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_stats(self, user_id: UUID) -> Dict:
        """Get comprehensive stats for a user."""
        user = self.db.query(SteamUser).filter(SteamUser.id == user_id).first()
        if not user:
            return {}
        
        # Get games stats
        games_stats = self.db.query(
            func.count(UserGame.id).label("total_games"),
            func.sum(UserGame.playtime_forever).label("total_playtime"),
            func.count(UserGame.id).filter(UserGame.playtime_forever > 0).label("games_played")
        ).filter(UserGame.steam_user_id == user_id).first()
        
        # Get achievements stats
        achievements_stats = self.db.query(
            func.count(UserAchievement.id).label("total"),
            func.count(UserAchievement.id).filter(UserAchievement.achieved == True).label("unlocked")
        ).filter(UserAchievement.steam_user_id == user_id).first()
        
        # Get genre distribution
        genre_distribution = self._get_user_genre_distribution(user_id)
        
        # Get backlog stats
        backlog_stats = self.db.query(
            UserBacklog.status,
            func.count(UserBacklog.id)
        ).filter(
            UserBacklog.steam_user_id == user_id
        ).group_by(UserBacklog.status).all()
        
        return {
            "user": user,
            "total_games": games_stats.total_games or 0,
            "total_playtime": games_stats.total_playtime or 0,
            "games_played": games_stats.games_played or 0,
            "total_achievements": achievements_stats.total or 0,
            "achievements_unlocked": achievements_stats.unlocked or 0,
            "completion_rate": (achievements_stats.unlocked / achievements_stats.total * 100) 
                if achievements_stats.total > 0 else 0,
            "genre_distribution": genre_distribution,
            "backlog_stats": dict(backlog_stats)
        }
    
    def _get_user_genre_distribution(self, user_id: UUID) -> List[Dict]:
        """Get genre distribution weighted by playtime."""
        results = self.db.query(
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
        ).group_by(
            Genre.name
        ).order_by(
            desc("total_playtime")
        ).limit(10).all()
        
        return [
            {
                "genre": r.name,
                "total_playtime": r.total_playtime or 0,
                "game_count": r.game_count
            }
            for r in results
        ]
    
    def compare_users(self, user_ids: List[UUID]) -> Dict:
        """Compare multiple users."""
        comparison = {
            "users": [],
            "common_games": [],
            "playtime_ranking": [],
            "achievement_ranking": []
        }
        
        for user_id in user_ids:
            stats = self.get_user_stats(user_id)
            if stats and stats.get("user"):
                user = stats["user"]
                user_data = {
                    "user_id": str(user.id),
                    "steam_id": user.steam_id,
                    "persona_name": user.persona_name,
                    "avatar_url": user.avatar_url,
                    "total_games": stats.get("total_games", 0),
                    "total_playtime": stats.get("total_playtime", 0),
                    "games_played": stats.get("games_played", 0),
                    "achievements_unlocked": stats.get("achievements_unlocked", 0),
                }
                comparison["users"].append(user_data)
        
        # Find common games
        if len(user_ids) >= 2:
            comparison["common_games"] = self._find_common_games(user_ids)
        
        # Rank by playtime
        comparison["playtime_ranking"] = sorted(
            comparison["users"],
            key=lambda x: x["total_playtime"],
            reverse=True
        )
        
        # Rank by achievements
        comparison["achievement_ranking"] = sorted(
            comparison["users"],
            key=lambda x: x["achievements_unlocked"],
            reverse=True
        )
        
        return comparison
    
    def _find_common_games(self, user_ids: List[UUID]) -> List[Dict]:
        """Find games owned by all specified users."""
        if not user_ids:
            return []
        
        # Get games for first user
        first_user_games = set(
            ug.game_id for ug in self.db.query(UserGame).filter(
                UserGame.steam_user_id == user_ids[0]
            ).all()
        )
        
        # Intersect with other users
        for user_id in user_ids[1:]:
            user_games = set(
                ug.game_id for ug in self.db.query(UserGame).filter(
                    UserGame.steam_user_id == user_id
                ).all()
            )
            first_user_games = first_user_games.intersection(user_games)
        
        # Get game details
        common_games = []
        for game_id in first_user_games:
            game = self.db.query(Game).filter(Game.id == game_id).first()
            if game:
                # Calculate combined playtime
                total_playtime = self.db.query(
                    func.sum(UserGame.playtime_forever)
                ).filter(
                    and_(
                        UserGame.game_id == game_id,
                        UserGame.steam_user_id.in_(user_ids)
                    )
                ).scalar() or 0
                
                common_games.append({
                    "game": game,
                    "total_combined_playtime": total_playtime,
                    "owner_count": len(user_ids)
                })
        
        # Sort by combined playtime
        common_games.sort(key=lambda x: x["total_combined_playtime"], reverse=True)
        
        return common_games
    
    def get_game_intersection(self, group_id: UUID) -> Dict:
        """Get games with highest ownership intersection in a group."""
        group_service = GroupService(self.db)
        members = group_service.get_group_members(group_id)
        
        if not members:
            return {"error": "No members in group"}
        
        member_ids = [m.id for m in members]
        
        # Count ownership for each game
        ownership_counts = self.db.query(
            Game.id,
            Game.name,
            Game.app_id,
            Game.header_image,
            func.count(UserGame.steam_user_id).label("owner_count"),
            func.sum(UserGame.playtime_forever).label("total_playtime")
        ).join(
            UserGame, Game.id == UserGame.game_id
        ).filter(
            UserGame.steam_user_id.in_(member_ids)
        ).group_by(
            Game.id
        ).order_by(
            desc("owner_count"),
            desc("total_playtime")
        ).all()
        
        total_members = len(member_ids)
        
        # Categorize by ownership level
        owned_by_all = []
        owned_by_majority = []
        
        for game in ownership_counts:
            game_data = {
                "game_id": game.id,
                "name": game.name,
                "app_id": game.app_id,
                "header_image": game.header_image,
                "owner_count": game.owner_count,
                "total_playtime": game.total_playtime or 0,
                "ownership_percentage": (game.owner_count / total_members) * 100
            }
            
            if game.owner_count == total_members:
                owned_by_all.append(game_data)
            elif game.owner_count >= total_members / 2:
                owned_by_majority.append(game_data)
        
        return {
            "group_id": group_id,
            "total_members": total_members,
            "games_owned_by_all": owned_by_all[:20],
            "games_owned_by_majority": owned_by_majority[:20]
        }
