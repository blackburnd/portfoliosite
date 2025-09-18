"""
Tests for API endpoints and routes.
"""
import pytest
from httpx import AsyncClient
from unittest.mock import patch


@pytest.mark.unit
class TestPublicEndpoints:
    """Test public API endpoints that don't require authentication."""

    async def test_home_page_loads(self, async_client: AsyncClient):
        """Test that the home page loads successfully."""
        response = await async_client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers['content-type']

    async def test_contact_page_loads(self, async_client: AsyncClient):
        """Test that the contact page loads successfully."""
        response = await async_client.get("/contact/")
        assert response.status_code == 200
        assert "text/html" in response.headers['content-type']
        assert "Let's Talk" in response.text

    async def test_work_page_loads(self, async_client: AsyncClient):
        """Test that the work/portfolio page loads successfully."""
        response = await async_client.get("/work/")
        assert response.status_code == 200
        assert "text/html" in response.headers['content-type']

    async def test_privacy_page_loads(self, async_client: AsyncClient):
        """Test that the privacy policy page loads successfully."""
        response = await async_client.get("/privacy/")
        assert response.status_code == 200
        assert "text/html" in response.headers['content-type']

    async def test_resume_redirect(self, async_client: AsyncClient):
        """Test that the resume endpoint redirects to PDF."""
        response = await async_client.get("/resume/", follow_redirects=False)
        assert response.status_code == 302
        assert "/assets/files/danielblackburn.pdf" in response.headers[
            "location"
        ]

    async def test_static_file_access(self, async_client: AsyncClient):
        """Test that static files are accessible."""
        response = await async_client.get("/assets/style.css")
        assert response.status_code == 200
        assert "text/css" in response.headers['content-type']


@pytest.mark.unit
class TestAPIEndpoints:
    """Test API data endpoints."""

    @patch('database.database')
    async def test_workitems_endpoint(
        self, mock_db, async_client: AsyncClient
    ):
        """Test the work items API endpoint."""
        # Mock database response
        mock_db.fetch_all.return_value = [
            {
                'id': '550e8400-e29b-41d4-a716-446655440000',
                'portfolio_id': '3fc521ad-660c-4067-b416-17dc388e66eb',
                'company': 'Test Company',
                'position': 'Developer',
                'location': 'Remote',
                'start_date': '2023-01-01',
                'end_date': '2024-01-01',
                'description': 'Test description',
                'is_current': False,
                'company_url': 'https://test.com',
                'sort_order': 1
            }
        ]

        response = await async_client.get("/workitems")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if data:  # Only check if we have data
            assert 'company' in data[0]
            assert 'position' in data[0]

    @patch('database.database')
    async def test_projects_endpoint(self, mock_db, async_client: AsyncClient):
        """Test the projects API endpoint."""
        # Mock database response
        mock_db.fetch_all.return_value = [
            {
                'id': '650e8400-e29b-41d4-a716-446655440000',
                'portfolio_id': '3fc521ad-660c-4067-b416-17dc388e66eb',
                'title': 'Test Project',
                'description': 'Test description',
                'url': 'https://github.com/test/project',
                'image_url': '/assets/test.jpg',
                'technologies': ['Python', 'FastAPI'],
                'sort_order': 1
            }
        ]

        response = await async_client.get("/projects")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_schema_endpoint(self, async_client: AsyncClient):
        """Test the database schema endpoint."""
        with patch('database.database') as mock_db:
            mock_db.fetch_all.side_effect = [
                [{'table_name': 'portfolios'}],
                [{'column_name': 'id', 'data_type': 'uuid'}]
            ]
            mock_db.fetch_val.return_value = 1

            response = await async_client.get("/schema")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, dict)


@pytest.mark.unit
class TestErrorHandling:
    """Test error handling and edge cases."""

    async def test_404_page(self, async_client: AsyncClient):
        """Test that 404 errors are handled gracefully."""
        response = await async_client.get("/nonexistent-page")
        assert response.status_code == 404

    async def test_invalid_work_item_id(self, async_client: AsyncClient):
        """Test handling of invalid work item IDs."""
        response = await async_client.get("/workitems/invalid-id")
        # Should return 404 or proper error handling
        assert response.status_code in [404, 422]

    async def test_invalid_project_id(self, async_client: AsyncClient):
        """Test handling of invalid project IDs."""
        response = await async_client.get("/projects/invalid-id")
        # Should return 404 or proper error handling
        assert response.status_code in [404, 422]


@pytest.mark.integration
class TestShowcaseEndpoints:
    """Test showcase and project detail endpoints."""

    async def test_showcase_project_portfoliosite(
        self, async_client: AsyncClient
    ):
        """Test the portfoliosite showcase page."""
        response = await async_client.get("/showcase/portfoliosite/")
        assert response.status_code == 200
        assert "text/html" in response.headers['content-type']
        assert "portfolioSite" in response.text

    async def test_showcase_project_pypgsvg(self, async_client: AsyncClient):
        """Test the pypgsvg showcase page."""
        response = await async_client.get("/showcase/pypgsvg/")
        assert response.status_code == 200
        assert "text/html" in response.headers['content-type']
        assert "pypgsvg" in response.text

    async def test_showcase_invalid_project(self, async_client: AsyncClient):
        """Test showcase page for non-existent project."""
        response = await async_client.get("/showcase/nonexistent/")
        assert response.status_code == 404


@pytest.mark.unit
class TestContactForm:
    """Test contact form functionality."""

    @patch('app.routers.contact.send_contact_email')
    async def test_contact_form_submission(
        self, mock_send_email, async_client: AsyncClient, sample_contact
    ):
        """Test contact form submission."""
        mock_send_email.return_value = None

        with patch('database.database') as mock_db:
            mock_db.execute.return_value = None

            response = await async_client.post(
                "/contact/submit",
                data=sample_contact
            )
            # Should redirect after successful submission
            assert response.status_code in [302, 200]

    async def test_contact_form_validation(self, async_client: AsyncClient):
        """Test contact form validation with invalid data."""
        invalid_data = {
            "name": "",  # Empty name
            "email": "invalid-email",  # Invalid email
            "subject": "",  # Empty subject
            "message": ""  # Empty message
        }

        response = await async_client.post(
            "/contact/submit",
            data=invalid_data
        )
        # Should handle validation errors gracefully
        assert response.status_code in [400, 422, 200]


@pytest.mark.unit
class TestGraphQLEndpoint:
    """Test GraphQL endpoint functionality."""

    async def test_graphql_endpoint_exists(self, async_client: AsyncClient):
        """Test that GraphQL endpoint is accessible."""
        # Simple introspection query
        query = {"query": "{ __schema { types { name } } }"}

        response = await async_client.post("/graphql", json=query)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data

    async def test_graphql_invalid_query(self, async_client: AsyncClient):
        """Test GraphQL with invalid query."""
        query = {"query": "{ invalidField }"}

        response = await async_client.post("/graphql", json=query)
        # Should return error but still 200 for GraphQL
        assert response.status_code == 200
        data = response.json()
        assert "errors" in data