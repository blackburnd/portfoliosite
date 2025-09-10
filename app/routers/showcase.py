from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter()

@router.get("/showcase/complex_schema.svg")
async def showcase_complex_schema():
    """Serve the interactive complex_schema.svg file."""
    return FileResponse(
        path="assets/showcase/complex_schema.svg",
        media_type="image/svg+xml",
        filename="complex_schema.svg",
        headers={"Content-Disposition": "inline"}
    )
