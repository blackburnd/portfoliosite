#!/bin/bash
# Debug startup script for local development
# This script starts the FastAPI server with proper environment variables and logs

# Use environment variable or fallback to local SQLite
export DATABASE_URL="${DATABASE_URL:-sqlite:///./test.db}"
sleep 2 && ./venv/bin/python -m uvicorn main:app --reload --host 0.0.0.0 --port 8001
