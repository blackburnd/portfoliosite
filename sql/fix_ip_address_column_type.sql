-- Fix ip_address column to use VARCHAR instead of INET type
-- Empty the column first, then change the type

UPDATE app_log SET ip_address = NULL;

ALTER TABLE app_log ALTER COLUMN ip_address TYPE VARCHAR(45);
