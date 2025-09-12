from fastapi import APIRouter, Request, Depends, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import time
import json
from datetime import datetime

from auth import require_admin_auth
from database import database
from log_capture import log_with_context
from schema_dump import generate_schema_dump

router = APIRouter()
templates = Jinja2Templates(directory="templates")

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
            return JSONResponse({"status": "error", "message": "No query provided"}, status_code=400)

        user_email = admin.get('email', 'unknown')
        log_with_context("INFO", "sql_admin", f"SQL Query executed by {user_email}: {query[:200]}", request)

        is_select = query.upper().strip().startswith('SELECT')
        if is_select:
            rows = await database.fetch_all(query)
            rows_data = [dict(row) for row in rows]
            execution_time = round((time.time() - start_time) * 1000, 2)
            return JSONResponse({
                "status": "success",
                "rows": json.loads(json.dumps(rows_data, default=serialize_special_types)),
                "columns": list(rows_data[0].keys()) if rows_data else [],
                "execution_time": execution_time,
                "message": f"Query executed successfully. {len(rows_data)} rows returned."
            })
        else:
            result = await database.execute(query)
            execution_time = round((time.time() - start_time) * 1000, 2)
            return JSONResponse({
                "status": "success",
                "rows": [],
                "execution_time": execution_time,
                "message": f"Query executed successfully. {result} rows affected."
            })
    except Exception as e:
        execution_time = round((time.time() - start_time) * 1000, 2)
        return JSONResponse({"status": "error", "message": str(e), "execution_time": execution_time}, status_code=500)


@router.get("/admin/sql/download-schema")
async def download_schema(request: Request, admin: dict = Depends(require_admin_auth)):
    """Download the current database schema as a SQL dump file"""
    try:
        log_with_context("INFO", "sql_admin_schema_download", "Admin downloading database schema", request)
        schema_content = await generate_schema_dump()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"database_schema_{timestamp}.sql"
        return Response(
            content=schema_content,
            media_type="application/sql",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        log_with_context("ERROR", "sql_admin_schema_error", f"Schema download error: {e}", request)
        return JSONResponse({"status": "error", "message": f"Schema download failed: {e}"}, status_code=500)


@router.get("/admin/sql/generate-erd")
async def generate_erd(
    request: Request, admin: dict = Depends(require_admin_auth)
):
    """Generate an ERD from the database schema using pypgsvg"""
    try:
        log_with_context(
            "INFO", "sql_admin_erd_generation",
            "Admin generating database ERD", request
        )
        
        # Generate the schema dump content
        schema_content = await generate_schema_dump()
        
        # Import pypgsvg to generate the ERD
        try:
            from pypgsvg import generate_svg_from_sql
        except ImportError:
            log_with_context(
                "ERROR", "sql_admin_erd_error",
                "pypgsvg package not available", request
            )
            pkg_msg = ("pypgsvg package is not installed. "
                       "Please install it first.")
            return JSONResponse({
                "status": "error",
                "message": pkg_msg
            }, status_code=500)
        
        # Generate SVG from the schema
        try:
            svg_content = generate_svg_from_sql(schema_content)
        except Exception as svg_error:
            log_with_context(
                "ERROR", "sql_admin_erd_svg_error",
                f"SVG generation failed: {svg_error}", request
            )
            return JSONResponse({
                "status": "error",
                "message": f"ERD generation failed: {str(svg_error)}"
            }, status_code=500)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"database_erd_{timestamp}.svg"
        
        log_with_context(
            "INFO", "sql_admin_erd_generated",
            f"ERD generated successfully: {filename}", request
        )
        
        return Response(
            content=svg_content,
            media_type="image/svg+xml",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "image/svg+xml"
            }
        )
        
    except Exception as e:
        log_with_context(
            "ERROR", "sql_admin_erd_error",
            f"ERD generation error: {e}", request
        )
        error_msg = f"ERD generation failed: {e}"
        return JSONResponse(
            {"status": "error", "message": error_msg}, status_code=500
        )
