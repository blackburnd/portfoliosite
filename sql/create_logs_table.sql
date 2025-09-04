-- Create application_logs table for internal logging
-- This table will store log entries from the application instead of relying on syslog

CREATE TABLE IF NOT EXISTS application_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    level VARCHAR(20) NOT NULL CHECK (level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')),
    source VARCHAR(100) NOT NULL,  -- logger name or source component
    message TEXT NOT NULL,
    -- Additional metadata fields for modern logging
    request_id VARCHAR(100),       -- for tracing requests
    user_id VARCHAR(100),         -- for user-specific logs
    session_id VARCHAR(100),      -- for session tracking
    ip_address INET,              -- client IP address
    user_agent TEXT,              -- client user agent
    extra_data JSONB DEFAULT '{}'::jsonb,  -- flexible field for additional log data
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_application_logs_timestamp ON application_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_application_logs_level ON application_logs(level);
CREATE INDEX IF NOT EXISTS idx_application_logs_source ON application_logs(source);
CREATE INDEX IF NOT EXISTS idx_application_logs_request_id ON application_logs(request_id);
CREATE INDEX IF NOT EXISTS idx_application_logs_created_at ON application_logs(created_at DESC);

-- Create partial index for errors and warnings (most important logs)
CREATE INDEX IF NOT EXISTS idx_application_logs_errors ON application_logs(timestamp DESC) 
WHERE level IN ('ERROR', 'WARNING', 'CRITICAL');

-- Add comment to document the table purpose
COMMENT ON TABLE application_logs IS 'Internal application logging table for debugging and monitoring';
COMMENT ON COLUMN application_logs.level IS 'Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL';
COMMENT ON COLUMN application_logs.source IS 'Logger name or source component that generated the log';
COMMENT ON COLUMN application_logs.extra_data IS 'Additional structured data in JSON format';