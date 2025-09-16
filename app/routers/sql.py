from fastapi import APIRouter, Request, Depends, Response
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates
import time
import json
import os
import subprocess
import tempfile
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
async def generate_erd(request: Request, admin: dict = Depends(require_admin_auth)):
    """Generate ERD from database schema and save to assets/files"""
    try:
        log_with_context("INFO", "sql_admin_erd", 
                         "Admin generating ERD", request)
        
        # Reuse the existing schema generation code
        schema_content = await generate_schema_dump()
        
        # Create a temporary dump file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', 
                                        delete=False) as dump_file:
            dump_file.write(schema_content)
            dump_file_path = dump_file.name
        
        try:
            # Determine the target path for saving the SVG
            target_paths = [
                "/opt/portfoliosite/assets/files/site_erd.svg",  # Production
                "assets/files/site_erd.svg"  # Local development
            ]
            
            target_path = None
            for path in target_paths:
                parent_dir = os.path.dirname(path)
                if (os.path.exists(parent_dir) or
                        parent_dir == "/opt/portfoliosite/assets/files"):
                    target_path = path
                    break
            
            if not target_path:
                # Create the assets/files directory if it doesn't exist
                os.makedirs("assets/files", exist_ok=True)
                target_path = "assets/files/site_erd.svg"
            
            # Run pypgsvg on the dump file to generate SVG directly to target
            result = subprocess.run(
                ['/opt/portfoliosite/venv/bin/python3', '-m', 'pypgsvg',
                 dump_file_path, '-o', target_path],
                capture_output=True,
                text=True,
                cwd='/opt/portfoliosite',
                env={'PYTHONPATH': '/opt/portfoliosite/venv/src/pypgsvg/src'}
            )
            
            if result.returncode != 0:
                raise Exception(f"pypgsvg failed: {result.stderr}")
            
            # Check if the SVG file was generated
            if not os.path.exists(target_path):
                raise Exception(f"Generated SVG file not found: {target_path}")
            
            log_with_context("INFO", "sql_admin_erd",
                             f"ERD saved to: {target_path}", request)
            
            # Now serve the file just like test-erd-complex
            with open(target_path, 'r') as svg_file:
                svg_content = svg_file.read()
            
            return Response(
                content=svg_content,
                media_type="image/svg+xml",
                headers={
                    "Content-Disposition": "inline; filename=site_erd.svg"
                }
            )
            
        finally:
            # Clean up the temporary dump file
            if os.path.exists(dump_file_path):
                os.unlink(dump_file_path)
                
    except Exception as e:
        log_with_context("ERROR", "sql_admin_erd_error",
                         f"ERD generation error: {e}", request)
        
        # Return an SVG error message instead of JSON
        error_msg = str(e)[:80] + "..." if len(str(e)) > 80 else str(e)
        error_svg = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="400">'
            '<rect width="800" height="400" fill="#f8f9fa" stroke="#dc3545" '
            'stroke-width="2"/>'
            '<text x="400" y="180" text-anchor="middle" font-family="Arial" '
            'font-size="24" fill="#dc3545">ERD Generation Failed</text>'
            '<text x="400" y="220" text-anchor="middle" font-family="Arial" '
            f'font-size="16" fill="#6c757d">Error: {error_msg}</text>'
            '<text x="400" y="260" text-anchor="middle" font-family="Arial" '
            'font-size="14" fill="#6c757d">Check logs for details</text>'
            '</svg>'
        )
        
        return Response(
            content=error_svg,
            media_type="image/svg+xml",
            headers={
                "Content-Disposition": "inline; filename=error.svg"
            },
            status_code=500
        )


@router.get("/admin/sql/test-erd-complex")
async def test_erd_complex(request: Request,
                           admin: dict = Depends(require_admin_auth)):
    """Test route to serve the complex_schema.svg file"""
    try:
        # Try production path first, then local development path
        svg_paths = [
            "/opt/portfoliosite/assets/files/complex_schema.svg",  # Production
            "assets/files/complex_schema.svg"  # Local development
        ]
        
        svg_path = None
        for path in svg_paths:
            if os.path.exists(path):
                svg_path = path
                break
                
        if not svg_path:
            paths_msg = f"SVG file not found in any of: {svg_paths}"
            return JSONResponse({"status": "error", "message": paths_msg},
                                status_code=404)
            
        with open(svg_path, 'r') as svg_file:
            svg_content = svg_file.read()
        
        return Response(
            content=svg_content,
            media_type="image/svg+xml",
            headers={
                "Content-Disposition": "inline; filename=complex_schema.svg"
            }
        )
        
    except Exception as e:
        error_msg = f"Error serving SVG: {e}"
        return JSONResponse({"status": "error", "message": error_msg},
                            status_code=500)


@router.get("/admin/sql/test-erd-site")
async def test_erd_site(request: Request,
                        admin: dict = Depends(require_admin_auth)):
    """Test route to serve the site_erd.svg file"""
    try:
        # Try production path first, then local development path
        svg_paths = [
            "/opt/portfoliosite/assets/files/site_erd.svg",  # Production
            "assets/files/site_erd.svg"  # Local development
        ]
        
        svg_path = None
        for path in svg_paths:
            if os.path.exists(path):
                svg_path = path
                break
                
        if not svg_path:
            paths_msg = f"SVG file not found in any of: {svg_paths}"
            return JSONResponse({"status": "error", "message": paths_msg},
                                status_code=404)
            
        with open(svg_path, 'r') as svg_file:
            svg_content = svg_file.read()
        
        return Response(
            content=svg_content,
            media_type="image/svg+xml",
            headers={
                "Content-Disposition": "inline; filename=site_erd.svg"
            }
        )
        
    except Exception as e:
        error_msg = f"Error serving SVG: {e}"
        return JSONResponse({"status": "error", "message": error_msg},
                            status_code=500)
