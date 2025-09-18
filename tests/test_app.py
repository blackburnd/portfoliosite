"""
Test-specific FastAPI application configuration.
This creates a minimal app for testing without complex production dependencies.
"""
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Create a minimal test app
test_app = FastAPI(title="Portfolio Test App", version="1.0.0")


@test_app.get("/")
async def test_root():
    """Test root endpoint."""
    return {"message": "Test app running"}


@test_app.get("/health")
async def test_health():
    """Test health check endpoint."""
    return {"status": "healthy"}


# Create test client
test_client = TestClient(test_app)