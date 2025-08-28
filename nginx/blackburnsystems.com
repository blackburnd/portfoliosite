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
    listen 443 ssl;
    server_name www.blackburnsystems.com;
    ssl_certificate /etc/letsencrypt/live/blackburnsystems.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/blackburnsystems.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
   
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Handle static assets
    location /assets/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

