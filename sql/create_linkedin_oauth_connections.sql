-- Create remaining TTW OAuth tables

CREATE TABLE IF NOT EXISTS linkedin_oauth_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_email VARCHAR(100) NOT NULL,
    linkedin_profile_id VARCHAR(100),
    linkedin_profile_name VARCHAR(200),
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_expires_at TIMESTAMP WITH TIME ZONE,
    granted_scopes TEXT NOT NULL,
    requested_scopes TEXT NOT NULL,
    last_sync_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(admin_email)
);
