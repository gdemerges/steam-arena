from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from enum import Enum


# Enums
class BacklogStatus(str, Enum):
    BACKLOG = "backlog"
    PLAYING = "playing"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    WISHLIST = "wishlist"


class SyncType(str, Enum):
    PROFILE = "profile"
    GAMES = "games"
    ACHIEVEMENTS = "achievements"
    FRIENDS = "friends"


class SyncStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


# Steam User Schemas
class SteamUserBase(BaseModel):
    steam_id: str
    persona_name: Optional[str] = None
    profile_url: Optional[str] = None
    avatar_url: Optional[str] = None
    avatar_medium_url: Optional[str] = None
    avatar_full_url: Optional[str] = None
    country_code: Optional[str] = None


class SteamUserCreate(BaseModel):
    steam_id: str


class SteamUserResponse(SteamUserBase):
    id: UUID
    time_created: Optional[datetime] = None
    last_logoff: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SteamUserWithStats(SteamUserResponse):
    total_games: int = 0
    total_playtime: int = 0
    total_achievements: int = 0
    games_played: int = 0


# Game Schemas
class GameBase(BaseModel):
    app_id: int
    name: str
    img_icon_url: Optional[str] = None
    header_image: Optional[str] = None
    short_description: Optional[str] = None
    is_free: bool = False


class GameResponse(GameBase):
    id: UUID
    developer: Optional[str] = None
    publisher: Optional[str] = None
    metacritic_score: Optional[int] = None
    release_date: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class GameWithGenres(GameResponse):
    genres: List[str] = []
    categories: List[str] = []


# User Game Schemas
class UserGameBase(BaseModel):
    playtime_forever: int = 0
    playtime_2weeks: int = 0


class UserGameResponse(UserGameBase):
    id: UUID
    game: GameResponse
    rtime_last_played: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Genre Schemas
class GenreResponse(BaseModel):
    id: UUID
    steam_genre_id: Optional[int] = None
    name: str

    class Config:
        from_attributes = True


# Group Schemas
class GroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class GroupUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None


class GroupMemberAdd(BaseModel):
    steam_ids: List[str] = Field(..., min_items=1)


class GroupMemberResponse(BaseModel):
    id: UUID
    steam_user: SteamUserResponse
    added_at: datetime

    class Config:
        from_attributes = True


class GroupResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    member_count: int = 0

    class Config:
        from_attributes = True


class GroupDetailResponse(GroupResponse):
    members: List[GroupMemberResponse] = []
    creator: Optional[SteamUserResponse] = None


# Achievement Schemas
class AchievementBase(BaseModel):
    api_name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    icon_url: Optional[str] = None


class AchievementResponse(AchievementBase):
    id: UUID
    game_id: UUID
    hidden: bool = False
    global_percent: Optional[float] = None

    class Config:
        from_attributes = True


class UserAchievementResponse(BaseModel):
    id: UUID
    achievement: AchievementResponse
    achieved: bool
    unlock_time: Optional[datetime] = None

    class Config:
        from_attributes = True


# Backlog Schemas
class BacklogCreate(BaseModel):
    game_id: UUID
    status: BacklogStatus = BacklogStatus.BACKLOG
    priority: int = 0
    notes: Optional[str] = None


class BacklogUpdate(BaseModel):
    status: Optional[BacklogStatus] = None
    priority: Optional[int] = None
    notes: Optional[str] = None


class BacklogResponse(BaseModel):
    id: UUID
    game: GameResponse
    status: str
    priority: int
    notes: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Sync History Schemas
class SyncHistoryResponse(BaseModel):
    id: UUID
    sync_type: str
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    items_synced: int = 0
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ML Features Schemas
class MLFeaturesResponse(BaseModel):
    id: UUID
    total_games: int
    total_playtime: int
    avg_playtime_per_game: float
    games_played: int
    games_never_played: int
    completion_rate: float
    total_achievements: int
    achievement_rate: float
    favorite_genre: Optional[str] = None
    genre_diversity_score: float
    top_genres: Optional[dict] = None
    activity_score: float
    cluster_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Recommendation Schemas
class RecommendationResponse(BaseModel):
    id: UUID
    game: GameResponse
    recommendation_type: str
    score: float
    reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Comparison Schemas
class UserComparisonStats(BaseModel):
    user: SteamUserResponse
    total_playtime: int
    total_games: int
    games_played: int
    total_achievements: int
    completion_rate: float
    top_genres: List[dict] = []
    backlog_count: int = 0


class GroupComparisonResponse(BaseModel):
    group: GroupResponse
    members: List[UserComparisonStats]
    common_games: List[GameResponse] = []
    common_games_count: int = 0
    recommended_games: List[GameResponse] = []


# Game Intersection Schemas
class GameOwnership(BaseModel):
    game: GameResponse
    owners: List[SteamUserResponse]
    owner_count: int
    total_combined_playtime: int


class GameIntersectionResponse(BaseModel):
    group_id: UUID
    total_members: int
    games_owned_by_all: List[GameOwnership] = []
    games_owned_by_majority: List[GameOwnership] = []


# Dashboard Schemas
class DashboardStats(BaseModel):
    total_users: int
    total_groups: int
    total_games_tracked: int
    total_playtime_tracked: int
    total_achievements_tracked: int


class UserDashboard(BaseModel):
    user: SteamUserWithStats
    recent_games: List[UserGameResponse] = []
    top_played_games: List[UserGameResponse] = []
    recent_achievements: List[UserAchievementResponse] = []
    backlog_summary: dict = {}
    genre_distribution: List[dict] = []


# Pagination
class PaginatedResponse(BaseModel):
    items: List
    total: int
    page: int
    page_size: int
    total_pages: int
