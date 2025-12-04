import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Dict, Optional, Tuple
from uuid import UUID
from collections import Counter

from app.models import (
    SteamUser, Game, UserGame, Genre, GameGenre, 
    UserAchievement, MLPlayerFeatures, Recommendation
)


class MLService:
    """Service for ML-based features: clustering, feature extraction, recommendations."""
    
    def __init__(self, db: Session):
        self.db = db
        self.scaler = StandardScaler()
    
    def extract_user_features(self, user_id: UUID) -> Dict:
        """Extract features for a single user for ML purposes."""
        # Get basic game stats
        games_stats = self.db.query(
            func.count(UserGame.id).label("total_games"),
            func.sum(UserGame.playtime_forever).label("total_playtime"),
            func.count(UserGame.id).filter(UserGame.playtime_forever > 0).label("games_played"),
            func.count(UserGame.id).filter(UserGame.playtime_forever == 0).label("games_never_played"),
            func.avg(UserGame.playtime_forever).label("avg_playtime")
        ).filter(UserGame.steam_user_id == user_id).first()
        
        # Get achievement stats
        achievements_stats = self.db.query(
            func.count(UserAchievement.id).label("total"),
            func.count(UserAchievement.id).filter(UserAchievement.achieved.is_(True)).label("unlocked")
        ).filter(UserAchievement.steam_user_id == user_id).first()
        
        # Get genre distribution
        genre_distribution = self._get_genre_playtime_distribution(user_id)
        
        # Calculate activity score (based on recent playtime)
        recent_playtime = self.db.query(
            func.sum(UserGame.playtime_2weeks)
        ).filter(UserGame.steam_user_id == user_id).scalar() or 0
        
        # Calculate genre diversity (Shannon entropy-like measure)
        genre_diversity = self._calculate_genre_diversity(genre_distribution)
        
        # Calculate completion rate
        total_achievements = achievements_stats.total or 0
        unlocked_achievements = achievements_stats.unlocked or 0
        completion_rate = (unlocked_achievements / total_achievements * 100) if total_achievements > 0 else 0
        
        # Get favorite genre
        favorite_genre = max(genre_distribution.items(), key=lambda x: x[1])[0] if genre_distribution else None
        
        features = {
            "total_games": games_stats.total_games or 0,
            "total_playtime": games_stats.total_playtime or 0,
            "avg_playtime_per_game": float(games_stats.avg_playtime or 0),
            "games_played": games_stats.games_played or 0,
            "games_never_played": games_stats.games_never_played or 0,
            "completion_rate": completion_rate,
            "total_achievements": total_achievements,
            "achievement_rate": (unlocked_achievements / total_achievements) if total_achievements > 0 else 0,
            "favorite_genre": favorite_genre,
            "genre_diversity_score": genre_diversity,
            "top_genres": genre_distribution,
            "activity_score": min(recent_playtime / 100, 100) if recent_playtime else 0,  # Normalize
        }
        
        return features
    
    def _get_genre_playtime_distribution(self, user_id: UUID) -> Dict[str, int]:
        """Get genre distribution weighted by playtime."""
        results = self.db.query(
            Genre.name,
            func.sum(UserGame.playtime_forever).label("total_playtime")
        ).join(
            GameGenre, Genre.id == GameGenre.genre_id
        ).join(
            Game, GameGenre.game_id == Game.id
        ).join(
            UserGame, Game.id == UserGame.game_id
        ).filter(
            UserGame.steam_user_id == user_id
        ).group_by(Genre.name).all()
        
        return {r.name: r.total_playtime or 0 for r in results}
    
    def _calculate_genre_diversity(self, genre_distribution: Dict[str, int]) -> float:
        """Calculate genre diversity score (entropy-based)."""
        if not genre_distribution:
            return 0.0
        
        total = sum(genre_distribution.values())
        if total == 0:
            return 0.0
        
        proportions = [v / total for v in genre_distribution.values()]
        # Shannon entropy
        entropy = -sum(p * np.log(p + 1e-10) for p in proportions if p > 0)
        # Normalize by max possible entropy
        max_entropy = np.log(len(genre_distribution))
        
        return entropy / max_entropy if max_entropy > 0 else 0.0
    
    def save_user_features(self, user_id: UUID) -> MLPlayerFeatures:
        """Extract and save features for a user."""
        features = self.extract_user_features(user_id)
        
        # Check if features exist
        ml_features = self.db.query(MLPlayerFeatures).filter(
            MLPlayerFeatures.steam_user_id == user_id
        ).first()
        
        # Create feature vector for clustering
        feature_vector = [
            features["total_games"],
            features["total_playtime"] / 60,  # Convert to hours
            features["avg_playtime_per_game"],
            features["games_played"],
            features["completion_rate"],
            features["achievement_rate"] * 100,
            features["genre_diversity_score"] * 100,
            features["activity_score"]
        ]
        
        if ml_features:
            for key, value in features.items():
                if key not in ["top_genres"]:
                    setattr(ml_features, key, value)
            ml_features.top_genres = features["top_genres"]
            ml_features.feature_vector = feature_vector
        else:
            ml_features = MLPlayerFeatures(
                steam_user_id=user_id,
                **{k: v for k, v in features.items() if k != "top_genres"},
                top_genres=features["top_genres"],
                feature_vector=feature_vector
            )
            self.db.add(ml_features)
        
        self.db.commit()
        self.db.refresh(ml_features)
        return ml_features
    
    def cluster_players(self, n_clusters: int = 5) -> Dict:
        """Cluster all players based on their features."""
        # Get all users with features
        all_features = self.db.query(MLPlayerFeatures).all()
        
        if len(all_features) < n_clusters:
            return {"error": f"Not enough users for {n_clusters} clusters. Have {len(all_features)} users."}
        
        # Prepare feature matrix
        user_ids = []
        feature_matrix = []
        
        for f in all_features:
            if f.feature_vector:
                user_ids.append(f.steam_user_id)
                feature_matrix.append(f.feature_vector)
        
        if not feature_matrix:
            return {"error": "No feature vectors found"}
        
        X = np.array(feature_matrix)
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Apply K-Means
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        clusters = kmeans.fit_predict(X_scaled)
        
        # Save cluster assignments
        for user_id, cluster_id in zip(user_ids, clusters):
            ml_features = self.db.query(MLPlayerFeatures).filter(
                MLPlayerFeatures.steam_user_id == user_id
            ).first()
            if ml_features:
                ml_features.cluster_id = int(cluster_id)
        
        self.db.commit()
        
        # Analyze clusters
        cluster_analysis = self._analyze_clusters(n_clusters)
        
        return {
            "n_clusters": n_clusters,
            "total_users_clustered": len(user_ids),
            "cluster_analysis": cluster_analysis
        }
    
    def _analyze_clusters(self, n_clusters: int) -> List[Dict]:
        """Analyze cluster characteristics."""
        analysis = []
        
        for cluster_id in range(n_clusters):
            cluster_users = self.db.query(MLPlayerFeatures).filter(
                MLPlayerFeatures.cluster_id == cluster_id
            ).all()
            
            if not cluster_users:
                continue
            
            # Calculate cluster statistics
            avg_playtime = np.mean([u.total_playtime or 0 for u in cluster_users])
            avg_games = np.mean([u.total_games or 0 for u in cluster_users])
            avg_completion = np.mean([u.completion_rate or 0 for u in cluster_users])
            avg_diversity = np.mean([u.genre_diversity_score or 0 for u in cluster_users])
            
            # Find common top genres
            all_top_genres = []
            for u in cluster_users:
                if u.top_genres:
                    top = sorted(u.top_genres.items(), key=lambda x: x[1], reverse=True)[:3]
                    all_top_genres.extend([g[0] for g in top])
            
            common_genres = Counter(all_top_genres).most_common(5)
            
            # Determine cluster type
            cluster_type = self._determine_cluster_type(
                avg_playtime, avg_games, avg_completion, avg_diversity
            )
            
            analysis.append({
                "cluster_id": cluster_id,
                "user_count": len(cluster_users),
                "avg_playtime_hours": avg_playtime / 60,
                "avg_games": avg_games,
                "avg_completion_rate": avg_completion,
                "avg_genre_diversity": avg_diversity,
                "common_genres": common_genres,
                "cluster_type": cluster_type
            })
        
        return analysis
    
    def _determine_cluster_type(
        self, 
        avg_playtime: float, 
        avg_games: float, 
        avg_completion: float,
        avg_diversity: float
    ) -> str:
        """Determine a descriptive type for a cluster."""
        if avg_playtime > 50000 and avg_completion > 50:
            return "Hardcore Completionist"
        elif avg_playtime > 30000 and avg_diversity > 0.7:
            return "Diverse Explorer"
        elif avg_playtime > 30000:
            return "Dedicated Gamer"
        elif avg_games > 200 and avg_playtime < 10000:
            return "Collector"
        elif avg_completion > 60:
            return "Achievement Hunter"
        elif avg_diversity > 0.8:
            return "Genre Explorer"
        elif avg_playtime < 5000:
            return "Casual Player"
        else:
            return "Regular Gamer"
    
    def get_collaborative_recommendations(
        self, 
        user_id: UUID, 
        n_recommendations: int = 10
    ) -> List[Dict]:
        """Generate game recommendations based on similar users."""
        # Get user's features
        user_features = self.db.query(MLPlayerFeatures).filter(
            MLPlayerFeatures.steam_user_id == user_id
        ).first()
        
        if not user_features or not user_features.feature_vector:
            return []
        
        # Get users in same cluster
        similar_users = self.db.query(MLPlayerFeatures).filter(
            and_(
                MLPlayerFeatures.cluster_id == user_features.cluster_id,
                MLPlayerFeatures.steam_user_id != user_id
            )
        ).all()
        
        if not similar_users:
            # Fallback: use all users with features
            similar_users = self.db.query(MLPlayerFeatures).filter(
                MLPlayerFeatures.steam_user_id != user_id
            ).limit(50).all()
        
        # Calculate similarity scores
        user_vector = np.array(user_features.feature_vector).reshape(1, -1)
        similarities = []
        
        for su in similar_users:
            if su.feature_vector:
                su_vector = np.array(su.feature_vector).reshape(1, -1)
                sim = cosine_similarity(user_vector, su_vector)[0][0]
                similarities.append((su.steam_user_id, sim))
        
        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)
        top_similar = similarities[:10]
        
        # Get user's games
        user_games = set(
            ug.game_id for ug in self.db.query(UserGame).filter(
                UserGame.steam_user_id == user_id
            ).all()
        )
        
        # Find games from similar users that user doesn't own
        game_scores = Counter()
        
        for similar_user_id, similarity in top_similar:
            similar_user_games = self.db.query(UserGame).filter(
                and_(
                    UserGame.steam_user_id == similar_user_id,
                    UserGame.playtime_forever > 60  # At least 1 hour played
                )
            ).all()
            
            for ug in similar_user_games:
                if ug.game_id not in user_games:
                    # Weight by similarity and playtime
                    score = similarity * np.log1p(ug.playtime_forever)
                    game_scores[ug.game_id] += score
        
        # Get top recommended games
        recommendations = []
        for game_id, score in game_scores.most_common(n_recommendations):
            game = self.db.query(Game).filter(Game.id == game_id).first()
            if game:
                recommendations.append({
                    "game": game,
                    "score": score,
                    "recommendation_type": "collaborative",
                    "reason": "Based on games played by similar users"
                })
        
        return recommendations
    
    def get_content_based_recommendations(
        self, 
        user_id: UUID, 
        n_recommendations: int = 10
    ) -> List[Dict]:
        """Generate recommendations based on user's genre preferences."""
        # Get user's genre distribution
        genre_dist = self._get_genre_playtime_distribution(user_id)
        
        if not genre_dist:
            return []
        
        # Get user's games
        user_games = set(
            ug.game_id for ug in self.db.query(UserGame).filter(
                UserGame.steam_user_id == user_id
            ).all()
        )
        
        # Find games matching top genres that user doesn't own
        top_genres = sorted(genre_dist.items(), key=lambda x: x[1], reverse=True)[:5]
        top_genre_names = [g[0] for g in top_genres]
        
        # Get genres by name
        genres = self.db.query(Genre).filter(Genre.name.in_(top_genre_names)).all()
        genre_ids = [g.id for g in genres]
        
        # Find games with these genres, ordered by metacritic score
        potential_games = self.db.query(Game).join(
            GameGenre, Game.id == GameGenre.game_id
        ).filter(
            and_(
                GameGenre.genre_id.in_(genre_ids),
                Game.id.notin_(user_games),
                Game.metacritic_score.isnot(None)
            )
        ).order_by(Game.metacritic_score.desc()).limit(50).all()
        
        # Score games by genre match
        recommendations = []
        seen_games = set()
        
        for game in potential_games:
            if game.id in seen_games:
                continue
            seen_games.add(game.id)
            
            # Get game's genres
            game_genres = self.db.query(Genre.name).join(
                GameGenre, Genre.id == GameGenre.genre_id
            ).filter(GameGenre.game_id == game.id).all()
            game_genre_names = [g.name for g in game_genres]
            
            # Calculate match score
            match_count = len(set(game_genre_names) & set(top_genre_names))
            score = match_count * (game.metacritic_score or 50) / 100
            
            recommendations.append({
                "game": game,
                "score": score,
                "recommendation_type": "content_based",
                "reason": f"Matches your favorite genres: {', '.join(set(game_genre_names) & set(top_genre_names))}"
            })
        
        # Sort by score
        recommendations.sort(key=lambda x: x["score"], reverse=True)
        
        return recommendations[:n_recommendations]
    
    def get_hybrid_recommendations(
        self, 
        user_id: UUID, 
        n_recommendations: int = 10
    ) -> List[Dict]:
        """Combine collaborative and content-based recommendations."""
        collaborative = self.get_collaborative_recommendations(user_id, n_recommendations)
        content_based = self.get_content_based_recommendations(user_id, n_recommendations)
        
        # Merge and deduplicate
        all_recs = {}
        
        for rec in collaborative:
            game_id = rec["game"].id
            all_recs[game_id] = {
                **rec,
                "score": rec["score"],
                "recommendation_type": "hybrid"
            }
        
        for rec in content_based:
            game_id = rec["game"].id
            if game_id in all_recs:
                # Combine scores
                all_recs[game_id]["score"] += rec["score"]
                all_recs[game_id]["reason"] = f"{all_recs[game_id]['reason']}; {rec['reason']}"
            else:
                all_recs[game_id] = {
                    **rec,
                    "recommendation_type": "hybrid"
                }
        
        # Sort and return top N
        sorted_recs = sorted(all_recs.values(), key=lambda x: x["score"], reverse=True)
        return sorted_recs[:n_recommendations]
    
    def save_recommendations(self, user_id: UUID, recommendations: List[Dict]):
        """Save recommendations to database."""
        # Clear old recommendations
        self.db.query(Recommendation).filter(
            Recommendation.steam_user_id == user_id
        ).delete()
        
        # Add new recommendations
        for rec in recommendations:
            recommendation = Recommendation(
                steam_user_id=user_id,
                game_id=rec["game"].id,
                recommendation_type=rec["recommendation_type"],
                score=rec["score"],
                reason=rec.get("reason")
            )
            self.db.add(recommendation)
        
        self.db.commit()
    
    def export_dataset(self) -> pd.DataFrame:
        """Export user features as a pandas DataFrame for external ML use."""
        features = self.db.query(MLPlayerFeatures).all()
        
        data = []
        for f in features:
            row = {
                "user_id": str(f.steam_user_id),
                "total_games": f.total_games,
                "total_playtime": f.total_playtime,
                "avg_playtime_per_game": f.avg_playtime_per_game,
                "games_played": f.games_played,
                "games_never_played": f.games_never_played,
                "completion_rate": f.completion_rate,
                "total_achievements": f.total_achievements,
                "achievement_rate": f.achievement_rate,
                "favorite_genre": f.favorite_genre,
                "genre_diversity_score": f.genre_diversity_score,
                "activity_score": f.activity_score,
                "cluster_id": f.cluster_id
            }
            data.append(row)
        
        return pd.DataFrame(data)
