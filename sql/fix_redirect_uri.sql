-- Fix LinkedIn OAuth redirect URI to match the actual callback endpoint
UPDATE linkedin_oauth_config 
SET redirect_uri = 'https://www.blackburnsystems.com/admin/linkedin/callback',
    updated_at = NOW()
WHERE is_active = true 
  AND redirect_uri = 'https://www.blackburnsystems.com/linkedin/oauth/callback';
