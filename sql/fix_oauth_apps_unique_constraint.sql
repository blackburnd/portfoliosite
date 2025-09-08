-- Fix OAuth Apps Table Constraint
-- Change unique constraint from (provider, app_name) to just (provider)
-- This prevents duplicate records when updating OAuth configurations

-- Drop the existing constraint
ALTER TABLE oauth_apps DROP CONSTRAINT IF EXISTS oauth_apps_provider_app_name_key;

-- Add new constraint on provider only
ALTER TABLE oauth_apps ADD CONSTRAINT oauth_apps_provider_key UNIQUE (provider);

-- Ensure we have the correct structure
-- If there are any duplicates, this migration should be run after manually cleaning them up
