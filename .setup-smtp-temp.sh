#!/bin/bash
# Temporary SMTP configuration - DO NOT COMMIT
# This file is in .gitignore

# Backup existing environment file
sudo cp /etc/environment /etc/environment.backup.$(date +%Y%m%d_%H%M%S)

# Add SMTP configuration
sudo bash -c 'cat >> /etc/environment << EOF

# SMTP Configuration for Contact Form Emails
SMTP_USERNAME="blackburnsystemsd@gmail.com"
SMTP_PASSWORD="SuperPassword#\$1103"
SMTP_HOST="smtp.gmail.com"
SMTP_PORT="587"
SMTP_FROM_EMAIL="blackburnsystemsd@gmail.com"
CONTACT_NOTIFICATION_EMAIL="blackburnd@gmail.com"
EOF'

# Secure the file
sudo chmod 600 /etc/environment

# Restart the service
sudo systemctl restart portfolio

echo "✓ SMTP configured successfully"
echo "✓ Service restarted"
echo "Test at: https://www.blackburnsystems.com/contact/"
