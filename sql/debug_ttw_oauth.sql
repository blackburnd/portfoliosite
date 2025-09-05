-- Debug TTW OAuth Configuration
-- Run each query separately to check the current state of LinkedIn OAuth setup

-- 1. Check if TTW OAuth tables exist
SELECT 
    schemaname, 
    tablename, 
    tableowner 
FROM pg_tables 
WHERE tablename IN ('linkedin_oauth_config', 'linkedin_oauth_connections', 'linkedin_oauth_scopes')
ORDER BY tablename;

-- 2. Check LinkedIn OAuth app configuration
-- SELECT 
--     id,
--     app_name,
--     client_id,
--     redirect_uri,
--     is_active,
--     configured_by_email,
--     created_at
-- FROM linkedin_oauth_config 
-- WHERE is_active = true
-- ORDER BY created_at DESC;

-- 3. Check OAuth connections
-- SELECT 
--     id,
--     admin_email,
--     linkedin_profile_id,
--     linkedin_profile_name,
--     token_expires_at,
--     granted_scopes,
--     is_active,
--     created_at
-- FROM linkedin_oauth_connections 
-- WHERE is_active = true
-- ORDER BY created_at DESC;

-- 4. Check available OAuth scopes
-- SELECT 
--     scope_name,
--     display_name,
--     is_required,
--     is_enabled,
--     sort_order
-- FROM linkedin_oauth_scopes 
-- WHERE is_enabled = true
-- ORDER BY sort_order, scope_name;

-- 5. Summary counts
-- SELECT 
--     'linkedin_oauth_config' as table_name,
--     COUNT(*) as total_records,
--     COUNT(*) FILTER (WHERE is_active = true) as active_records
-- FROM linkedin_oauth_config
-- UNION ALL
-- SELECT 
--     'linkedin_oauth_connections' as table_name,
--     COUNT(*) as total_records,
--     COUNT(*) FILTER (WHERE is_active = true) as active_records
-- FROM linkedin_oauth_connections
-- UNION ALL
-- SELECT 
--     'linkedin_oauth_scopes' as table_name,
--     COUNT(*) as total_records,
--     COUNT(*) FILTER (WHERE is_enabled = true) as enabled_records
-- FROM linkedin_oauth_scopes;
