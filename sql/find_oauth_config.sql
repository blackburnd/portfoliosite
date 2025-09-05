-- Check for OAuth configuration in different possible tables

-- Check linkedin_oauth_config (TTW table)
SELECT 'linkedin_oauth_config' as source_table, COUNT(*) as count FROM linkedin_oauth_config WHERE is_active = true;

-- Check if there's an oauth_apps table (from old system)
-- SELECT 'oauth_apps' as source_table, COUNT(*) as count FROM oauth_apps WHERE is_active = true;
