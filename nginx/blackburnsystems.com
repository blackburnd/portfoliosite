# Redirect direct IP address requests to domain name
server {
    listen 80 default_server;
    server_name _;
    return 301 https://www.blackburnsystems.com$request_uri;
}

server {
    listen 80;
    server_name blackburnsystems.com www.blackburnsystems.com;
    return 301 https://$host$request_uri;
}

# Redirect HTTPS direct IP address requests to domain name
server {
    listen 443 ssl default_server;
    server_name _;
    
    # Use the same certificates as the main site
    ssl_certificate /etc/letsencrypt/live/blackburnsystems.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/blackburnsystems.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
    
    return 301 https://www.blackburnsystems.com$request_uri;
}

server {
    listen 443 ssl;
    server_name blackburnsystems.com www.blackburnsystems.com;

    # Replace with your actual certificate and key paths
    ssl_certificate /etc/letsencrypt/live/blackburnsystems.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/blackburnsystems.com/privkey.pem;

    # Recommended SSL settings
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
