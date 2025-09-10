# Redirect bare domain to www
server {
    listen 80;
    server_name blackburnsystems.com;
    return 301 https://www.blackburnsystems.com$request_uri;
}

# Main server block for www
server {
    listen 80;
    server_name www.blackburnsystems.com;
    return 301 https://www.blackburnsystems.com$request_uri;
}

# Redirect bare domain to www for HTTPS
server {
    listen 443 ssl;
    server_name blackburnsystems.com;
    ssl_certificate /etc/letsencrypt/live/blackburnsystems.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/blackburnsystems.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
    return 301 https://www.blackburnsystems.com$request_uri;
}

# Main HTTPS server block for www
server {
    listen 443 ssl http2;
    server_name www.blackburnsystems.com;
    
    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/blackburnsystems.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/blackburnsystems.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    # OAuth popup support - allow same-origin popups to communicate
    add_header Cross-Origin-Opener-Policy "same-origin-allow-popups" always;
    add_header Cross-Origin-Embedder-Policy "unsafe-none" always;
    
    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;
    
    # Client max body size for file uploads
    client_max_body_size 10M;
    
    # Handle static assets directly (more efficient than proxying)
    location /assets/ {
        alias /opt/portfoliosite/assets/;
        expires 1y;
        add_header Cache-Control "public, immutable";
        
        # Enable directory browsing
        autoindex on;
        autoindex_exact_size off;
        autoindex_format html;
        autoindex_localtime on;
        
        # Fallback to FastAPI if file not found (for dynamic directory listing)
        try_files $uri $uri/ @fastapi;
    }
    
    # Special handling for resume
    location = /resume {
        return 302 /assets/files/danielblackburn.pdf;
    }
    
    location = /resume/ {
        return 302 /assets/files/danielblackburn.pdf;
    }
    
    # FastAPI application
    location / {
        try_files $uri @fastapi;
    }
    
    location @fastapi {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Port $server_port;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Handle health checks
    location = /health {
        proxy_pass http://127.0.0.1:8000;
        access_log off;
    }
    
    # Block access to sensitive files
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }
    
    location ~ \.(env|log|ini)$ {
        deny all;
        access_log off;
        log_not_found off;
    }
}

