#!/bin/bash

# Load environment variables from .env file
if [ -f .env ]; then
    echo "Loading environment variables from .env..."
    export $(cat .env | grep -v '^#' | xargs)
fi

# Activate the Python 3.13 virtual environment
echo "Activating virtual environment (venv-dev with Python 3.13)..."
. venv-dev/bin/activate

# Start the FastAPI server with auto-reload for development
echo "Starting FastAPI server on http://127.0.0.1:8005"
echo "Press CTRL+C to stop"
echo ""

uvicorn main:app --reload --host 127.0.0.1 --port 8005
