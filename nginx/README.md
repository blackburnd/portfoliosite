# Nginx Configuration

## Overview
This directory contains the nginx configuration for blackburnsystems.com.

## Configuration File
- `blackburnsystems.com` - Main nginx configuration file

## Setup Instructions

### 1. Basic HTTP Setup (no SSL)
The current configuration will work immediately for HTTP traffic:
- Redirects bare domain to www subdomain
- Proxies requests to FastAPI application running on localhost:8000

### 2. SSL/HTTPS Setup
To enable SSL (HTTPS):

1. Run the SSL setup script:
   ```bash
   sudo ./setup_ssl.sh
   ```

2. After SSL certificates are obtained, edit `blackburnsystems.com`:
   - Uncomment the SSL server blocks (lines 53-79)
   - Update HTTP server blocks to redirect to HTTPS:
     ```nginx
     # Change this line in the HTTP www server block:
     return 301 http://www.blackburnsystems.com$request_uri;
     # To:
     return 301 https://www.blackburnsystems.com$request_uri;
     ```

### 3. Deployment
To deploy this configuration:

```bash
# Copy to nginx sites-available
sudo cp nginx/blackburnsystems.com /etc/nginx/sites-available/

# Create symlink to enable
sudo ln -sf /etc/nginx/sites-available/blackburnsystems.com /etc/nginx/sites-enabled/

# Remove default site if needed
sudo rm -f /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

## Features
- Domain redirection (bare to www)
- Proxy to FastAPI application
- Gzip compression
- SSL/TLS support (when certificates are available)
- Security headers and best practices