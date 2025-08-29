import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from httpx import AsyncClient

# Set a dummy DATABASE_URL before importing the app to avoid import-time errors
os.environ['DATABASE_URL'] = 'postgresql://test:test@localhost/test'

from main import app

# Clear startup/shutdown events to prevent database connection attempts
app.dependency_overrides = {}
app.router.startup_event_handlers = []
app.router.shutdown_event_handlers = []


@pytest.mark.asyncio
async def test_resume_redirect():
    """Test that the /resume/ endpoint redirects to the PDF."""
    async with AsyncClient(app=app, base_url="http://test", follow_redirects=False) as ac:
        response = await ac.get("/resume/")
    assert response.status_code == 302
    assert response.headers["location"] == "/assets/files/danielblackburn.pdf"

@pytest.mark.asyncio
async def test_resume_pdf_access():
    """Test that the resume PDF is accessible."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/assets/files/danielblackburn.pdf")
    assert response.status_code == 200
    assert response.headers['content-type'] == 'application/pdf'

@pytest.mark.asyncio
async def test_image_access():
    """Test that an image is accessible."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/assets/files/daniel2.jpg")
    assert response.status_code == 200
    assert response.headers['content-type'] == 'image/jpeg'
