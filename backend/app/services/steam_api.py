import httpx
from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncio
from cachetools import TTLCache

from app.config import settings


class SteamAPIClient:
    """Client for interacting with Steam Web API."""
    
    def __init__(self):
        self.api_key = settings.steam_api_key
        self.base_url = settings.steam_api_base_url
        self.store_url = settings.steam_store_api_url
        self._cache = TTLCache(maxsize=1000, ttl=settings.cache_ttl_seconds)
    
    async def _make_request(
        self, 
        url: str, 
        params: Optional[Dict] = None,
        use_cache: bool = True
    ) -> Optional[Dict]:
        """Make an async HTTP request to Steam API."""
        cache_key = f"{url}:{str(params)}"
        
        if use_cache and cache_key in self._cache:
            return self._cache[cache_key]
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                if use_cache:
                    self._cache[cache_key] = data
                
                return data
            except httpx.HTTPError as e:
                print(f"HTTP error occurred: {e}")
                return None
            except Exception as e:
                print(f"Error making request: {e}")
                return None
    
    async def get_player_summary(self, steam_id: str) -> Optional[Dict]:
        """Get player profile summary."""
        url = f"{self.base_url}/ISteamUser/GetPlayerSummaries/v2/"
        params = {
            "key": self.api_key,
            "steamids": steam_id
        }
        
        data = await self._make_request(url, params)
        if data and "response" in data and "players" in data["response"]:
            players = data["response"]["players"]
            return players[0] if players else None
        return None
    
    async def get_player_summaries(self, steam_ids: List[str]) -> List[Dict]:
        """Get profile summaries for multiple players (max 100 per request)."""
        results = []
        
        # Steam API allows max 100 steam IDs per request
        for i in range(0, len(steam_ids), 100):
            batch = steam_ids[i:i + 100]
            url = f"{self.base_url}/ISteamUser/GetPlayerSummaries/v2/"
            params = {
                "key": self.api_key,
                "steamids": ",".join(batch)
            }
            
            data = await self._make_request(url, params, use_cache=False)
            if data and "response" in data and "players" in data["response"]:
                results.extend(data["response"]["players"])
        
        return results
    
    async def get_owned_games(
        self, 
        steam_id: str, 
        include_free_games: bool = True,
        include_app_info: bool = True
    ) -> Optional[Dict]:
        """Get list of games owned by a player."""
        url = f"{self.base_url}/IPlayerService/GetOwnedGames/v1/"
        params = {
            "key": self.api_key,
            "steamid": steam_id,
            "include_played_free_games": include_free_games,
            "include_appinfo": include_app_info,
            "format": "json"
        }
        
        data = await self._make_request(url, params, use_cache=False)
        if data and "response" in data:
            return data["response"]
        return None
    
    async def get_recently_played_games(
        self, 
        steam_id: str, 
        count: int = 10
    ) -> Optional[List[Dict]]:
        """Get recently played games for a player."""
        url = f"{self.base_url}/IPlayerService/GetRecentlyPlayedGames/v1/"
        params = {
            "key": self.api_key,
            "steamid": steam_id,
            "count": count,
            "format": "json"
        }
        
        data = await self._make_request(url, params, use_cache=False)
        if data and "response" in data and "games" in data["response"]:
            return data["response"]["games"]
        return None
    
    async def get_player_achievements(
        self, 
        steam_id: str, 
        app_id: int
    ) -> Optional[Dict]:
        """Get achievements for a player in a specific game."""
        url = f"{self.base_url}/ISteamUserStats/GetPlayerAchievements/v1/"
        params = {
            "key": self.api_key,
            "steamid": steam_id,
            "appid": app_id,
            "l": "english"
        }
        
        data = await self._make_request(url, params, use_cache=False)
        if data and "playerstats" in data:
            return data["playerstats"]
        return None
    
    async def get_game_schema(self, app_id: int) -> Optional[Dict]:
        """Get game schema including achievement definitions."""
        url = f"{self.base_url}/ISteamUserStats/GetSchemaForGame/v2/"
        params = {
            "key": self.api_key,
            "appid": app_id,
            "l": "english"
        }
        
        data = await self._make_request(url, params)
        if data and "game" in data:
            return data["game"]
        return None
    
    async def get_global_achievement_percentages(
        self, 
        app_id: int
    ) -> Optional[List[Dict]]:
        """Get global achievement percentages for a game."""
        url = f"{self.base_url}/ISteamUserStats/GetGlobalAchievementPercentagesForApp/v2/"
        params = {
            "gameid": app_id
        }
        
        data = await self._make_request(url, params)
        if data and "achievementpercentages" in data:
            return data["achievementpercentages"].get("achievements", [])
        return None
    
    async def get_friend_list(self, steam_id: str) -> Optional[List[Dict]]:
        """Get friend list for a player."""
        url = f"{self.base_url}/ISteamUser/GetFriendList/v1/"
        params = {
            "key": self.api_key,
            "steamid": steam_id,
            "relationship": "friend"
        }
        
        data = await self._make_request(url, params)
        if data and "friendslist" in data:
            return data["friendslist"].get("friends", [])
        return None
    
    async def get_app_details(self, app_id: int) -> Optional[Dict]:
        """Get detailed information about a game from Steam Store."""
        url = f"{self.store_url}/appdetails"
        params = {
            "appids": app_id,
            "l": "english"
        }
        
        data = await self._make_request(url, params)
        if data and str(app_id) in data:
            app_data = data[str(app_id)]
            if app_data.get("success"):
                return app_data.get("data")
        return None
    
    async def resolve_vanity_url(self, vanity_url: str) -> Optional[str]:
        """Resolve a vanity URL to a Steam ID."""
        url = f"{self.base_url}/ISteamUser/ResolveVanityURL/v1/"
        params = {
            "key": self.api_key,
            "vanityurl": vanity_url
        }
        
        data = await self._make_request(url, params)
        if data and "response" in data:
            response = data["response"]
            if response.get("success") == 1:
                return response.get("steamid")
        return None
    
    async def get_user_stats_for_game(
        self, 
        steam_id: str, 
        app_id: int
    ) -> Optional[Dict]:
        """Get user stats for a specific game."""
        url = f"{self.base_url}/ISteamUserStats/GetUserStatsForGame/v2/"
        params = {
            "key": self.api_key,
            "steamid": steam_id,
            "appid": app_id
        }
        
        data = await self._make_request(url, params, use_cache=False)
        if data and "playerstats" in data:
            return data["playerstats"]
        return None
    
    def parse_player_data(self, player_data: Dict) -> Dict:
        """Parse raw player data from Steam API."""
        return {
            "steam_id": player_data.get("steamid"),
            "persona_name": player_data.get("personaname"),
            "profile_url": player_data.get("profileurl"),
            "avatar_url": player_data.get("avatar"),
            "avatar_medium_url": player_data.get("avatarmedium"),
            "avatar_full_url": player_data.get("avatarfull"),
            "country_code": player_data.get("loccountrycode"),
            "time_created": datetime.fromtimestamp(player_data["timecreated"]) 
                if "timecreated" in player_data else None,
            "last_logoff": datetime.fromtimestamp(player_data["lastlogoff"]) 
                if "lastlogoff" in player_data else None,
            "profile_state": player_data.get("profilestate"),
            "community_visibility_state": player_data.get("communityvisibilitystate")
        }
    
    def parse_game_data(self, game_data: Dict) -> Dict:
        """Parse raw game data from owned games API."""
        return {
            "app_id": game_data.get("appid"),
            "name": game_data.get("name", f"Unknown Game {game_data.get('appid')}"),
            "img_icon_url": f"https://media.steampowered.com/steamcommunity/public/images/apps/{game_data.get('appid')}/{game_data.get('img_icon_url')}.jpg" 
                if game_data.get("img_icon_url") else None,
            "playtime_forever": game_data.get("playtime_forever", 0),
            "playtime_2weeks": game_data.get("playtime_2weeks", 0),
            "playtime_windows": game_data.get("playtime_windows_forever", 0),
            "playtime_mac": game_data.get("playtime_mac_forever", 0),
            "playtime_linux": game_data.get("playtime_linux_forever", 0),
            "rtime_last_played": datetime.fromtimestamp(game_data["rtime_last_played"]) 
                if game_data.get("rtime_last_played") else None
        }
    
    def parse_app_details(self, app_details: Dict) -> Dict:
        """Parse detailed app info from Steam Store API."""
        release_date = None
        if app_details.get("release_date") and not app_details["release_date"].get("coming_soon"):
            try:
                release_date = datetime.strptime(
                    app_details["release_date"].get("date", ""), 
                    "%b %d, %Y"
                )
            except:
                pass
        
        price_initial = None
        price_final = None
        discount = 0
        
        if app_details.get("price_overview"):
            price_overview = app_details["price_overview"]
            price_initial = price_overview.get("initial")
            price_final = price_overview.get("final")
            discount = price_overview.get("discount_percent", 0)
        
        metacritic_score = None
        metacritic_url = None
        if app_details.get("metacritic"):
            metacritic_score = app_details["metacritic"].get("score")
            metacritic_url = app_details["metacritic"].get("url")
        
        developers = app_details.get("developers", [])
        publishers = app_details.get("publishers", [])
        
        return {
            "name": app_details.get("name"),
            "header_image": app_details.get("header_image"),
            "short_description": app_details.get("short_description"),
            "detailed_description": app_details.get("detailed_description"),
            "about_the_game": app_details.get("about_the_game"),
            "release_date": release_date,
            "developer": ", ".join(developers) if developers else None,
            "publisher": ", ".join(publishers) if publishers else None,
            "price_initial": price_initial,
            "price_final": price_final,
            "discount_percent": discount,
            "is_free": app_details.get("is_free", False),
            "metacritic_score": metacritic_score,
            "metacritic_url": metacritic_url,
            "genres": [g.get("description") for g in app_details.get("genres", [])],
            "categories": [c.get("description") for c in app_details.get("categories", [])]
        }


# Singleton instance
steam_client = SteamAPIClient()
