# Database Logging Implementation

This document describes the implementation of internal database logging for the portfolio application.

## Overview

The application now uses a dedicated PostgreSQL table (`application_logs`) to store log entries instead of relying on syslog. This provides better control, searchability, and persistence of application logs.

## Implementation Details

### 1. Database Schema

Created `sql/create_logs_table.sql` with a comprehensive logging table:

```sql
CREATE TABLE application_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    level VARCHAR(20) NOT NULL,  -- DEBUG, INFO, WARNING, ERROR, CRITICAL
    source VARCHAR(100) NOT NULL, -- logger name or component
    message TEXT NOT NULL,
    -- Enhanced metadata fields
    request_id VARCHAR(100),
    user_id VARCHAR(100), 
    session_id VARCHAR(100),
    ip_address INET,
    user_agent TEXT,
    extra_data JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 2. Core Logging Module (`log_capture.py`)

Updated to use async database operations:
- `add_log()` - Write logs to database with fallback to console
- `get_logs()` - Retrieve logs from database with filtering and pagination
- `get_stats()` - Generate statistics from database logs
- `clear_logs()` - Remove all logs from database

### 3. Standard Logging Integration (`database_logging.py`)

Created a custom logging handler that captures all Python `logging` calls:
- Runs in background thread to avoid blocking
- Automatically extracts metadata (file, line, function, exceptions)
- Queues log entries for async database writes
- Graceful fallback if database unavailable

### 4. Web Interface Updates

Updated log endpoints in `main.py`:
- `/debug/logs/data` - Now uses async database retrieval
- `/debug/logs/clear` - Now clears database table
- Maintains same JSON API for frontend compatibility

### 5. Migration and Setup

Created utilities for deployment:
- `apply_logs_migration.py` - Applies database schema
- `demo_database_logging.py` - Demonstrates functionality
- `test_logging_comprehensive.py` - Comprehensive test suite

## Usage

### Basic Logging

```python
from log_capture import log_capture

# Async logging with metadata
await log_capture.add_log(
    "INFO", 
    "my_component", 
    "Operation completed successfully",
    request_id="req-123",
    user_id="user-456",
    extra_data={"operation": "user_update"}
)

# Standard Python logging (automatically captured)
import logging
logger = logging.getLogger("my_app")
logger.info("This goes to both console and database")
logger.error("Error with context", exc_info=True)
```

### Retrieving Logs

```python
# Get recent logs
logs = await log_capture.get_logs(limit=100)

# Filter by level
error_logs = await log_capture.get_logs(level_filter="ERROR")

# Get statistics
stats = await log_capture.get_stats()
print(f"Total logs: {stats['total']}")
print(f"Errors: {stats['errors']}")
```

## Deployment Steps

1. **Apply Migration:**
   ```bash
   python apply_logs_migration.py
   ```

2. **Start Application:**
   The logging system initializes automatically when the application starts.

3. **Verify Functionality:**
   ```bash
   python demo_database_logging.py
   ```

4. **Monitor Logs:**
   Visit `/debug/logs` in the web interface to view logs in real-time.

## Features

### ✅ Modern Log Structure
- Structured logging with JSON metadata
- Request/session tracking capabilities
- IP address and user agent capture
- Flexible extra_data field for custom attributes

### ✅ High Performance
- Async database operations
- Background thread for standard logging
- Connection pooling and efficient queries
- Graceful fallback when database unavailable

### ✅ Developer Friendly
- Compatible with existing Python logging
- Rich metadata extraction
- Comprehensive test suite
- Clear migration path

### ✅ Production Ready
- Proper indexing for performance
- Log rotation handled by database
- Error handling and fallbacks
- Monitoring and statistics

## Database Indexes

The implementation includes optimized indexes:
- Primary timestamp index for chronological queries
- Level index for filtering by severity
- Source index for component-based filtering
- Partial index for errors/warnings (most critical logs)

## Backward Compatibility

- Maintains existing `/debug/logs` API
- Preserves log display format in web interface
- Falls back to demo data when database unavailable
- No breaking changes to existing logging calls

## Security Considerations

- Sensitive data filtering (can be extended)
- IP address tracking for security analysis
- User context for audit trails
- Request tracking for debugging

This implementation provides a robust, scalable logging foundation for the portfolio application while maintaining simplicity and performance.