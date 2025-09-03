-- Migration to make start_date nullable in work_experience table
-- Run this against the production database

ALTER TABLE work_experience ALTER COLUMN start_date DROP NOT NULL;
