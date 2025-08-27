# nginx VirtualHost Configuration

## Problem
Users accessing the website were seeing the IP address (35.209.93.55) in their browser address bar instead of the domain name (www.blackburnsystems.com).

## Solution
Added nginx server blocks with `default_server` directives to handle direct IP address requests and redirect them to the proper domain name.

## Configuration Details

The nginx configuration now includes:

1. **Default HTTP Server Block**: Catches all unmatched HTTP requests (including direct IP access) and redirects to HTTPS domain
2. **Default HTTPS Server Block**: Catches all unmatched HTTPS requests and redirects to the proper domain
3. **Domain-specific Server Blocks**: Handle requests to blackburnsystems.com and www.blackburnsystems.com normally

## How It Works

- `server_name _;` acts as a wildcard to match any hostname not explicitly handled by other server blocks
- `default_server` directive ensures these blocks handle unmatched requests
- Redirects preserve the original request path using `$request_uri`
- All redirects point to `https://www.blackburnsystems.com` to ensure consistent branding

## Expected Behavior

- `http://35.209.93.55/path` → `https://www.blackburnsystems.com/path`
- `https://35.209.93.55/path` → `https://www.blackburnsystems.com/path`
- `http://blackburnsystems.com/path` → `https://blackburnsystems.com/path`
- `http://www.blackburnsystems.com/path` → `https://www.blackburnsystems.com/path`
- `https://blackburnsystems.com/path` → served normally
- `https://www.blackburnsystems.com/path` → served normally

This ensures users always see the proper domain name in their browser address bar.