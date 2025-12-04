from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
import json

from app.database import get_db
from app.models import SteamUser, MLPlayerFeatures, Recommendation
from app.schemas import MLFeaturesResponse, RecommendationResponse
from app.services.ml_service import MLService

router = APIRouter(prefix="/ml", tags=["Machine Learning"])


@router.post("/users/{user_id}/extract-features", response_model=MLFeaturesResponse)
def extract_user_features(user_id: UUID, db: Session = Depends(get_db)):
    """Extract ML features for a user."""
    user = db.query(SteamUser).filter(SteamUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    ml_service = MLService(db)
    features = ml_service.save_user_features(user_id)
    
    return features


@router.post("/extract-all-features")
def extract_all_features(db: Session = Depends(get_db)):
    """Extract ML features for all users."""
    users = db.query(SteamUser).all()
    
    ml_service = MLService(db)
    results = {"success": 0, "failed": 0}
    
    for user in users:
        try:
            ml_service.save_user_features(user.id)
            results["success"] += 1
        except Exception as e:
            results["failed"] += 1
            print(f"Error extracting features for {user.steam_id}: {e}")
    
    return results


@router.get("/users/{user_id}/features", response_model=MLFeaturesResponse)
def get_user_features(user_id: UUID, db: Session = Depends(get_db)):
    """Get ML features for a user."""
    features = db.query(MLPlayerFeatures).filter(
        MLPlayerFeatures.steam_user_id == user_id
    ).first()
    
    if not features:
        raise HTTPException(status_code=404, detail="Features not found. Run extract-features first.")
    
    return features


@router.post("/cluster")
def cluster_players(
    n_clusters: int = Query(5, ge=2, le=20),
    db: Session = Depends(get_db)
):
    """Cluster all players based on their features."""
    ml_service = MLService(db)
    result = ml_service.cluster_players(n_clusters)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.get("/clusters")
def get_clusters(db: Session = Depends(get_db)):
    """Get cluster analysis."""
    from sqlalchemy import func
    
    # Get cluster distribution
    clusters = db.query(
        MLPlayerFeatures.cluster_id,
        func.count(MLPlayerFeatures.id).label("count")
    ).filter(
        MLPlayerFeatures.cluster_id.isnot(None)
    ).group_by(MLPlayerFeatures.cluster_id).all()
    
    if not clusters:
        return {"message": "No clusters found. Run /cluster endpoint first."}
    
    # Get detailed analysis for each cluster
    ml_service = MLService(db)
    n_clusters = max(c.cluster_id for c in clusters) + 1
    analysis = ml_service._analyze_clusters(n_clusters)
    
    return {
        "total_clustered_users": sum(c.count for c in clusters),
        "n_clusters": len(clusters),
        "cluster_analysis": analysis
    }


@router.get("/users/{user_id}/cluster")
def get_user_cluster(user_id: UUID, db: Session = Depends(get_db)):
    """Get cluster info for a specific user."""
    features = db.query(MLPlayerFeatures).filter(
        MLPlayerFeatures.steam_user_id == user_id
    ).first()
    
    if not features:
        raise HTTPException(status_code=404, detail="User features not found")
    
    if features.cluster_id is None:
        return {"message": "User not yet assigned to a cluster. Run /cluster endpoint."}
    
    # Get cluster mates
    cluster_mates = db.query(MLPlayerFeatures).filter(
        MLPlayerFeatures.cluster_id == features.cluster_id,
        MLPlayerFeatures.steam_user_id != user_id
    ).limit(10).all()
    
    cluster_mate_users = []
    for mate in cluster_mates:
        user = db.query(SteamUser).filter(SteamUser.id == mate.steam_user_id).first()
        if user:
            cluster_mate_users.append({
                "user": user,
                "favorite_genre": mate.favorite_genre,
                "total_playtime_hours": mate.total_playtime // 60 if mate.total_playtime else 0
            })
    
    return {
        "cluster_id": features.cluster_id,
        "user_features": features,
        "similar_users": cluster_mate_users
    }


@router.get("/users/{user_id}/recommendations")
def get_recommendations(
    user_id: UUID,
    recommendation_type: str = Query("hybrid", enum=["collaborative", "content_based", "hybrid"]),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Get game recommendations for a user."""
    user = db.query(SteamUser).filter(SteamUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    ml_service = MLService(db)
    
    if recommendation_type == "collaborative":
        recommendations = ml_service.get_collaborative_recommendations(user_id, limit)
    elif recommendation_type == "content_based":
        recommendations = ml_service.get_content_based_recommendations(user_id, limit)
    else:
        recommendations = ml_service.get_hybrid_recommendations(user_id, limit)
    
    # Save recommendations
    if recommendations:
        ml_service.save_recommendations(user_id, recommendations)
    
    return {
        "user_id": str(user_id),
        "recommendation_type": recommendation_type,
        "recommendations": [
            {
                "game": {
                    "id": str(r["game"].id),
                    "app_id": r["game"].app_id,
                    "name": r["game"].name,
                    "header_image": r["game"].header_image
                },
                "score": round(r["score"], 4),
                "reason": r.get("reason")
            }
            for r in recommendations
        ]
    }


@router.get("/users/{user_id}/saved-recommendations", response_model=List[RecommendationResponse])
def get_saved_recommendations(user_id: UUID, db: Session = Depends(get_db)):
    """Get previously saved recommendations."""
    from app.models import Game
    
    recommendations = db.query(Recommendation).filter(
        Recommendation.steam_user_id == user_id
    ).order_by(Recommendation.score.desc()).all()
    
    results = []
    for rec in recommendations:
        game = db.query(Game).filter(Game.id == rec.game_id).first()
        if game:
            results.append(RecommendationResponse(
                id=rec.id,
                game=game,
                recommendation_type=rec.recommendation_type,
                score=rec.score,
                reason=rec.reason,
                created_at=rec.created_at
            ))
    
    return results


@router.get("/export-dataset")
def export_dataset(
    format: str = Query("json", enum=["json", "csv"]),
    db: Session = Depends(get_db)
):
    """Export ML dataset for external use."""
    ml_service = MLService(db)
    df = ml_service.export_dataset()
    
    if df.empty:
        raise HTTPException(status_code=404, detail="No data to export")
    
    if format == "csv":
        csv_content = df.to_csv(index=False)
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=steam_arena_dataset.csv"}
        )
    else:
        json_content = df.to_json(orient="records")
        return Response(
            content=json_content,
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=steam_arena_dataset.json"}
        )


@router.get("/feature-stats")
def get_feature_statistics(db: Session = Depends(get_db)):
    """Get statistics about the ML features dataset."""
    from sqlalchemy import func
    
    stats = db.query(
        func.count(MLPlayerFeatures.id).label("total_users"),
        func.avg(MLPlayerFeatures.total_games).label("avg_games"),
        func.avg(MLPlayerFeatures.total_playtime).label("avg_playtime"),
        func.avg(MLPlayerFeatures.completion_rate).label("avg_completion_rate"),
        func.avg(MLPlayerFeatures.genre_diversity_score).label("avg_diversity"),
        func.count(MLPlayerFeatures.id).filter(MLPlayerFeatures.cluster_id.isnot(None)).label("clustered_users")
    ).first()
    
    # Get favorite genre distribution
    genre_dist = db.query(
        MLPlayerFeatures.favorite_genre,
        func.count(MLPlayerFeatures.id).label("count")
    ).filter(
        MLPlayerFeatures.favorite_genre.isnot(None)
    ).group_by(MLPlayerFeatures.favorite_genre).order_by(
        func.count(MLPlayerFeatures.id).desc()
    ).limit(10).all()
    
    return {
        "total_users_with_features": stats.total_users or 0,
        "clustered_users": stats.clustered_users or 0,
        "averages": {
            "games_per_user": round(stats.avg_games or 0, 2),
            "playtime_hours": round((stats.avg_playtime or 0) / 60, 2),
            "completion_rate": round(stats.avg_completion_rate or 0, 2),
            "genre_diversity": round(stats.avg_diversity or 0, 4)
        },
        "top_favorite_genres": [
            {"genre": g.favorite_genre, "count": g.count}
            for g in genre_dist
        ]
    }
