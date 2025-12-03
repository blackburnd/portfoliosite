"""
Integration tests using the test app to verify test infrastructure.
"""
import pytest
from .test_app import test_client, test_app


@pytest.mark.unit
class TestTestInfrastructure:
    """Test that our test infrastructure is working correctly."""

    def test_test_app_creation(self):
        """Test that the test app is created successfully."""
        assert test_app is not None
        assert test_app.title == "Portfolio Test App"

    def test_test_client_creation(self):
        """Test that the test client is created successfully."""
        assert test_client is not None

    def test_test_root_endpoint(self):
        """Test the test app root endpoint."""
        response = test_client.get("/")
        assert response.status_code == 200
        assert response.json() == {"message": "Test app running"}

    def test_test_health_endpoint(self):
        """Test the test app health endpoint."""
        response = test_client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


@pytest.mark.integration
class TestTestEnvironment:
    """Test that the test environment is configured correctly."""

    def test_environment_variables(self):
        """Test that test environment variables are set."""
        import os
        assert os.getenv('ENV') == 'testing'
        assert os.getenv('DATABASE_URL') is not None
        assert os.getenv('ADMIN_USERNAME') is not None

    def test_pytest_markers(self):
        """Test that pytest markers are working."""
        # This test itself uses markers, so if it runs, markers work
        assert True

    def test_asyncio_support(self):
        """Test that asyncio support is working."""
        import asyncio
        
        async def async_test():
            return "async works"
        
        # Run the async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(async_test())
            assert result == "async works"
        finally:
            loop.close()