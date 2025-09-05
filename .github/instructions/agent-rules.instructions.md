---
applyTo: '**'

Never add css <style> blocks to html, css belongs in css files only.

## Google Cloud Debugging Commands

When production shows 502 errors or application failures, use these gcloud commands:

1. **List instances:**
   ```bash
   gcloud compute instances list
   ```

2. **Get instance ID:**
   ```bash
   gcloud compute instances describe INSTANCE_NAME --zone=ZONE --format="get(id)"
   ```

3. **View application logs:**
   ```bash
   gcloud logging read "resource.type=gce_instance AND resource.labels.instance_id=INSTANCE_ID" --limit=20 --format="table(timestamp,severity,textPayload)"
   ```

4. **Check for errors in logs:**
   ```bash
   gcloud logging read "resource.type=gce_instance AND resource.labels.instance_id=INSTANCE_ID AND severity>=ERROR" --limit=10
   ```

5. **Real-time log streaming:**
   ```bash
   gcloud logging tail "resource.type=gce_instance AND resource.labels.instance_id=INSTANCE_ID"
   ```

## Known Instance Details
- Instance Name: instance-20250825-143058
- Zone: us-central1-c
- Instance ID: 8718870209064193364

## Deployment Safety Rules
- NEVER break working functionality
- Test changes locally first
- Use git reset --hard to revert broken deployments immediately
- Force push reverts to restore production quickly


---
Provide project context and coding guidelines that AI should follow when generating code, answering questions, or reviewing changes.