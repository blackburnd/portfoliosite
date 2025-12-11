#!/bin/bash
# Script to configure SMTP settings on production server
# Run this directly on the production server via SSH
# Usage: sudo ./configure_smtp.sh

set -e

echo "========================================="
echo "SMTP Configuration Setup"
echo "========================================="
echo ""
echo "This script will configure SMTP settings for contact form emails."
echo "Your credentials will be stored securely in /etc/environment"
echo "and will NOT be committed to the repository."
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: Please run as root (use sudo)"
    exit 1
fi

# Prompt for SMTP settings
read -p "SMTP Username (e.g., blackburnd@gmail.com): " SMTP_USERNAME
read -s -p "SMTP App Password (will be hidden): " SMTP_PASSWORD
echo ""
read -p "SMTP Host [smtp.gmail.com]: " SMTP_HOST
SMTP_HOST=${SMTP_HOST:-smtp.gmail.com}
read -p "SMTP Port [587]: " SMTP_PORT
SMTP_PORT=${SMTP_PORT:-587}
read -p "From Email [${SMTP_USERNAME}]: " SMTP_FROM_EMAIL
SMTP_FROM_EMAIL=${SMTP_FROM_EMAIL:-${SMTP_USERNAME}}
read -p "Notification Email (where to receive contacts) [${SMTP_USERNAME}]: " CONTACT_NOTIFICATION_EMAIL
CONTACT_NOTIFICATION_EMAIL=${CONTACT_NOTIFICATION_EMAIL:-${SMTP_USERNAME}}

echo ""
echo "Configuring SMTP settings..."

# Backup existing /etc/environment
cp /etc/environment /etc/environment.backup.$(date +%Y%m%d_%H%M%S)

# Remove existing SMTP settings if they exist
sed -i '/^SMTP_USERNAME=/d' /etc/environment
sed -i '/^SMTP_PASSWORD=/d' /etc/environment
sed -i '/^SMTP_HOST=/d' /etc/environment
sed -i '/^SMTP_PORT=/d' /etc/environment
sed -i '/^SMTP_FROM_EMAIL=/d' /etc/environment
sed -i '/^CONTACT_NOTIFICATION_EMAIL=/d' /etc/environment

# Add new SMTP settings
cat >> /etc/environment <<EOF

# SMTP Configuration for Contact Form Emails
SMTP_USERNAME="${SMTP_USERNAME}"
SMTP_PASSWORD="${SMTP_PASSWORD}"
SMTP_HOST="${SMTP_HOST}"
SMTP_PORT="${SMTP_PORT}"
SMTP_FROM_EMAIL="${SMTP_FROM_EMAIL}"
CONTACT_NOTIFICATION_EMAIL="${CONTACT_NOTIFICATION_EMAIL}"
EOF

# Secure the file (only root can read passwords)
chmod 600 /etc/environment

echo ""
echo "✓ SMTP configuration saved to /etc/environment"
echo "✓ File permissions secured (600)"
echo ""
echo "Restarting portfolio service to apply changes..."

# Restart the service to pick up new environment variables
systemctl restart portfolio

echo ""
echo "========================================="
echo "✓ Configuration Complete!"
echo "========================================="
echo ""
echo "SMTP is now configured with:"
echo "  Host: ${SMTP_HOST}:${SMTP_PORT}"
echo "  Username: ${SMTP_USERNAME}"
echo "  From: ${SMTP_FROM_EMAIL}"
echo "  Notifications to: ${CONTACT_NOTIFICATION_EMAIL}"
echo ""
echo "Test the contact form at: https://www.blackburnsystems.com/contact/"
echo "Check logs: sudo journalctl -u portfolio -f"
echo ""
