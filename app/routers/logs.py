from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import time
import json
import traceback
from datetime import datetime
from typing import Optional

from auth import require_admin_auth
from database import database
from log_capture import add_log

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/logs", response_class=HTMLResponse)
async def logs_admin_page(request: Request):
    """Application logs viewer interface"""
    return templates.TemplateResponse("logs.html", {
        "request": request,
        "current_page": "logs",
        "user_info": None,
        "user_authenticated": False,
        "user_email": "",
        "cache_bust_version": str(int(time.time()))
    })


@router.get("/logs/data")
async def get_logs_data(
    request: Request,
    offset: int = 0,
    limit: int = 50,
    page: int = None,
    sort_field: str = "timestamp",
    sort_order: str = "desc",
    search: Optional[str] = None,
    level: Optional[str] = None,
    module: Optional[str] = None,
    time_filter: Optional[str] = None
):
    """Get log data for endless scrolling logs interface"""
    if page is not None:
        offset = (page - 1) * limit

    def serialize_datetime(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return obj

    try:
        valid_sort_fields = {
            "timestamp", "level", "message", "module",
            "function", "line", "user", "ip_address"
        }
        if sort_field not in valid_sort_fields:
            sort_field = "timestamp"

        if sort_order.lower() not in {"asc", "desc"}:
            sort_order = "desc"

        where_conditions = []
        params = {"limit": limit, "offset": offset}

        from database import PORTFOLIO_ID
        where_conditions.append("portfolio_id = :portfolio_id")
        params["portfolio_id"] = PORTFOLIO_ID

        if search:
            where_conditions.append(
                "(message ILIKE :search OR module ILIKE :search OR "
                "function ILIKE :search)"
            )
            params["search"] = f"%{search}%"

        if level:
            where_conditions.append("LOWER(level) = LOWER(:level)")
            params["level"] = level

        if module:
            where_conditions.append("module = :module")
            params["module"] = module

        if time_filter:
            interval = {
                "1h": "1 hour", "24h": "24 hours", "7d": "7 days"
            }.get(time_filter)
            if interval:
                where_conditions.append(
                    f"timestamp >= NOW() - INTERVAL '{interval}'"
                )

        where_clause = ("WHERE " + " AND ".join(where_conditions)
                        if where_conditions else "")

        count_query = f"SELECT COUNT(*) as count FROM app_log {where_clause}"
        count_params = {
            k: v for k, v in params.items() if k not in ['limit', 'offset']
        }
        count_result = await database.fetch_one(count_query, count_params)
        total_count = count_result['count'] if count_result else 0

        order_clause = f"ORDER BY {sort_field} {sort_order.upper()}"
        logs_query = f"""
            SELECT timestamp, level, message, module, function, line,
                   user, extra, ip_address
            FROM app_log {where_clause} {order_clause}
            LIMIT :limit OFFSET :offset
        """
        logs = await database.fetch_all(logs_query, params)
        logs_data = [dict(log) for log in logs]

        return JSONResponse({
            "status": "success",
            "logs": json.loads(
                json.dumps(logs_data, default=serialize_datetime)
            ),
            "has_more": len(logs_data) == limit,
            "pagination": {
                "page": (offset // limit) + 1,
                "limit": limit,
                "offset": offset,
                "total": total_count,
                "showing": len(logs_data)
            }
        })
    except Exception as e:
        add_log(
            "ERROR", "logs_endpoint", f"Failed to fetch logs: {e}",
            extra=traceback.format_exc()
        )
        return JSONResponse(
            {"status": "error", "message": f"Failed to fetch logs: {e}"},
            status_code=500
        )


@router.post("/logs/clear")
async def clear_logs(
    request: Request,
    admin: dict = Depends(require_admin_auth)
):
    """Clear all application logs"""
    try:
        user_email = admin.get("email", "unknown")
        add_log(
            "INFO", "logs_admin",
            f"Admin ({user_email}) cleared all application logs",
            function="clear_logs"
        )
        await database.execute("DELETE FROM app_log")
        return JSONResponse(
            {"status": "success", "message": "All logs cleared successfully"}
        )
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": f"Failed to clear logs: {e}"},
            status_code=500
        )


@router.get("/logs/level")
async def get_log_level(
    request: Request, user_info=Depends(require_admin_auth)
):
    """Get current log level"""
    import logging
    
    try:
        # Get main application logger
        main_logger = logging.getLogger('portfoliosite')
        current_level = main_logger.level
        level_name = logging.getLevelName(current_level)
        
        # Get other important loggers
        uvicorn_access_logger = logging.getLogger('uvicorn.access')
        uvicorn_access_level = logging.getLevelName(
            uvicorn_access_logger.level
        )
        
        uvicorn_error_logger = logging.getLogger('uvicorn.error')
        uvicorn_error_level = logging.getLevelName(uvicorn_error_logger.level)
        
        databases_logger = logging.getLogger('databases')
        databases_level = logging.getLevelName(databases_logger.level)
        
        return JSONResponse({
            "status": "success",
            "current_level": level_name,
            "current_level_number": current_level,
            "loggers": {
                "portfoliosite": level_name,
                "uvicorn.access": uvicorn_access_level,
                "uvicorn.error": uvicorn_error_level,
                "databases": databases_level
            },
            "available_levels": {
                "DEBUG": logging.DEBUG,
                "INFO": logging.INFO,
                "WARNING": logging.WARNING,
                "ERROR": logging.ERROR,
                "CRITICAL": logging.CRITICAL
            }
        })
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": f"Failed to get log level: {e}"},
            status_code=500
        )


@router.post("/logs/level")
async def set_log_level(
    request: Request,
    user_info=Depends(require_admin_auth)
):
    """Set runtime log level"""
    import logging
    
    try:
        data = await request.json()
        new_level = data.get("level")
        
        if not new_level:
            return JSONResponse(
                {"status": "error", "message": "Level is required"},
                status_code=400
            )
        
        # Convert level name to number if needed
        if isinstance(new_level, str):
            level_mapping = {
                "DEBUG": logging.DEBUG,
                "INFO": logging.INFO,
                "WARNING": logging.WARNING,
                "ERROR": logging.ERROR,
                "CRITICAL": logging.CRITICAL
            }
            if new_level.upper() not in level_mapping:
                error_msg = f"Invalid log level: {new_level}"
                return JSONResponse(
                    {"status": "error", "message": error_msg},
                    status_code=400
                )
            new_level_number = level_mapping[new_level.upper()]
            level_name = new_level.upper()
        else:
            new_level_number = new_level
            level_name = logging.getLevelName(new_level_number)
        
        # Set the main application logger level
        main_logger = logging.getLogger('portfoliosite')
        old_level = logging.getLevelName(main_logger.level)
        main_logger.setLevel(new_level_number)
        
        # Log the change
        user_email = user_info.get("email", "unknown")
        log_msg = (f"Admin ({user_email}) changed log level "
                   f"from {old_level} to {level_name}")
        add_log(
            level="info",
            message=log_msg,
            module="logs_admin",
            function="set_log_level"
        )
        
        return JSONResponse({
            "status": "success",
            "message": f"Log level changed from {old_level} to {level_name}",
            "old_level": old_level,
            "new_level": level_name
        })
        
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": f"Failed to set log level: {e}"},
            status_code=500
        )
