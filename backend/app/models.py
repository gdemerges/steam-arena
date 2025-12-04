from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base


class SteamUser(Base):
    __tablename__ = "steam_users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    steam_id = Column(String(20), unique=True, nullable=False, index=True)
    persona_name = Column(String(255))
    profile_url = Column(Text)
    avatar_url = Column(Text)
    avatar_medium_url = Column(Text)
    avatar_full_url = Column(Text)
    country_code = Column(String(10))
    time_created = Column(DateTime)
    last_logoff = Column(DateTime)
    profile_state = Column(Integer)
    community_visibility_state = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    games = relationship("UserGame", back_populates="user", cascade="all, delete-orphan")
    achievements = relationship("UserAchievement", back_populates="user", cascade="all, delete-orphan")
    backlog = relationship("UserBacklog", back_populates="user", cascade="all, delete-orphan")
    group_memberships = relationship("GroupMember", back_populates="user", cascade="all, delete-orphan")
    ml_features = relationship("MLPlayerFeatures", back_populates="user", uselist=False)
    recommendations = relationship("Recommendation", back_populates="user", cascade="all, delete-orphan")
    sync_history = relationship("SyncHistory", back_populates="user", cascade="all, delete-orphan")


class UserGroup(Base):
    __tablename__ = "user_groups"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    created_by = Column(UUID(as_uuid=True), ForeignKey("steam_users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    members = relationship("GroupMember", back_populates="group", cascade="all, delete-orphan")
    creator = relationship("SteamUser", foreign_keys=[created_by])


class GroupMember(Base):
    __tablename__ = "group_members"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(UUID(as_uuid=True), ForeignKey("user_groups.id", ondelete="CASCADE"), index=True)
    steam_user_id = Column(UUID(as_uuid=True), ForeignKey("steam_users.id", ondelete="CASCADE"), index=True)
    added_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    group = relationship("UserGroup", back_populates="members")
    user = relationship("SteamUser", back_populates="group_memberships")


class Game(Base):
    __tablename__ = "games"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    app_id = Column(Integer, unique=True, nullable=False, index=True)
    name = Column(String(500), nullable=False)
    img_icon_url = Column(Text)
    img_logo_url = Column(Text)
    header_image = Column(Text)
    short_description = Column(Text)
    detailed_description = Column(Text)
    about_the_game = Column(Text)
    release_date = Column(DateTime)
    developer = Column(String(500))
    publisher = Column(String(500))
    price_initial = Column(Integer)
    price_final = Column(Integer)
    discount_percent = Column(Integer)
    is_free = Column(Boolean, default=False)
    metacritic_score = Column(Integer)
    metacritic_url = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user_games = relationship("UserGame", back_populates="game", cascade="all, delete-orphan")
    achievements = relationship("Achievement", back_populates="game", cascade="all, delete-orphan")
    genres = relationship("GameGenre", back_populates="game", cascade="all, delete-orphan")
    categories = relationship("GameCategory", back_populates="game", cascade="all, delete-orphan")
    backlog_entries = relationship("UserBacklog", back_populates="game", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="game", cascade="all, delete-orphan")


class Genre(Base):
    __tablename__ = "genres"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    steam_genre_id = Column(Integer, unique=True)
    name = Column(String(100), nullable=False)
    
    # Relationships
    games = relationship("GameGenre", back_populates="genre")


class GameGenre(Base):
    __tablename__ = "game_genres"
    
    game_id = Column(UUID(as_uuid=True), ForeignKey("games.id", ondelete="CASCADE"), primary_key=True)
    genre_id = Column(UUID(as_uuid=True), ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True)
    
    # Relationships
    game = relationship("Game", back_populates="genres")
    genre = relationship("Genre", back_populates="games")


class Category(Base):
    __tablename__ = "categories"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    steam_category_id = Column(Integer, unique=True)
    name = Column(String(100), nullable=False)
    
    # Relationships
    games = relationship("GameCategory", back_populates="category")


class GameCategory(Base):
    __tablename__ = "game_categories"
    
    game_id = Column(UUID(as_uuid=True), ForeignKey("games.id", ondelete="CASCADE"), primary_key=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True)
    
    # Relationships
    game = relationship("Game", back_populates="categories")
    category = relationship("Category", back_populates="games")


class UserGame(Base):
    __tablename__ = "user_games"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    steam_user_id = Column(UUID(as_uuid=True), ForeignKey("steam_users.id", ondelete="CASCADE"), index=True)
    game_id = Column(UUID(as_uuid=True), ForeignKey("games.id", ondelete="CASCADE"), index=True)
    playtime_forever = Column(Integer, default=0)  # in minutes
    playtime_2weeks = Column(Integer, default=0)
    playtime_windows = Column(Integer, default=0)
    playtime_mac = Column(Integer, default=0)
    playtime_linux = Column(Integer, default=0)
    rtime_last_played = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("SteamUser", back_populates="games")
    game = relationship("Game", back_populates="user_games")


class Achievement(Base):
    __tablename__ = "achievements"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    game_id = Column(UUID(as_uuid=True), ForeignKey("games.id", ondelete="CASCADE"), index=True)
    api_name = Column(String(255), nullable=False)
    display_name = Column(String(500))
    description = Column(Text)
    icon_url = Column(Text)
    icon_gray_url = Column(Text)
    hidden = Column(Boolean, default=False)
    global_percent = Column(Float)
    
    # Relationships
    game = relationship("Game", back_populates="achievements")
    user_achievements = relationship("UserAchievement", back_populates="achievement", cascade="all, delete-orphan")


class UserAchievement(Base):
    __tablename__ = "user_achievements"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    steam_user_id = Column(UUID(as_uuid=True), ForeignKey("steam_users.id", ondelete="CASCADE"), index=True)
    achievement_id = Column(UUID(as_uuid=True), ForeignKey("achievements.id", ondelete="CASCADE"))
    achieved = Column(Boolean, default=False)
    unlock_time = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("SteamUser", back_populates="achievements")
    achievement = relationship("Achievement", back_populates="user_achievements")


class UserBacklog(Base):
    __tablename__ = "user_backlog"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    steam_user_id = Column(UUID(as_uuid=True), ForeignKey("steam_users.id", ondelete="CASCADE"))
    game_id = Column(UUID(as_uuid=True), ForeignKey("games.id", ondelete="CASCADE"))
    status = Column(String(50), default="backlog")  # backlog, playing, completed, abandoned, wishlist
    priority = Column(Integer, default=0)
    notes = Column(Text)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("SteamUser", back_populates="backlog")
    game = relationship("Game", back_populates="backlog_entries")


class SyncHistory(Base):
    __tablename__ = "sync_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    steam_user_id = Column(UUID(as_uuid=True), ForeignKey("steam_users.id", ondelete="CASCADE"), index=True)
    sync_type = Column(String(50), nullable=False)  # profile, games, achievements, friends
    status = Column(String(20), default="pending")  # pending, in_progress, completed, failed
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    error_message = Column(Text)
    items_synced = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("SteamUser", back_populates="sync_history")


class MLPlayerFeatures(Base):
    __tablename__ = "ml_player_features"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    steam_user_id = Column(UUID(as_uuid=True), ForeignKey("steam_users.id", ondelete="CASCADE"), unique=True)
    total_games = Column(Integer, default=0)
    total_playtime = Column(Integer, default=0)
    avg_playtime_per_game = Column(Float, default=0)
    games_played = Column(Integer, default=0)
    games_never_played = Column(Integer, default=0)
    completion_rate = Column(Float, default=0)
    total_achievements = Column(Integer, default=0)
    achievement_rate = Column(Float, default=0)
    favorite_genre = Column(String(100))
    genre_diversity_score = Column(Float, default=0)
    top_genres = Column(JSONB)
    playtime_distribution = Column(JSONB)
    activity_score = Column(Float, default=0)
    cluster_id = Column(Integer, index=True)
    feature_vector = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("SteamUser", back_populates="ml_features")


class Recommendation(Base):
    __tablename__ = "recommendations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    steam_user_id = Column(UUID(as_uuid=True), ForeignKey("steam_users.id", ondelete="CASCADE"), index=True)
    game_id = Column(UUID(as_uuid=True), ForeignKey("games.id", ondelete="CASCADE"))
    recommendation_type = Column(String(50))  # collaborative, content_based, hybrid
    score = Column(Float)
    reason = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("SteamUser", back_populates="recommendations")
    game = relationship("Game", back_populates="recommendations")
