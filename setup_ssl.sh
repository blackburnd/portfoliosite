#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# --- IMPORTANT ---
# Change this to your email address for Let's Encrypt notifications.
EMAIL="blackburnd@gmail.com"
DOMAIN="blackburnsystems.com"
WWW_DOMAIN="www.blackburnsystems.com"

# Check if Nginx is installed
if ! [ -x "$(command -v nginx)" ]; then
  echo "Nginx is not installed. Please install it first."
  exit 1
fi

# Check if Certbot is installed
if ! [ -x "$(command -v certbot)" ]; then
  echo 'Certbot not found. Installing...'
  sudo apt-get update
  sudo apt-get install -y certbot python3-certbot-nginx
else
  echo 'Certbot is already installed.'
fi

# Check if a certificate already exists to avoid hitting rate limits
if [ -d "/etc/letsencrypt/live/$DOMAIN" ]; then
  echo "Certificate for $DOMAIN already exists."
  echo "To renew, run 'sudo certbot renew'."
else
  echo "Requesting a new certificate for $DOMAIN."
  # Use certbot to automatically obtain a certificate and configure Nginx.
  # --non-interactive: Run without asking questions.
  # --agree-tos: Agree to the Let's Encrypt Terms of Service.
  # -m: Email for urgent renewal and security notices.
  # --nginx: Use the Nginx plugin to modify the config.
  # -d: Specify the domains.
  sudo certbot --nginx -d $DOMAIN -d $WWW_DOMAIN --non-interactive --agree-tos -m $EMAIL --redirect
  echo "Certbot has been configured."
fi

echo "SSL setup script finished."
