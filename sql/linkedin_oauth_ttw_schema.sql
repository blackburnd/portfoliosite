-- LinkedIn OAuth TTW (Through-The-Web) Configuration Schema
-- Complete self-contained OAuth implementation with no environment variables

-- LinkedIn OAuth Application Configuration
-- Stores the LinkedIn OAuth app credentials configured by admin
CREATE TABLE IF NOT EXISTS linkedin_oauth_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    app_name VARCHAR(200) NOT NULL DEFAULT 'Portfolio LinkedIn Integration',
    client_id VARCHAR(200) NOT NULL,
    client_secret TEXT NOT NULL,                    -- Encrypted
    redirect_uri VARCHAR(500) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    configured_by_email VARCHAR(100) NOT NULL,      -- Admin who configured it
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- LinkedIn OAuth User Connections
-- Stores individual admin user connections and their granted permissions
CREATE TABLE IF NOT EXISTS linkedin_oauth_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_email VARCHAR(100) NOT NULL,
    linkedin_profile_id VARCHAR(100),
    linkedin_profile_name VARCHAR(200),
    access_token TEXT NOT NULL,                     -- Encrypted
    refresh_token TEXT,                             -- Encrypted
    token_expires_at TIMESTAMP WITH TIME ZONE,
    granted_scopes TEXT NOT NULL,                   -- Space-separated scopes granted by user
    requested_scopes TEXT NOT NULL,                 -- Space-separated scopes we requested
    last_sync_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(admin_email)
);

-- LinkedIn OAuth Permission Scopes
-- Defines available LinkedIn permissions and their descriptions
CREATE TABLE IF NOT EXISTS linkedin_oauth_scopes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scope_name VARCHAR(100) NOT NULL UNIQUE,
    display_name VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    data_access_description TEXT NOT NULL,          -- What data this scope allows access to
    is_required BOOLEAN DEFAULT FALSE,              -- Required for basic functionality
    is_enabled BOOLEAN DEFAULT TRUE,                -- Available for selection
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_linkedin_oauth_config_active ON linkedin_oauth_config(is_active);
CREATE INDEX IF NOT EXISTS idx_linkedin_oauth_connections_admin_email ON linkedin_oauth_connections(admin_email);
CREATE INDEX IF NOT EXISTS idx_linkedin_oauth_connections_active ON linkedin_oauth_connections(is_active);
CREATE INDEX IF NOT EXISTS idx_linkedin_oauth_connections_expires_at ON linkedin_oauth_connections(token_expires_at);
CREATE INDEX IF NOT EXISTS idx_linkedin_oauth_scopes_enabled ON linkedin_oauth_scopes(is_enabled);

-- Create function to update updated_at column
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
DROP TRIGGER IF EXISTS update_linkedin_oauth_config_updated_at ON linkedin_oauth_config;
CREATE TRIGGER update_linkedin_oauth_config_updated_at 
    BEFORE UPDATE ON linkedin_oauth_config 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_linkedin_oauth_connections_updated_at ON linkedin_oauth_connections;
CREATE TRIGGER update_linkedin_oauth_connections_updated_at 
    BEFORE UPDATE ON linkedin_oauth_connections 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default LinkedIn OAuth scopes
INSERT INTO linkedin_oauth_scopes (scope_name, display_name, description, data_access_description, is_required, sort_order) VALUES
('r_liteprofile', 'Basic Profile', 'Access to basic profile information', 'First name, last name, profile picture, headline', true, 1),
('r_emailaddress', 'Email Address', 'Access to primary email address', 'Primary email address associated with LinkedIn account', true, 2),
('r_basicprofile', 'Full Profile', 'Access to full profile information', 'Complete profile including summary, location, industry', false, 3),
('rw_company_admin', 'Company Administration', 'Access to company pages (if admin)', 'Company page information for pages you admin', false, 4),
('w_member_social', 'Share Content', 'Ability to share content on behalf of user', 'Post updates and share content to LinkedIn feed', false, 5)
ON CONFLICT (scope_name) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    data_access_description = EXCLUDED.data_access_description,
    is_required = EXCLUDED.is_required,
    sort_order = EXCLUDED.sort_order;

-- Add table comments
COMMENT ON TABLE linkedin_oauth_config IS 'LinkedIn OAuth application configuration - stores app credentials configured through admin interface';
COMMENT ON TABLE linkedin_oauth_connections IS 'Individual admin user LinkedIn OAuth connections with granted permissions';
COMMENT ON TABLE linkedin_oauth_scopes IS 'Available LinkedIn OAuth permission scopes and their descriptions';

COMMENT ON COLUMN linkedin_oauth_config.client_secret IS 'LinkedIn OAuth app client secret (encrypted at application level)';
COMMENT ON COLUMN linkedin_oauth_connections.access_token IS 'LinkedIn OAuth access token (encrypted at application level)';
COMMENT ON COLUMN linkedin_oauth_connections.refresh_token IS 'LinkedIn OAuth refresh token (encrypted at application level)';
COMMENT ON COLUMN linkedin_oauth_connections.granted_scopes IS 'Space-separated list of scopes actually granted by user';
COMMENT ON COLUMN linkedin_oauth_connections.requested_scopes IS 'Space-separated list of scopes we requested from user';

-- Example usage:
-- 1. Admin configures LinkedIn OAuth app:
-- INSERT INTO linkedin_oauth_config (app_name, client_id, client_secret, redirect_uri, configured_by_email)
-- VALUES ('My Portfolio App', 'client_id', 'encrypted_secret', 'https://domain.com/callback', 'admin@example.com');

-- 2. User grants permissions during OAuth flow:
-- INSERT INTO linkedin_oauth_connections (admin_email, access_token, granted_scopes, requested_scopes)
-- VALUES ('admin@example.com', 'encrypted_token', 'r_liteprofile r_emailaddress', 'r_liteprofile r_emailaddress r_basicprofile');

-- 3. Check what data admin can access:
-- SELECT c.admin_email, c.granted_scopes, s.display_name, s.data_access_description
-- FROM linkedin_oauth_connections c
-- CROSS JOIN linkedin_oauth_scopes s
-- WHERE c.admin_email = 'admin@example.com' 
-- AND c.granted_scopes LIKE '%' || s.scope_name || '%';
