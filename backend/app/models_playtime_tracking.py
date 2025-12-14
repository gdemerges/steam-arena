# Extension des models pour le tracking historique du playtime
# À ajouter dans models.py

class PlaytimeHistory(Base):
    """
    Table pour tracker l'historique du temps de jeu.
    Permet de calculer le temps joué par an/mois en comparant les snapshots.
    """
    __tablename__ = "playtime_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    steam_user_id = Column(UUID(as_uuid=True), ForeignKey("steam_users.id", ondelete="CASCADE"), index=True)
    game_id = Column(UUID(as_uuid=True), ForeignKey("games.id", ondelete="CASCADE"), index=True)
    playtime_forever = Column(Integer, default=0)  # Snapshot du total à ce moment
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)  # Timestamp du snapshot
    year = Column(Integer, index=True)  # Année pour faciliter les requêtes
    month = Column(Integer, index=True)  # Mois pour faciliter les requêtes
    
    # Relationships
    user = relationship("SteamUser")
    game = relationship("Game")
    
    # Index composite pour performances
    __table_args__ = (
        Index('idx_user_game_date', 'steam_user_id', 'game_id', 'recorded_at'),
        Index('idx_user_year', 'steam_user_id', 'year'),
    )


class UserYearlyStats(Base):
    """
    Table agrégée pour les stats annuelles d'un utilisateur.
    Pré-calculée pour performances optimales.
    """
    __tablename__ = "user_yearly_stats"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    steam_user_id = Column(UUID(as_uuid=True), ForeignKey("steam_users.id", ondelete="CASCADE"), index=True)
    year = Column(Integer, nullable=False, index=True)
    total_playtime_minutes = Column(Integer, default=0)
    total_playtime_hours = Column(Float, default=0.0)
    games_played_count = Column(Integer, default=0)
    new_games_count = Column(Integer, default=0)  # Jeux ajoutés cette année
    achievements_unlocked = Column(Integer, default=0)
    most_played_game_id = Column(UUID(as_uuid=True), ForeignKey("games.id"))
    most_played_playtime = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("SteamUser")
    most_played_game = relationship("Game")
    
    __table_args__ = (
        Index('idx_user_year_unique', 'steam_user_id', 'year', unique=True),
    )
