-- Migration to convert encrypted client_secret values to plain text in oauth_apps table
-- This script is for manual execution to migrate existing encrypted client_secret values

-- First, check if there are any encrypted client_secret values
SELECT 
    provider,
    app_name,
    client_id,
    LENGTH(client_secret) as secret_length,
    created_by,
    created_at
FROM oauth_apps 
WHERE provider = 'linkedin'
ORDER BY updated_at DESC;

-- Note: If client_secret values appear to be encrypted (very long strings),
-- you will need to:
-- 1. Re-enter the client_secret values in the admin interface
-- 2. Or manually update them if you have the original values
-- 
-- The application will now store client_secret as plain text instead of encrypted

-- To clear existing LinkedIn OAuth configurations and start fresh:
-- DELETE FROM oauth_apps WHERE provider = 'linkedin';

-- After running this migration, reconfigure the LinkedIn OAuth app 
-- through the admin interface to store the client_secret as plain text
