-- Create page analytics table for tracking site usage
CREATE TABLE IF NOT EXISTS page_analytics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    page_path TEXT NOT NULL,
    ip_address INET,
    user_agent TEXT,
    referer TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_page_analytics_timestamp ON page_analytics(timestamp);
CREATE INDEX IF NOT EXISTS idx_page_analytics_page_path ON page_analytics(page_path);
CREATE INDEX IF NOT EXISTS idx_page_analytics_ip ON page_analytics(ip_address);