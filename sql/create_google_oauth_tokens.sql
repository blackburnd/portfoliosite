-- Create Google OAuth Tokens Table
-- Run this to add Google OAuth token storage to the database

-- Create Google OAuth Tokens table
CREATE TABLE IF NOT EXISTS google_oauth_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_email VARCHAR(100) NOT NULL,
    access_token TEXT NOT NULL,                     -- Google OAuth access token
    refresh_token TEXT,                             -- Google OAuth refresh token
    token_expires_at TIMESTAMP WITH TIME ZONE,
    granted_scopes TEXT NOT NULL,                   -- Space-separated scopes granted by user
    requested_scopes TEXT NOT NULL,                 -- Space-separated scopes we requested
    token_type VARCHAR(50) DEFAULT 'Bearer',
    last_used_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(admin_email)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_google_oauth_tokens_admin_email ON google_oauth_tokens(admin_email);
CREATE INDEX IF NOT EXISTS idx_google_oauth_tokens_active ON google_oauth_tokens(is_active);
CREATE INDEX IF NOT EXISTS idx_google_oauth_tokens_expires_at ON google_oauth_tokens(token_expires_at);

-- Create trigger for automatic updated_at
CREATE OR REPLACE TRIGGER update_google_oauth_tokens_updated_at 
    BEFORE UPDATE ON google_oauth_tokens 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add table comments
COMMENT ON TABLE google_oauth_tokens IS 'Stores Google OAuth tokens for authenticated admin users';
COMMENT ON COLUMN google_oauth_tokens.admin_email IS 'Email of the admin user who authorized the tokens';
COMMENT ON COLUMN google_oauth_tokens.access_token IS 'Google OAuth access token';
COMMENT ON COLUMN google_oauth_tokens.refresh_token IS 'Google OAuth refresh token';
COMMENT ON COLUMN google_oauth_tokens.granted_scopes IS 'Space-separated list of scopes actually granted by Google';
COMMENT ON COLUMN google_oauth_tokens.requested_scopes IS 'Space-separated list of scopes we requested from Google';
COMMENT ON COLUMN google_oauth_tokens.last_used_at IS 'Timestamp when tokens were last used for API calls';

-- Show created table
SELECT 'Google OAuth tokens table created successfully' as message;
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name = 'google_oauth_tokens';
