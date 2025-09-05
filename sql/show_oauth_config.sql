-- Show any LinkedIn OAuth configuration that exists
SELECT 
    app_name,
    client_id,
    LEFT(client_secret, 10) || '...' as client_secret_preview,
    redirect_uri,
    is_active,
    configured_by_email,
    created_at
FROM linkedin_oauth_config 
ORDER BY created_at DESC;
