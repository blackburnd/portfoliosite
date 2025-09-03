-- LinkedIn OAuth Credentials Table
-- This table stores LinkedIn OAuth tokens associated with admin users (Google accounts)

CREATE TABLE IF NOT EXISTS linkedin_oauth_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_email VARCHAR(100) NOT NULL,
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_expires_at TIMESTAMP WITH TIME ZONE,
    linkedin_profile_id VARCHAR(100),
    scope TEXT DEFAULT 'r_liteprofile r_emailaddress',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(admin_email)
);

-- Create index for efficient lookups
CREATE INDEX IF NOT EXISTS idx_linkedin_oauth_admin_email ON linkedin_oauth_credentials(admin_email);
CREATE INDEX IF NOT EXISTS idx_linkedin_oauth_expires_at ON linkedin_oauth_credentials(token_expires_at);

-- Create function to update updated_at column if it doesn't exist
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger to automatically update updated_at
DROP TRIGGER IF EXISTS update_linkedin_oauth_credentials_updated_at ON linkedin_oauth_credentials;
CREATE TRIGGER update_linkedin_oauth_credentials_updated_at 
    BEFORE UPDATE ON linkedin_oauth_credentials 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add comment for documentation
COMMENT ON TABLE linkedin_oauth_credentials IS 'Stores LinkedIn OAuth 2.0 credentials for admin users (identified by Google account email) to enable secure LinkedIn data sync';
COMMENT ON COLUMN linkedin_oauth_credentials.admin_email IS 'Email of the admin user (from Google OAuth authentication)';
COMMENT ON COLUMN linkedin_oauth_credentials.access_token IS 'LinkedIn OAuth access token (encrypted at application level)';
COMMENT ON COLUMN linkedin_oauth_credentials.refresh_token IS 'LinkedIn OAuth refresh token (encrypted at application level)';
COMMENT ON COLUMN linkedin_oauth_credentials.token_expires_at IS 'When the access token expires (UTC)';
COMMENT ON COLUMN linkedin_oauth_credentials.linkedin_profile_id IS 'LinkedIn profile ID associated with the tokens';
COMMENT ON COLUMN linkedin_oauth_credentials.scope IS 'OAuth scopes granted by LinkedIn (read-only access)';

-- Example usage:
-- INSERT INTO linkedin_oauth_credentials (admin_email, access_token, refresh_token, token_expires_at, linkedin_profile_id, scope)
-- VALUES ('admin@example.com', 'encrypted_access_token', 'encrypted_refresh_token', NOW() + INTERVAL '60 days', 'linkedin_user_id', 'r_liteprofile r_emailaddress');

-- Query to check admin's LinkedIn connection:
-- SELECT admin_email, linkedin_profile_id, token_expires_at, scope 
-- FROM linkedin_oauth_credentials 
-- WHERE admin_email = 'admin@example.com' AND token_expires_at > NOW();