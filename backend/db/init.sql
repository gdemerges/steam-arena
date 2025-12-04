-- Steam Arena Database Schema

-- Extension for UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Steam Users table
CREATE TABLE IF NOT EXISTS steam_users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    steam_id VARCHAR(20) UNIQUE NOT NULL,
    persona_name VARCHAR(255),
    profile_url TEXT,
    avatar_url TEXT,
    avatar_medium_url TEXT,
    avatar_full_url TEXT,
    country_code VARCHAR(10),
    time_created TIMESTAMP,
    last_logoff TIMESTAMP,
    profile_state INTEGER,
    community_visibility_state INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User Groups (for friend groups management)
CREATE TABLE IF NOT EXISTS user_groups (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_by UUID REFERENCES steam_users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Group Members (many-to-many relationship)
CREATE TABLE IF NOT EXISTS group_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    group_id UUID REFERENCES user_groups(id) ON DELETE CASCADE,
    steam_user_id UUID REFERENCES steam_users(id) ON DELETE CASCADE,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(group_id, steam_user_id)
);

-- Games table
CREATE TABLE IF NOT EXISTS games (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    app_id INTEGER UNIQUE NOT NULL,
    name VARCHAR(500) NOT NULL,
    img_icon_url TEXT,
    img_logo_url TEXT,
    header_image TEXT,
    short_description TEXT,
    detailed_description TEXT,
    about_the_game TEXT,
    release_date DATE,
    developer VARCHAR(500),
    publisher VARCHAR(500),
    price_initial INTEGER,
    price_final INTEGER,
    discount_percent INTEGER,
    is_free BOOLEAN DEFAULT FALSE,
    metacritic_score INTEGER,
    metacritic_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Game Genres
CREATE TABLE IF NOT EXISTS genres (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    steam_genre_id INTEGER UNIQUE,
    name VARCHAR(100) NOT NULL
);

-- Game-Genre relationship
CREATE TABLE IF NOT EXISTS game_genres (
    game_id UUID REFERENCES games(id) ON DELETE CASCADE,
    genre_id UUID REFERENCES genres(id) ON DELETE CASCADE,
    PRIMARY KEY (game_id, genre_id)
);

-- Game Categories (tags)
CREATE TABLE IF NOT EXISTS categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    steam_category_id INTEGER UNIQUE,
    name VARCHAR(100) NOT NULL
);

-- Game-Category relationship
CREATE TABLE IF NOT EXISTS game_categories (
    game_id UUID REFERENCES games(id) ON DELETE CASCADE,
    category_id UUID REFERENCES categories(id) ON DELETE CASCADE,
    PRIMARY KEY (game_id, category_id)
);

-- User Game Library (owned games with playtime)
CREATE TABLE IF NOT EXISTS user_games (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    steam_user_id UUID REFERENCES steam_users(id) ON DELETE CASCADE,
    game_id UUID REFERENCES games(id) ON DELETE CASCADE,
    playtime_forever INTEGER DEFAULT 0, -- in minutes
    playtime_2weeks INTEGER DEFAULT 0, -- in minutes
    playtime_windows INTEGER DEFAULT 0,
    playtime_mac INTEGER DEFAULT 0,
    playtime_linux INTEGER DEFAULT 0,
    rtime_last_played TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(steam_user_id, game_id)
);

-- Achievements table
CREATE TABLE IF NOT EXISTS achievements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    game_id UUID REFERENCES games(id) ON DELETE CASCADE,
    api_name VARCHAR(255) NOT NULL,
    display_name VARCHAR(500),
    description TEXT,
    icon_url TEXT,
    icon_gray_url TEXT,
    hidden BOOLEAN DEFAULT FALSE,
    global_percent FLOAT,
    UNIQUE(game_id, api_name)
);

-- User Achievements
CREATE TABLE IF NOT EXISTS user_achievements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    steam_user_id UUID REFERENCES steam_users(id) ON DELETE CASCADE,
    achievement_id UUID REFERENCES achievements(id) ON DELETE CASCADE,
    achieved BOOLEAN DEFAULT FALSE,
    unlock_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(steam_user_id, achievement_id)
);

-- Backlog status for games
CREATE TABLE IF NOT EXISTS user_backlog (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    steam_user_id UUID REFERENCES steam_users(id) ON DELETE CASCADE,
    game_id UUID REFERENCES games(id) ON DELETE CASCADE,
    status VARCHAR(50) DEFAULT 'backlog', -- backlog, playing, completed, abandoned, wishlist
    priority INTEGER DEFAULT 0,
    notes TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(steam_user_id, game_id)
);

-- Data sync history (for tracking when data was last fetched)
CREATE TABLE IF NOT EXISTS sync_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    steam_user_id UUID REFERENCES steam_users(id) ON DELETE CASCADE,
    sync_type VARCHAR(50) NOT NULL, -- profile, games, achievements, friends
    status VARCHAR(20) DEFAULT 'pending', -- pending, in_progress, completed, failed
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    items_synced INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ML Features table (for storing extracted features for ML)
CREATE TABLE IF NOT EXISTS ml_player_features (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    steam_user_id UUID REFERENCES steam_users(id) ON DELETE CASCADE UNIQUE,
    total_games INTEGER DEFAULT 0,
    total_playtime INTEGER DEFAULT 0,
    avg_playtime_per_game FLOAT DEFAULT 0,
    games_played INTEGER DEFAULT 0,
    games_never_played INTEGER DEFAULT 0,
    completion_rate FLOAT DEFAULT 0,
    total_achievements INTEGER DEFAULT 0,
    achievement_rate FLOAT DEFAULT 0,
    favorite_genre VARCHAR(100),
    genre_diversity_score FLOAT DEFAULT 0,
    top_genres JSONB,
    playtime_distribution JSONB,
    activity_score FLOAT DEFAULT 0,
    cluster_id INTEGER,
    feature_vector JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Recommendations table
CREATE TABLE IF NOT EXISTS recommendations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    steam_user_id UUID REFERENCES steam_users(id) ON DELETE CASCADE,
    game_id UUID REFERENCES games(id) ON DELETE CASCADE,
    recommendation_type VARCHAR(50), -- collaborative, content_based, hybrid
    score FLOAT,
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(steam_user_id, game_id, recommendation_type)
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_steam_users_steam_id ON steam_users(steam_id);
CREATE INDEX IF NOT EXISTS idx_games_app_id ON games(app_id);
CREATE INDEX IF NOT EXISTS idx_user_games_steam_user_id ON user_games(steam_user_id);
CREATE INDEX IF NOT EXISTS idx_user_games_game_id ON user_games(game_id);
CREATE INDEX IF NOT EXISTS idx_user_achievements_steam_user_id ON user_achievements(steam_user_id);
CREATE INDEX IF NOT EXISTS idx_achievements_game_id ON achievements(game_id);
CREATE INDEX IF NOT EXISTS idx_group_members_group_id ON group_members(group_id);
CREATE INDEX IF NOT EXISTS idx_group_members_steam_user_id ON group_members(steam_user_id);
CREATE INDEX IF NOT EXISTS idx_sync_history_steam_user_id ON sync_history(steam_user_id);
CREATE INDEX IF NOT EXISTS idx_ml_player_features_cluster_id ON ml_player_features(cluster_id);
CREATE INDEX IF NOT EXISTS idx_recommendations_steam_user_id ON recommendations(steam_user_id);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
CREATE TRIGGER update_steam_users_updated_at BEFORE UPDATE ON steam_users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_user_groups_updated_at BEFORE UPDATE ON user_groups FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_games_updated_at BEFORE UPDATE ON games FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_user_games_updated_at BEFORE UPDATE ON user_games FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_user_backlog_updated_at BEFORE UPDATE ON user_backlog FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_ml_player_features_updated_at BEFORE UPDATE ON ml_player_features FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
