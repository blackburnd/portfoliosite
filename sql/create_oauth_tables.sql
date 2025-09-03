-- Create OAuth Management Tables
-- Run this script directly on PostgreSQL database

-- Create oauth_system_settings table
CREATE TABLE IF NOT EXISTS oauth_system_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    setting_key VARCHAR(100) UNIQUE NOT NULL,
    setting_value TEXT NOT NULL,
    description TEXT,
    is_encrypted BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255) NOT NULL
);

-- Create oauth_apps table
CREATE TABLE IF NOT EXISTS oauth_apps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider VARCHAR(50) NOT NULL,
    app_name VARCHAR(255) NOT NULL,
    client_id VARCHAR(255) NOT NULL,
    client_secret TEXT NOT NULL,
    redirect_uri VARCHAR(500) NOT NULL,
    scopes TEXT[],
    is_active BOOLEAN DEFAULT true,
    encryption_key TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255) NOT NULL,
    UNIQUE(provider, app_name)
);

-- Create linkedin_oauth_config table
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

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for automatic updated_at
CREATE OR REPLACE TRIGGER update_oauth_system_settings_updated_at 
    BEFORE UPDATE ON oauth_system_settings 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE OR REPLACE TRIGGER update_oauth_apps_updated_at 
    BEFORE UPDATE ON oauth_apps 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_oauth_apps_provider ON oauth_apps(provider);
CREATE INDEX IF NOT EXISTS idx_oauth_apps_active ON oauth_apps(is_active);
CREATE INDEX IF NOT EXISTS idx_oauth_system_settings_key ON oauth_system_settings(setting_key);
CREATE INDEX IF NOT EXISTS idx_linkedin_oauth_config_active ON linkedin_oauth_config(is_active);

-- Show created tables
SELECT 'Tables created successfully:' as message;
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('oauth_system_settings', 'oauth_apps', 'linkedin_oauth_config');
