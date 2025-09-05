-- Check if LinkedIn OAuth app is configured
SELECT COUNT(*) as oauth_apps_configured FROM linkedin_oauth_config WHERE is_active = true;
