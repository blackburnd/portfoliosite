"""
Contact Submissions Admin Router
Provides admin interface for viewing and managing contact form submissions
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime, timedelta
from typing import Optional

from auth import require_admin_auth
from database import database

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/contact-submissions", response_class=HTMLResponse)
async def contact_submissions_admin_page(
    request: Request,
    admin: dict = Depends(require_admin_auth)
):
    """Display the contact submissions admin page"""
    return templates.TemplateResponse("contact_submissions.html", {
        "request": request,
        "current_page": "contact_submissions",
        "user_authenticated": True,
        "user_email": admin.get("email"),
        "admin": admin
    })


@router.get("/contact-submissions/data", response_class=JSONResponse)
async def get_contact_submissions_data(
    request: Request,
    offset: int = 0,
    limit: int = 50,
    search: Optional[str] = None,
    status: Optional[str] = None,
    time_filter: Optional[str] = None,
    sort_field: str = "created_at",
    sort_order: str = "desc",
    admin: dict = Depends(require_admin_auth)
):
    """
    Get contact submissions data with pagination, filtering, and search

    Query parameters:
    - offset: Starting position for pagination
    - limit: Number of records to return
    - search: Search term for name, email, subject, or message
    - status: Filter by read status ('read', 'unread')
    - time_filter: Filter by time period ('1h', '24h', '7d')
    - sort_field: Field to sort by
    - sort_order: Sort order ('asc' or 'desc')
    """

    # Build the WHERE clause with filters
    where_conditions = []
    params = {}

    # Search filter
    if search:
        where_conditions.append("""
            (name ILIKE :search
             OR email ILIKE :search
             OR subject ILIKE :search
             OR message ILIKE :search)
        """)
        params["search"] = f"%{search}%"

    # Status filter
    if status == "read":
        where_conditions.append("is_read = TRUE")
    elif status == "unread":
        where_conditions.append("is_read = FALSE")

    # Time filter
    if time_filter:
        time_map = {
            "1h": timedelta(hours=1),
            "24h": timedelta(hours=24),
            "7d": timedelta(days=7)
        }
        if time_filter in time_map:
            cutoff_time = datetime.utcnow() - time_map[time_filter]
            where_conditions.append("created_at >= :cutoff_time")
            params["cutoff_time"] = cutoff_time

    # Build WHERE clause
    where_clause = ""
    if where_conditions:
        where_clause = "WHERE " + " AND ".join(where_conditions)

    # Validate sort field to prevent SQL injection
    valid_sort_fields = ["created_at", "name", "email", "subject", "is_read"]
    if sort_field not in valid_sort_fields:
        sort_field = "created_at"

    # Validate sort order
    if sort_order.lower() not in ["asc", "desc"]:
        sort_order = "desc"

    # Get total count
    count_query = f"SELECT COUNT(*) FROM contact_messages {where_clause}"
    total_count = await database.fetch_val(count_query, params)

    # Get paginated data
    data_query = f"""
        SELECT
            id,
            portfolio_id,
            name,
            email,
            subject,
            message,
            created_at,
            is_read
        FROM contact_messages
        {where_clause}
        ORDER BY {sort_field} {sort_order}
        LIMIT :limit OFFSET :offset
    """
    params["limit"] = limit
    params["offset"] = offset

    rows = await database.fetch_all(data_query, params)

    # Convert rows to dictionaries
    submissions = []
    for row in rows:
        submissions.append({
            "id": str(row["id"]),
            "portfolio_id": str(row["portfolio_id"]),
            "name": row["name"],
            "email": row["email"],
            "subject": row["subject"],
            "message": row["message"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "is_read": row["is_read"]
        })

    # Calculate pagination info
    total_pages = (total_count + limit - 1) // limit if limit > 0 else 1
    current_page = (offset // limit) + 1 if limit > 0 else 1
    has_more = (offset + limit) < total_count

    return {
        "submissions": submissions,
        "total_count": total_count,
        "has_more": has_more,
        "pagination": {
            "total": total_count,
            "page": current_page,
            "pages": total_pages,
            "offset": offset,
            "limit": limit
        }
    }


@router.post("/contact-submissions/mark-read/{submission_id}")
async def mark_submission_read(
    submission_id: str,
    admin: dict = Depends(require_admin_auth)
):
    """Mark a contact submission as read"""
    query = """
        UPDATE contact_messages
        SET is_read = TRUE
        WHERE id = :id
        RETURNING id
    """
    result = await database.fetch_one(query, {"id": submission_id})

    if not result:
        raise HTTPException(status_code=404, detail="Submission not found")

    return {"success": True, "message": "Submission marked as read"}


@router.post("/contact-submissions/mark-unread/{submission_id}")
async def mark_submission_unread(
    submission_id: str,
    admin: dict = Depends(require_admin_auth)
):
    """Mark a contact submission as unread"""
    query = """
        UPDATE contact_messages
        SET is_read = FALSE
        WHERE id = :id
        RETURNING id
    """
    result = await database.fetch_one(query, {"id": submission_id})

    if not result:
        raise HTTPException(status_code=404, detail="Submission not found")

    return {"success": True, "message": "Submission marked as unread"}


@router.delete("/contact-submissions/delete/{submission_id}")
async def delete_submission(
    submission_id: str,
    admin: dict = Depends(require_admin_auth)
):
    """Delete a single contact submission"""
    query = "DELETE FROM contact_messages WHERE id = :id RETURNING id"
    result = await database.fetch_one(query, {"id": submission_id})

    if not result:
        raise HTTPException(status_code=404, detail="Submission not found")

    return {"success": True, "message": "Submission deleted"}


@router.post("/contact-submissions/clear")
async def clear_all_submissions(
    admin: dict = Depends(require_admin_auth)
):
    """Delete all contact submissions"""
    query = "DELETE FROM contact_messages"
    await database.execute(query)

    return {"success": True, "message": "All submissions cleared"}
