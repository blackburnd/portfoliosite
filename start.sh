#!/bin/bash

PORT=${1:-80}

# Set default DATABASE_URL if not already set
if [ -z "$DATABASE_URL" ]; then
    export DATABASE_URL="postgresql://postgres:password@35.184.209.128:5432/daniel_portfolio"
    echo "Using default DATABASE_URL"
else
    echo "Using provided DATABASE_URL"
fi

# Find the process ID (PID) of the process listening on the specified port
PID=$(lsof -t -i:$PORT)

if [ -n "$PID" ]; then
  echo "Process found on port $PORT with PID $PID. Stopping it."
  kill -9 $PID
fi

echo "Starting GraphQL FastAPI application on port $PORT"
cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "Activated virtual environment"
else
    echo "No virtual environment found, using system Python"
fi

# Test database connection before starting
echo "Testing database connection..."
python3 test_database.py
if [ $? -eq 0 ]; then
    echo "Database connection successful, starting application..."
    nohup uvicorn main:app --host 0.0.0.0 --port $PORT &
    echo "Application started with PID $!"
    echo "GraphQL endpoint: http://localhost:$PORT/graphql"
    echo "GraphQL Playground: http://localhost:$PORT/playground"
else
    echo "Database connection failed, starting application anyway (will retry on startup)..."
    nohup uvicorn main:app --host 0.0.0.0 --port $PORT &
    echo "Application started with PID $!"
    echo "Warning: Database connection issues detected"
fi
