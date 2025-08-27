#!/bin/bash
set -e

EMAIL="daniel@blackburn.systems"
DOMAIN="blackburnsystems.com"
WWW_DOMAIN="www.blackburnsystems.com"

# Install Certbot if it's not already installed
if ! command -v certbot &> /dev/null
then
    echo "Certbot not found. Installing..."
    sudo apt-get update
    sudo apt-get install -y certbot python3-certbot-nginx
else
    echo "Certbot is already installed."
fi

# Run Certbot to obtain/renew the certificate and configure Nginx.
# This command will obtain a new certificate if one doesn't exist,
# or renew it if it's close to expiring. It will also ensure the
# Nginx configuration is correctly set up for SSL.
sudo certbot --nginx \
    --redirect \
    --non-interactive \
    --agree-tos \
    -m "$EMAIL" \
    -d "$DOMAIN" \
    -d "$WWW_DOMAIN"

echo "SSL setup script finished."
