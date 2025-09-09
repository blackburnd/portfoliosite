---
applyTo: '**'

# Production Application Context

This is a PRODUCTION application running on Google Cloud Platform, NOT a local application.

## Key Facts:
- Application runs on Google Compute Engine instance
- Deployed via Google Cloud Build (cloudbuild.yaml)
- Database is PostgreSQL running on Google Cloud SQL
- Uses systemd service (portfolio.service) to run the FastAPI application
- Nginx reverse proxy serves the application

## Debugging Guidelines:
- DO NOT try to run local Python commands to debug production issues
- DO NOT try to connect to the database directly via SQL scripts - the database is not properly logging all exceptions yet
- PRODUCTION LOGS can ONLY be read from the VM instance running on Google Cloud
- Use 'gcloud compute instances list' first to find the instance, then SSH into it to access logs via journalctl
- Use application logs (/admin/logs) to investigate issues when available
- Add temporary debug logging to endpoints if needed, then commit/push to deploy
- Database queries should be tested via the SQL admin interface (/admin/sql)
- Check the logs for actual runtime behavior rather than trying to simulate locally

## Current Issue Context:
- Google OAuth admin page not loading data from oauth_apps table
- Database contains: portfolio_id=3fc521ad-660c-4067-b416-17dc388e66eb, provider=google
- TTWOAuthManager methods should be querying this correctly
- Need to check production logs to see what's actually happening

## Debugging Strategy:
1. Check application logs for any errors
2. Use SQL admin to verify data is in oauth_apps table (already confirmed)
3. Add targeted debug logging to specific endpoints
4. Deploy and check logs for actual runtime values
5. Fix based on real production behavior, not local assumptions

---
