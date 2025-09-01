#!/usr/bin/env python3
# Simple test to verify log viewer works without database dependencies

import os
os.environ["DATABASE_URL"] = "sqlite:///test.db"  # Set a dummy URL to avoid import errors

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from log_capture import log_capture
import logging

# Create simple app
app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Set up some test logging
logger = logging.getLogger("test")
logger.info("Starting log viewer test")
logger.warning("This is a test warning")
logger.error("This is a test error")

@app.get("/admin/logs", response_class=HTMLResponse)
async def logs_admin_page(request: Request):
    """Admin page for viewing application logs"""
    return templates.TemplateResponse("logs.html", {
        "request": request,
        "current_page": "logs"
    })

@app.get("/admin/logs/data")
async def get_logs_data():
    """API endpoint to get log data as JSON"""
    logs = log_capture.get_logs()
    stats = log_capture.get_stats()
    return JSONResponse({
        "logs": logs,
        "stats": stats
    })

@app.post("/admin/logs/clear")
async def clear_logs_data():
    """API endpoint to clear all logs"""
    log_capture.clear_logs()
    return JSONResponse({"status": "success", "message": "Logs cleared"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8004)
