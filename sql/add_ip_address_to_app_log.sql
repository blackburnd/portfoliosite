-- Migration: Add ip_address column to app_log table for security monitoring
-- This will help track client IP addresses for vulnerability scanning detection

ALTER TABLE app_log 
ADD COLUMN IF NOT EXISTS ip_address INET;

-- Add index for IP address lookups (useful for security analysis)
CREATE INDEX IF NOT EXISTS idx_app_log_ip_address ON app_log(ip_address);

-- Add index for timestamp + IP for time-based IP analysis
CREATE INDEX IF NOT EXISTS idx_app_log_timestamp_ip ON app_log(timestamp, ip_address);
