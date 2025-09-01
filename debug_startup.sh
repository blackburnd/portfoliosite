#!/bin/bash
# Debug startup script for local development
# This script starts the FastAPI server with proper environment variables and logs

sleep 2 && export DATABASE_URL="postgresql://postgres:-8JB6On1kTf6puF-@35.184.209.128:5432/daniel_portfolio" && ./venv/bin/python -m uvicorn main:app --reload --host 0.0.0.0 --port 8001
