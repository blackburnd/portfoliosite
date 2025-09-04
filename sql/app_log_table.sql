-- Table: app_log
-- Modern log entry columns: id, timestamp, level, message, module, function, line, user, extra
CREATE TABLE IF NOT EXISTS app_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    level TEXT NOT NULL,
    message TEXT NOT NULL,
    module TEXT,
    function TEXT,
    line INTEGER,
    user TEXT,
    extra TEXT
);
