# SMTP Email Configuration for Contact Form

## Security: Never Commit Credentials

**NEVER** commit SMTP credentials to the repository. They should only exist on the production server.

## Quick Setup (Recommended)

### Step 1: Get Gmail App Password

1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Enable **2-Step Verification** 
3. Go to [App Passwords](https://myaccount.google.com/apppasswords)
4. Generate password for **Mail**
5. Copy the 16-character password

### Step 2: Configure on Production Server

SSH into production and run the automated script:

```bash
# SSH into the server
gcloud compute ssh blackburnd@instance-20250825-143058 --zone us-central1-c

# Navigate to app directory
cd /opt/portfoliosite
git pull

# Run configuration script
sudo ./configure_smtp.sh
```

The script will:
- Prompt for SMTP credentials (password input is hidden)
- Store them securely in `/etc/environment`
- Set proper file permissions (600)
- Restart the service to apply changes

### Step 3: Test

1. Visit https://www.blackburnsystems.com/contact/
2. Submit a test message
3. Check email and logs: `sudo journalctl -u portfolio -f`

## Environment Variables

These are configured in `/etc/environment` on the production server:

```bash
SMTP_USERNAME="your-email@gmail.com"       # Your Gmail address
SMTP_PASSWORD="your-app-password"          # 16-char app password
SMTP_HOST="smtp.gmail.com"                 # SMTP server
SMTP_PORT="587"                            # SMTP port
SMTP_FROM_EMAIL="your-email@gmail.com"     # From address
CONTACT_NOTIFICATION_EMAIL="your-email@gmail.com"  # Where to receive contacts
```

## Other Email Providers

### SendGrid
```bash
SMTP_HOST="smtp.sendgrid.net"
SMTP_PORT="587"
SMTP_USERNAME="apikey"
SMTP_PASSWORD="your-sendgrid-api-key"
```

### AWS SES
```bash
SMTP_HOST="email-smtp.us-east-1.amazonaws.com"
SMTP_PORT="587"
SMTP_USERNAME="your-ses-username"
SMTP_PASSWORD="your-ses-password"
```

### Mailgun
```bash
SMTP_HOST="smtp.mailgun.org"
SMTP_PORT="587"
SMTP_USERNAME="postmaster@your-domain.mailgun.org"
SMTP_PASSWORD="your-mailgun-password"
```

## Testing

Once configured, contact form submissions will:
1. Save to the database (as before)
2. Send an email notification to `CONTACT_NOTIFICATION_EMAIL`
3. Log the email send status

## Fallback Behavior

If email configuration is missing:
- Contact forms still work and save to database
- Warning is logged about missing email configuration
- No email is sent (graceful degradation)

## Email Content

The notification email includes:
- Contact ID for reference
- Sender's name and email
- Subject line
- Full message content
- Timestamp information
