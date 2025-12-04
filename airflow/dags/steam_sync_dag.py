"""
Steam Arena - Airflow DAG for syncing Steam user data.

This DAG:
1. Takes a list of Steam IDs as input
2. Creates tasks to sync each user's data
3. Stores everything in the PostgreSQL database
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import Variable
import os
import requests
import psycopg2
from psycopg2.extras import execute_values
import json


# Configuration
STEAM_API_KEY = os.environ.get('STEAM_API_KEY', Variable.get('steam_api_key', default_var=''))
DATABASE_URL = os.environ.get('DATABASE_URL', Variable.get('database_url', default_var='postgresql://steam_arena:steam_arena_secret@postgres:5432/steam_arena'))

# Default args for the DAG
default_args = {
    'owner': 'steam_arena',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}


def get_db_connection():
    """Create database connection."""
    return psycopg2.connect(DATABASE_URL)


def fetch_player_summary(steam_id: str) -> dict:
    """Fetch player summary from Steam API."""
    url = f"https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/"
    params = {'key': STEAM_API_KEY, 'steamids': steam_id}
    
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    
    data = response.json()
    players = data.get('response', {}).get('players', [])
    return players[0] if players else None


def fetch_owned_games(steam_id: str) -> list:
    """Fetch owned games from Steam API."""
    url = f"https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"
    params = {
        'key': STEAM_API_KEY,
        'steamid': steam_id,
        'include_played_free_games': True,
        'include_appinfo': True,
        'format': 'json'
    }
    
    response = requests.get(url, params=params, timeout=60)
    response.raise_for_status()
    
    data = response.json()
    return data.get('response', {}).get('games', [])


def fetch_player_achievements(steam_id: str, app_id: int) -> dict:
    """Fetch player achievements for a specific game."""
    url = f"https://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v1/"
    params = {
        'key': STEAM_API_KEY,
        'steamid': steam_id,
        'appid': app_id,
        'l': 'english'
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json().get('playerstats', {})
    except Exception:
        return {}


def sync_user_profile(**context):
    """Sync a single user's profile."""
    steam_id = context['params'].get('steam_id')
    if not steam_id:
        raise ValueError("steam_id is required")
    
    player_data = fetch_player_summary(steam_id)
    if not player_data:
        print(f"Could not fetch data for Steam ID: {steam_id}")
        return None
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Insert or update user
        cur.execute("""
            INSERT INTO steam_users (
                steam_id, persona_name, profile_url, avatar_url, 
                avatar_medium_url, avatar_full_url, country_code,
                time_created, last_logoff, profile_state, 
                community_visibility_state, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s,
                to_timestamp(%s), to_timestamp(%s), %s, %s, NOW()
            )
            ON CONFLICT (steam_id) DO UPDATE SET
                persona_name = EXCLUDED.persona_name,
                profile_url = EXCLUDED.profile_url,
                avatar_url = EXCLUDED.avatar_url,
                avatar_medium_url = EXCLUDED.avatar_medium_url,
                avatar_full_url = EXCLUDED.avatar_full_url,
                country_code = EXCLUDED.country_code,
                last_logoff = EXCLUDED.last_logoff,
                profile_state = EXCLUDED.profile_state,
                community_visibility_state = EXCLUDED.community_visibility_state,
                updated_at = NOW()
            RETURNING id
        """, (
            player_data.get('steamid'),
            player_data.get('personaname'),
            player_data.get('profileurl'),
            player_data.get('avatar'),
            player_data.get('avatarmedium'),
            player_data.get('avatarfull'),
            player_data.get('loccountrycode'),
            player_data.get('timecreated'),
            player_data.get('lastlogoff'),
            player_data.get('profilestate'),
            player_data.get('communityvisibilitystate')
        ))
        
        user_id = cur.fetchone()[0]
        conn.commit()
        
        # Log sync
        cur.execute("""
            INSERT INTO sync_history (steam_user_id, sync_type, status, started_at, completed_at, items_synced)
            VALUES (%s, 'profile', 'completed', NOW(), NOW(), 1)
        """, (user_id,))
        conn.commit()
        
        print(f"Successfully synced profile for {player_data.get('personaname')} ({steam_id})")
        return str(user_id)
        
    except Exception as e:
        conn.rollback()
        print(f"Error syncing profile for {steam_id}: {e}")
        raise
    finally:
        cur.close()
        conn.close()


def sync_user_games(**context):
    """Sync a user's game library."""
    steam_id = context['params'].get('steam_id')
    if not steam_id:
        raise ValueError("steam_id is required")
    
    games_data = fetch_owned_games(steam_id)
    if not games_data:
        print(f"No games found for Steam ID: {steam_id}")
        return 0
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Get user ID
        cur.execute("SELECT id FROM steam_users WHERE steam_id = %s", (steam_id,))
        result = cur.fetchone()
        if not result:
            print(f"User not found: {steam_id}")
            return 0
        user_id = result[0]
        
        games_synced = 0
        
        for game_data in games_data:
            app_id = game_data.get('appid')
            name = game_data.get('name', f'Unknown Game {app_id}')
            
            # Insert or update game
            img_icon = game_data.get('img_icon_url')
            icon_url = f"https://media.steampowered.com/steamcommunity/public/images/apps/{app_id}/{img_icon}.jpg" if img_icon else None
            
            cur.execute("""
                INSERT INTO games (app_id, name, img_icon_url, updated_at)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (app_id) DO UPDATE SET
                    name = COALESCE(EXCLUDED.name, games.name),
                    img_icon_url = COALESCE(EXCLUDED.img_icon_url, games.img_icon_url),
                    updated_at = NOW()
                RETURNING id
            """, (app_id, name, icon_url))
            
            game_id = cur.fetchone()[0]
            
            # Insert or update user_game
            rtime_last_played = game_data.get('rtime_last_played')
            
            cur.execute("""
                INSERT INTO user_games (
                    steam_user_id, game_id, playtime_forever, playtime_2weeks,
                    playtime_windows, playtime_mac, playtime_linux,
                    rtime_last_played, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, to_timestamp(%s), NOW())
                ON CONFLICT (steam_user_id, game_id) DO UPDATE SET
                    playtime_forever = EXCLUDED.playtime_forever,
                    playtime_2weeks = EXCLUDED.playtime_2weeks,
                    playtime_windows = EXCLUDED.playtime_windows,
                    playtime_mac = EXCLUDED.playtime_mac,
                    playtime_linux = EXCLUDED.playtime_linux,
                    rtime_last_played = EXCLUDED.rtime_last_played,
                    updated_at = NOW()
            """, (
                user_id,
                game_id,
                game_data.get('playtime_forever', 0),
                game_data.get('playtime_2weeks', 0),
                game_data.get('playtime_windows_forever', 0),
                game_data.get('playtime_mac_forever', 0),
                game_data.get('playtime_linux_forever', 0),
                rtime_last_played if rtime_last_played else None
            ))
            
            games_synced += 1
        
        conn.commit()
        
        # Log sync
        cur.execute("""
            INSERT INTO sync_history (steam_user_id, sync_type, status, started_at, completed_at, items_synced)
            VALUES (%s, 'games', 'completed', NOW(), NOW(), %s)
        """, (user_id, games_synced))
        conn.commit()
        
        print(f"Successfully synced {games_synced} games for {steam_id}")
        return games_synced
        
    except Exception as e:
        conn.rollback()
        print(f"Error syncing games for {steam_id}: {e}")
        raise
    finally:
        cur.close()
        conn.close()


def sync_user_achievements(**context):
    """Sync achievements for all games of a user."""
    steam_id = context['params'].get('steam_id')
    if not steam_id:
        raise ValueError("steam_id is required")
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Get user ID and their games
        cur.execute("""
            SELECT su.id, g.app_id 
            FROM steam_users su
            JOIN user_games ug ON su.id = ug.steam_user_id
            JOIN games g ON ug.game_id = g.id
            WHERE su.steam_id = %s AND ug.playtime_forever > 0
            LIMIT 50
        """, (steam_id,))
        
        results = cur.fetchall()
        if not results:
            print(f"No played games found for {steam_id}")
            return 0
        
        user_id = results[0][0]
        app_ids = [r[1] for r in results]
        
        total_achievements = 0
        
        for app_id in app_ids:
            achievements_data = fetch_player_achievements(steam_id, app_id)
            if not achievements_data or 'achievements' not in achievements_data:
                continue
            
            # Get game ID
            cur.execute("SELECT id FROM games WHERE app_id = %s", (app_id,))
            game_result = cur.fetchone()
            if not game_result:
                continue
            game_id = game_result[0]
            
            for ach in achievements_data['achievements']:
                api_name = ach.get('apiname')
                achieved = ach.get('achieved', 0) == 1
                unlock_time = ach.get('unlocktime')
                
                # Insert or update achievement
                cur.execute("""
                    INSERT INTO achievements (game_id, api_name, display_name)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (game_id, api_name) DO UPDATE SET
                        display_name = COALESCE(EXCLUDED.display_name, achievements.display_name)
                    RETURNING id
                """, (game_id, api_name, ach.get('name')))
                
                achievement_id = cur.fetchone()[0]
                
                # Insert or update user achievement
                cur.execute("""
                    INSERT INTO user_achievements (steam_user_id, achievement_id, achieved, unlock_time)
                    VALUES (%s, %s, %s, to_timestamp(%s))
                    ON CONFLICT (steam_user_id, achievement_id) DO UPDATE SET
                        achieved = EXCLUDED.achieved,
                        unlock_time = EXCLUDED.unlock_time
                """, (user_id, achievement_id, achieved, unlock_time if unlock_time else None))
                
                total_achievements += 1
        
        conn.commit()
        
        # Log sync
        cur.execute("""
            INSERT INTO sync_history (steam_user_id, sync_type, status, started_at, completed_at, items_synced)
            VALUES (%s, 'achievements', 'completed', NOW(), NOW(), %s)
        """, (user_id, total_achievements))
        conn.commit()
        
        print(f"Successfully synced {total_achievements} achievements for {steam_id}")
        return total_achievements
        
    except Exception as e:
        conn.rollback()
        print(f"Error syncing achievements for {steam_id}: {e}")
        raise
    finally:
        cur.close()
        conn.close()


def extract_ml_features(**context):
    """Extract ML features for a user."""
    steam_id = context['params'].get('steam_id')
    if not steam_id:
        raise ValueError("steam_id is required")
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Get user stats
        cur.execute("""
            WITH user_stats AS (
                SELECT 
                    su.id as user_id,
                    COUNT(DISTINCT ug.game_id) as total_games,
                    COALESCE(SUM(ug.playtime_forever), 0) as total_playtime,
                    COALESCE(AVG(ug.playtime_forever), 0) as avg_playtime,
                    COUNT(DISTINCT ug.game_id) FILTER (WHERE ug.playtime_forever > 0) as games_played,
                    COUNT(DISTINCT ug.game_id) FILTER (WHERE ug.playtime_forever = 0) as games_never_played,
                    COALESCE(SUM(ug.playtime_2weeks), 0) as recent_playtime
                FROM steam_users su
                LEFT JOIN user_games ug ON su.id = ug.steam_user_id
                WHERE su.steam_id = %s
                GROUP BY su.id
            ),
            achievement_stats AS (
                SELECT 
                    su.id as user_id,
                    COUNT(ua.id) as total_achievements,
                    COUNT(ua.id) FILTER (WHERE ua.achieved = true) as unlocked_achievements
                FROM steam_users su
                LEFT JOIN user_achievements ua ON su.id = ua.steam_user_id
                WHERE su.steam_id = %s
                GROUP BY su.id
            ),
            genre_stats AS (
                SELECT 
                    su.id as user_id,
                    g.name as genre_name,
                    SUM(ug.playtime_forever) as genre_playtime
                FROM steam_users su
                JOIN user_games ug ON su.id = ug.steam_user_id
                JOIN game_genres gg ON ug.game_id = gg.game_id
                JOIN genres g ON gg.genre_id = g.id
                WHERE su.steam_id = %s
                GROUP BY su.id, g.name
                ORDER BY genre_playtime DESC
                LIMIT 5
            )
            SELECT 
                us.user_id,
                us.total_games,
                us.total_playtime,
                us.avg_playtime,
                us.games_played,
                us.games_never_played,
                us.recent_playtime,
                ast.total_achievements,
                ast.unlocked_achievements,
                (SELECT json_agg(json_build_object('genre', genre_name, 'playtime', genre_playtime)) FROM genre_stats) as top_genres
            FROM user_stats us
            LEFT JOIN achievement_stats ast ON us.user_id = ast.user_id
        """, (steam_id, steam_id, steam_id))
        
        result = cur.fetchone()
        if not result:
            print(f"No data found for {steam_id}")
            return None
        
        user_id, total_games, total_playtime, avg_playtime, games_played, games_never_played, \
        recent_playtime, total_achievements, unlocked_achievements, top_genres = result
        
        # Calculate derived features
        completion_rate = (unlocked_achievements / total_achievements * 100) if total_achievements else 0
        achievement_rate = (unlocked_achievements / total_achievements) if total_achievements else 0
        activity_score = min(recent_playtime / 100, 100) if recent_playtime else 0
        
        # Get favorite genre
        favorite_genre = None
        if top_genres:
            try:
                genres_list = json.loads(top_genres) if isinstance(top_genres, str) else top_genres
                if genres_list:
                    favorite_genre = genres_list[0].get('genre')
            except Exception:
                pass
        
        # Calculate genre diversity
        genre_diversity = 0
        if top_genres:
            try:
                genres_list = json.loads(top_genres) if isinstance(top_genres, str) else top_genres
                if genres_list:
                    total_genre_playtime = sum(g.get('playtime', 0) or 0 for g in genres_list)
                    if total_genre_playtime > 0:
                        import math
                        entropy = 0
                        for g in genres_list:
                            p = (g.get('playtime', 0) or 0) / total_genre_playtime
                            if p > 0:
                                entropy -= p * math.log(p)
                        max_entropy = math.log(len(genres_list)) if len(genres_list) > 0 else 1
                        genre_diversity = entropy / max_entropy if max_entropy > 0 else 0
            except Exception:
                pass
        
        # Build feature vector
        feature_vector = [
            total_games or 0,
            (total_playtime or 0) / 60,  # Convert to hours
            avg_playtime or 0,
            games_played or 0,
            completion_rate,
            achievement_rate * 100,
            genre_diversity * 100,
            activity_score
        ]
        
        # Insert or update ML features
        cur.execute("""
            INSERT INTO ml_player_features (
                steam_user_id, total_games, total_playtime, avg_playtime_per_game,
                games_played, games_never_played, completion_rate, total_achievements,
                achievement_rate, favorite_genre, genre_diversity_score, top_genres,
                activity_score, feature_vector, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (steam_user_id) DO UPDATE SET
                total_games = EXCLUDED.total_games,
                total_playtime = EXCLUDED.total_playtime,
                avg_playtime_per_game = EXCLUDED.avg_playtime_per_game,
                games_played = EXCLUDED.games_played,
                games_never_played = EXCLUDED.games_never_played,
                completion_rate = EXCLUDED.completion_rate,
                total_achievements = EXCLUDED.total_achievements,
                achievement_rate = EXCLUDED.achievement_rate,
                favorite_genre = EXCLUDED.favorite_genre,
                genre_diversity_score = EXCLUDED.genre_diversity_score,
                top_genres = EXCLUDED.top_genres,
                activity_score = EXCLUDED.activity_score,
                feature_vector = EXCLUDED.feature_vector,
                updated_at = NOW()
        """, (
            user_id,
            total_games or 0,
            total_playtime or 0,
            avg_playtime or 0,
            games_played or 0,
            games_never_played or 0,
            completion_rate,
            total_achievements or 0,
            achievement_rate,
            favorite_genre,
            genre_diversity,
            json.dumps(top_genres) if top_genres else None,
            activity_score,
            json.dumps(feature_vector)
        ))
        
        conn.commit()
        print(f"Successfully extracted ML features for {steam_id}")
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"Error extracting ML features for {steam_id}: {e}")
        raise
    finally:
        cur.close()
        conn.close()


def sync_group_users(**context):
    """Sync all users in a group."""
    group_id = context['params'].get('group_id')
    if not group_id:
        # Get steam_ids directly from params
        steam_ids = context['params'].get('steam_ids', [])
    else:
        # Fetch steam_ids from group
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT su.steam_id 
            FROM group_members gm
            JOIN steam_users su ON gm.steam_user_id = su.id
            WHERE gm.group_id = %s
        """, (group_id,))
        
        steam_ids = [r[0] for r in cur.fetchall()]
        cur.close()
        conn.close()
    
    results = []
    for steam_id in steam_ids:
        try:
            # Sync profile
            sync_user_profile.python_callable(params={'steam_id': steam_id})
            # Sync games
            sync_user_games.python_callable(params={'steam_id': steam_id})
            results.append({'steam_id': steam_id, 'status': 'success'})
        except Exception as e:
            results.append({'steam_id': steam_id, 'status': 'error', 'error': str(e)})
    
    return results


# Create the DAG
with DAG(
    'steam_user_sync',
    default_args=default_args,
    description='Sync Steam user data including profile, games, and achievements',
    schedule_interval=timedelta(hours=6),
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['steam', 'sync'],
) as dag:
    
    # These tasks can be triggered with params: {'steam_id': 'STEAM_ID_HERE'}
    
    sync_profile = PythonOperator(
        task_id='sync_user_profile',
        python_callable=sync_user_profile,
        provide_context=True,
    )
    
    sync_games = PythonOperator(
        task_id='sync_user_games',
        python_callable=sync_user_games,
        provide_context=True,
    )
    
    sync_achievements = PythonOperator(
        task_id='sync_user_achievements',
        python_callable=sync_user_achievements,
        provide_context=True,
    )
    
    extract_features = PythonOperator(
        task_id='extract_ml_features',
        python_callable=extract_ml_features,
        provide_context=True,
    )
    
    # Define task dependencies
    sync_profile >> sync_games >> sync_achievements >> extract_features


# Create a separate DAG for batch processing
with DAG(
    'steam_batch_sync',
    default_args=default_args,
    description='Batch sync multiple Steam users',
    schedule_interval=None,  # Manual trigger only
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['steam', 'batch', 'sync'],
) as batch_dag:
    
    def batch_sync_users(**context):
        """Sync multiple users from a list of Steam IDs."""
        steam_ids = context['params'].get('steam_ids', [])
        
        if not steam_ids:
            print("No steam_ids provided")
            return []
        
        results = []
        for steam_id in steam_ids:
            try:
                # Create a mock context for each user
                user_context = {'params': {'steam_id': steam_id}}
                
                sync_user_profile(**user_context)
                sync_user_games(**user_context)
                sync_user_achievements(**user_context)
                extract_ml_features(**user_context)
                
                results.append({'steam_id': steam_id, 'status': 'success'})
            except Exception as e:
                results.append({'steam_id': steam_id, 'status': 'error', 'error': str(e)})
        
        print(f"Batch sync complete. Results: {results}")
        return results
    
    batch_sync = PythonOperator(
        task_id='batch_sync_users',
        python_callable=batch_sync_users,
        provide_context=True,
    )


# Create DAG for group sync
with DAG(
    'steam_group_sync',
    default_args=default_args,
    description='Sync all users in a Steam Arena group',
    schedule_interval=None,  # Manual trigger only
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['steam', 'group', 'sync'],
) as group_dag:
    
    def sync_group(**context):
        """Sync all users in a group."""
        group_id = context['params'].get('group_id')
        
        if not group_id:
            raise ValueError("group_id is required")
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            # Get all steam_ids in the group
            cur.execute("""
                SELECT su.steam_id 
                FROM group_members gm
                JOIN steam_users su ON gm.steam_user_id = su.id
                WHERE gm.group_id = %s
            """, (group_id,))
            
            steam_ids = [r[0] for r in cur.fetchall()]
            
        finally:
            cur.close()
            conn.close()
        
        if not steam_ids:
            print(f"No users found in group {group_id}")
            return []
        
        results = []
        for steam_id in steam_ids:
            try:
                user_context = {'params': {'steam_id': steam_id}}
                
                sync_user_profile(**user_context)
                sync_user_games(**user_context)
                
                results.append({'steam_id': steam_id, 'status': 'success'})
            except Exception as e:
                results.append({'steam_id': steam_id, 'status': 'error', 'error': str(e)})
        
        print(f"Group sync complete. Results: {results}")
        return results
    
    group_sync = PythonOperator(
        task_id='sync_group_users',
        python_callable=sync_group,
        provide_context=True,
    )
