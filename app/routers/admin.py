import time
import json
import traceback
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.templating import Jinja2Templates

from auth import require_admin_auth
from database import database
from log_capture import add_log, log_with_context
from schema_dump import generate_schema_dump

router = APIRouter()
templates = Jinja2Templates(directory="templates")


# --- Work Admin Page ---
@router.get("/workadmin", response_class=HTMLResponse)
async def work_admin_page(
    request: Request,
    admin: dict = Depends(require_admin_auth)
):
    return templates.TemplateResponse("workadmin.html", {
        "request": request,
        "current_page": "workadmin",
        "user_info": admin,
        "user_authenticated": True,
        "user_email": admin.get("email", "")
    })


# --- Logs Admin Page ---
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


# --- SQL Admin Tool ---
@router.get("/admin/sql", response_class=HTMLResponse)
async def sql_admin_page(
    request: Request,
    admin: dict = Depends(require_admin_auth)
):
    """SQL Admin interface for executing database queries"""
    return templates.TemplateResponse("sql_admin.html", {
        "request": request,
        "current_page": "sql_admin",
        "user_info": admin,
        "user_authenticated": True,
        "user_email": admin.get("email", "")
    })


@router.post("/admin/sql/execute")
async def execute_sql(
    request: Request,
    admin: dict = Depends(require_admin_auth)
):
    """Execute SQL query against the database"""
    start_time = time.time()

    def serialize_special_types(obj):
        import uuid
        from datetime import datetime, date
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, uuid.UUID):
            return str(obj)
        return obj

    try:
        body = await request.json()
        query = body.get("query", "").strip()
        if not query:
            return JSONResponse(
                {"status": "error", "message": "No query provided"},
                status_code=400
            )

        user_email = admin.get('email', 'unknown')
        log_with_context(
            "INFO", "sql_admin",
            f"SQL Query executed by {user_email}: {query[:200]}",
            request
        )

        is_select = query.upper().strip().startswith('SELECT')
        if is_select:
            rows = await database.fetch_all(query)
            rows_data = [dict(row) for row in rows]
            execution_time = round((time.time() - start_time) * 1000, 2)
            return JSONResponse({
                "status": "success",
                "rows": json.loads(
                    json.dumps(rows_data, default=serialize_special_types)
                ),
                "columns": list(rows_data[0].keys()) if rows_data else [],
                "execution_time": execution_time,
                "message": (f"Query executed successfully. "
                            f"{len(rows_data)} rows returned.")
            })
        else:
            result = await database.execute(query)
            execution_time = round((time.time() - start_time) * 1000, 2)
            return JSONResponse({
                "status": "success",
                "rows": [],
                "execution_time": execution_time,
                "message": (f"Query executed successfully. "
                            f"{result} rows affected.")
            })
    except Exception as e:
        execution_time = round((time.time() - start_time) * 1000, 2)
        return JSONResponse(
            {
                "status": "error",
                "message": str(e),
                "execution_time": execution_time
            },
            status_code=500
        )


@router.get("/admin/sql/download-schema")
async def download_schema(
    request: Request, admin: dict = Depends(require_admin_auth)
):
    """Download the current database schema as a SQL dump file"""
    try:
        log_with_context(
            "INFO", "sql_admin_schema_download",
            "Admin downloading database schema",
            request
        )
        schema_content = await generate_schema_dump()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"database_schema_{timestamp}.sql"
        return Response(
            content=schema_content,
            media_type="application/sql",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        log_with_context(
            "ERROR", "sql_admin_schema_error",
            f"Schema download error: {e}",
            request
        )
        return JSONResponse(
            {"status": "error", "message": f"Schema download failed: {e}"},
            status_code=500
        )
        