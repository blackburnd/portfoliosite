-- Remove Bootstrap System Database Tables
-- This script removes the bootstrap-related tables that are no longer needed

-- Drop oauth_system_settings table (used by bootstrap system)
DROP TABLE IF EXISTS oauth_system_settings CASCADE;

-- Drop any related bootstrap indexes
DROP INDEX IF EXISTS idx_oauth_system_settings_key;

-- Drop any bootstrap-related triggers
DROP TRIGGER IF EXISTS update_oauth_system_settings_updated_at ON oauth_system_settings;

-- Note: We keep the linkedin_oauth_config, linkedin_oauth_connections, and linkedin_oauth_scopes tables
-- as they are part of the TTW OAuth system and are still needed

-- Tables kept (TTW OAuth system):
-- - linkedin_oauth_config
-- - linkedin_oauth_connections  
-- - linkedin_oauth_scopes

COMMENT ON SCHEMA public IS 'Bootstrap system tables removed - using TTW OAuth only';
