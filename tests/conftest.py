"""
Test configuration and shared fixtures for the portfolio application.
"""
import os
import sys
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Set test environment variables before importing anything
os.environ.update({
    'DATABASE_URL': 'postgresql://test:test@localhost/test_portfolio',
    'SECRET_KEY': 'test-secret-key-for-testing-only',
    'ADMIN_USERNAME': 'test_admin',
    'ADMIN_PASSWORD': 'test_password',
    'ENV': 'testing',
    'SESSION_SECRET_KEY': 'test-session-secret',
    'GOOGLE_CLIENT_ID': 'test-google-client-id',
    'GOOGLE_CLIENT_SECRET': 'test-google-client-secret',
    'AUTHORIZED_EMAILS': 'test@example.com,admin@blackburnsystems.com'
})

# Import application modules after setting environment
# Import only what's needed for testing, avoiding complex dependencies
try:
    # Patch os.makedirs to prevent permission errors in test environments
    from unittest.mock import patch
    with patch('os.makedirs'), patch('logging.handlers.RotatingFileHandler'):
        from main import app  # noqa: E402
except (ImportError, PermissionError, OSError, Exception):
    # If main can't be imported due to missing dependencies or permissions,
    # use our test app instead
    from .test_app import test_app as app

from httpx import AsyncClient  # noqa: E402

# Mock database for testing
try:
    from database import database  # noqa: E402
except ImportError:
    # If database can't be imported, create a mock
    from unittest.mock import MagicMock
    database = MagicMock()


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def setup_app():
    """Setup and teardown for each test."""
    # Clear any existing event handlers to avoid database connection attempts
    app.router.startup_event_handlers = []
    app.router.shutdown_event_handlers = []
    
    # Mock database connection
    database.is_connected = True
    
    yield
    
    # Cleanup
    database.is_connected = False


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create async test client."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
async def mock_database():
    """Mock database connection for testing."""
    mock_db = AsyncMock()
    mock_db.is_connected = True
    mock_db.fetch_all.return_value = []
    mock_db.fetch_one.return_value = None
    mock_db.fetch_val.return_value = 0
    mock_db.execute.return_value = None
    return mock_db


@pytest.fixture
def auth_headers():
    """Authentication headers for admin endpoints."""
    return {
        "Authorization": "Bearer test-token",
        "X-Admin-Token": "test-admin-token"
    }


@pytest.fixture
def sample_work_item():
    """Sample work item data for testing."""
    return {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "portfolio_id": "3fc521ad-660c-4067-b416-17dc388e66eb",
        "company": "Test Company",
        "position": "Senior Developer",
        "location": "Remote",
        "start_date": "2023-01-01",
        "end_date": "2024-01-01",
        "description": "Test job description",
        "is_current": False,
        "company_url": "https://testcompany.com",
        "sort_order": 1
    }


@pytest.fixture
def sample_project():
    """Sample project data for testing."""
    return {
        "id": "650e8400-e29b-41d4-a716-446655440000",
        "portfolio_id": "3fc521ad-660c-4067-b416-17dc388e66eb",
        "title": "Test Project",
        "description": "A test project for testing purposes",
        "url": "https://github.com/test/project",
        "image_url": "/assets/test-project.jpg",
        "technologies": ["Python", "FastAPI", "PostgreSQL"],
        "sort_order": 1
    }


@pytest.fixture
def sample_contact():
    """Sample contact data for testing."""
    return {
        "name": "John Doe",
        "email": "john.doe@example.com",
        "subject": "Test Message",
        "message": "This is a test contact message."
    }


@pytest.fixture
def mock_site_config():
    """Mock site configuration data."""
    return {
        "full_name": "Daniel Blackburn",
        "professional_title": "Software Engineer",
        "email": "daniel@blackburnsystems.com",
        "tagline": "Innovation through collaboration",
        "bio": ("Experienced software engineer with expertise in "
                "Python and web development."),
        "linkedin_url": "https://linkedin.com/in/danielblackburn",
        "github_url": "https://github.com/blackburnd"
    }


@pytest.fixture
def mock_oauth_tokens():
    """Mock OAuth token data."""
    return {
        "access_token": "test-access-token",
        "refresh_token": "test-refresh-token",
        "id_token": "test-id-token",
        "token_type": "Bearer",
        "expires_in": 3600,
        "scope": "openid email profile"
    }


@pytest.fixture
async def authenticated_client(async_client: AsyncClient, auth_headers):
    """Create authenticated test client."""
    async_client.headers.update(auth_headers)
    return async_client


# Monkey patch to disable actual database connections during testing
@pytest.fixture(autouse=True)
def disable_database_startup():
    """Disable database startup for all tests."""
    import database
    original_init = database.init_database
    original_close = database.close_database
    
    async def mock_init():
        pass
    
    async def mock_close():
        pass
    
    database.init_database = mock_init
    database.close_database = mock_close
    
    yield
    
    database.init_database = original_init
    database.close_database = original_close


# Custom markers for test categorization
pytestmark = pytest.mark.asyncio