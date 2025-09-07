# Email Configuration for Contact Form

## Environment Variables Required

Add these environment variables to your `.env` file or production environment:

### Gmail SMTP Configuration (Recommended)
```env
# SMTP Server Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Where to send contact form notifications
CONTACT_NOTIFICATION_EMAIL=blackburnd@gmail.com
```

### Gmail App Password Setup
1. Enable 2FA on your Gmail account
2. Go to Google Account settings → Security → 2-Step Verification → App passwords
3. Generate an app password for "Mail"
4. Use this app password as `SMTP_PASSWORD` (not your regular Gmail password)

### Other Email Providers

#### Outlook/Hotmail
```env
SMTP_SERVER=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USERNAME=your-email@outlook.com
SMTP_PASSWORD=your-password
```

#### Yahoo Mail
```env
SMTP_SERVER=smtp.mail.yahoo.com
SMTP_PORT=587
SMTP_USERNAME=your-email@yahoo.com
SMTP_PASSWORD=your-app-password
```

#### Custom SMTP Server
```env
SMTP_SERVER=mail.yourdomain.com
SMTP_PORT=587
SMTP_USERNAME=noreply@yourdomain.com
SMTP_PASSWORD=your-password
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
