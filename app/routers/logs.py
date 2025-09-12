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
                   user, extra, ip_address, traceback
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
