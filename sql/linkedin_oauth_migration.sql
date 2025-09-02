-- LinkedIn OAuth Credentials Table
-- This table stores LinkedIn OAuth tokens associated with admin users

CREATE TABLE IF NOT EXISTS linkedin_oauth_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_email VARCHAR(100) NOT NULL,
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_expires_at TIMESTAMP WITH TIME ZONE,
    linkedin_profile_id VARCHAR(100),
    scope TEXT DEFAULT 'r_liteprofile,r_emailaddress',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(admin_email)
);

-- Create index for efficient lookups
CREATE INDEX IF NOT EXISTS idx_linkedin_oauth_admin_email ON linkedin_oauth_credentials(admin_email);
CREATE INDEX IF NOT EXISTS idx_linkedin_oauth_expires_at ON linkedin_oauth_credentials(token_expires_at);

-- Create trigger to automatically update updated_at
CREATE TRIGGER update_linkedin_oauth_credentials_updated_at 
    BEFORE UPDATE ON linkedin_oauth_credentials 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add comment for documentation
COMMENT ON TABLE linkedin_oauth_credentials IS 'Stores LinkedIn OAuth 2.0 credentials for admin users to enable secure LinkedIn data sync';
COMMENT ON COLUMN linkedin_oauth_credentials.admin_email IS 'Email of the admin user (from Google OAuth)';
COMMENT ON COLUMN linkedin_oauth_credentials.access_token IS 'LinkedIn OAuth access token (encrypted)';
COMMENT ON COLUMN linkedin_oauth_credentials.refresh_token IS 'LinkedIn OAuth refresh token (encrypted)';
COMMENT ON COLUMN linkedin_oauth_credentials.token_expires_at IS 'When the access token expires';
COMMENT ON COLUMN linkedin_oauth_credentials.linkedin_profile_id IS 'LinkedIn profile ID to sync data from';
COMMENT ON COLUMN linkedin_oauth_credentials.scope IS 'OAuth scopes granted by LinkedIn';