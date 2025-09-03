-- OAuth Configuration Management Schema
-- This will store all OAuth configurations and encryption keys in the database

-- Table for storing OAuth app configurations
CREATE TABLE IF NOT EXISTS oauth_apps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider VARCHAR(50) NOT NULL, -- 'google', 'linkedin', etc.
    app_name VARCHAR(255) NOT NULL,
    client_id VARCHAR(255) NOT NULL,
    client_secret TEXT NOT NULL,
    redirect_uri VARCHAR(500) NOT NULL,
    scopes TEXT[], -- Array of scopes
    is_active BOOLEAN DEFAULT true,
    encryption_key TEXT NOT NULL, -- Stored encrypted with master key
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255) NOT NULL,
    UNIQUE(provider, app_name)
);

-- Table for system-wide OAuth settings
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

-- Insert master encryption key (this should be done once)
INSERT INTO oauth_system_settings (setting_key, setting_value, description, is_encrypted, created_by)
VALUES 
    ('master_encryption_key', 'REPLACE_WITH_GENERATED_KEY', 'Master key for encrypting OAuth secrets', false, 'system')
ON CONFLICT (setting_key) DO NOTHING;

-- Migrate existing LinkedIn config to new structure
INSERT INTO oauth_apps (provider, app_name, client_id, client_secret, redirect_uri, scopes, encryption_key, created_by)
SELECT 
    'linkedin' as provider,
    app_name,
    client_id,
    client_secret,
    redirect_uri,
    ARRAY['r_liteprofile', 'r_emailaddress'] as scopes,
    'TEMP_KEY' as encryption_key,
    configured_by_email
FROM linkedin_oauth_config 
WHERE is_active = true
ON CONFLICT (provider, app_name) DO NOTHING;

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_oauth_apps_provider ON oauth_apps(provider);
CREATE INDEX IF NOT EXISTS idx_oauth_apps_active ON oauth_apps(is_active);
CREATE INDEX IF NOT EXISTS idx_oauth_system_settings_key ON oauth_system_settings(setting_key);

-- Add updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE OR REPLACE TRIGGER update_oauth_apps_updated_at 
    BEFORE UPDATE ON oauth_apps 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE OR REPLACE TRIGGER update_oauth_system_settings_updated_at 
    BEFORE UPDATE ON oauth_system_settings 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
