#!/bin/bash

PORT=${1:-80}

# Find the process ID (PID) of the process listening on the specified port
PID=$(lsof -t -i:$PORT)

if [ -n "$PID" ]; then
  echo "Process found on port $PORT with PID $PID. Stopping it."
  kill -9 $PID
fi

echo "Starting application on port $PORT"
source venv/bin/activate
nohup uvicorn main:app --host 0.0.0.0 --port $PORT &
