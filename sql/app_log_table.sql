-- Table: app_log
-- Modern log entry columns: id, timestamp, level, message, module, function, line, user, extra
-- PostgreSQL compatible version
CREATE TABLE IF NOT EXISTS app_log (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    level TEXT NOT NULL,
    message TEXT NOT NULL,
    module TEXT,
    function TEXT,
    line INTEGER,
    "user" TEXT,
    extra TEXT
);
