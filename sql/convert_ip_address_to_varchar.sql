-- Migration: Convert ip_address column from INET to VARCHAR for simplicity
-- This avoids JSON serialization issues with PostgreSQL INET types

-- Drop existing indexes on ip_address column
DROP INDEX IF EXISTS idx_app_log_ip_address;
DROP INDEX IF EXISTS idx_app_log_timestamp_ip;

-- Convert the column type from INET to VARCHAR
ALTER TABLE app_log 
ALTER COLUMN ip_address TYPE VARCHAR(45) USING ip_address::text;

-- Recreate indexes for IP address lookups
CREATE INDEX IF NOT EXISTS idx_app_log_ip_address ON app_log(ip_address);

-- Recreate index for timestamp + IP for time-based IP analysis  
CREATE INDEX IF NOT EXISTS idx_app_log_timestamp_ip ON app_log(timestamp, ip_address);
