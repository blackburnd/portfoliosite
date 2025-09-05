-- Create TTW OAuth Tables (run if tables don't exist)
-- This creates the necessary tables for Through-The-Web OAuth configuration

CREATE TABLE IF NOT EXISTS linkedin_oauth_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    app_name VARCHAR(200) NOT NULL DEFAULT 'Portfolio LinkedIn Integration',
    client_id VARCHAR(200) NOT NULL,
    client_secret TEXT NOT NULL,
    redirect_uri VARCHAR(500) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    configured_by_email VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
