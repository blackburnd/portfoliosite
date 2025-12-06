"""
Tests for contact submissions admin functionality.
"""
import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
from datetime import datetime
import uuid


@pytest.fixture
def sample_contact_submission():
    """Sample contact submission data for testing."""
    return {
        "id": str(uuid.uuid4()),
        "portfolio_id": str(uuid.uuid4()),
        "name": "John Doe",
        "email": "john.doe@example.com",
        "subject": "Test Inquiry",
        "message": "This is a test message from the contact form.",
        "created_at": datetime.utcnow(),
        "is_read": False
    }


@pytest.fixture
def multiple_contact_submissions():
    """Multiple contact submission records for testing."""
    portfolio_id = str(uuid.uuid4())
    return [
        {
            "id": str(uuid.uuid4()),
            "portfolio_id": portfolio_id,
            "name": "John Doe",
            "email": "john@example.com",
            "subject": "Inquiry about services",
            "message": "I would like to know more about your services.",
            "created_at": datetime.utcnow(),
            "is_read": False
        },
        {
            "id": str(uuid.uuid4()),
            "portfolio_id": portfolio_id,
            "name": "Jane Smith",
            "email": "jane@example.com",
            "subject": "Project collaboration",
            "message": "Interested in collaborating on a project.",
            "created_at": datetime.utcnow(),
            "is_read": True
        },
        {
            "id": str(uuid.uuid4()),
            "portfolio_id": portfolio_id,
            "name": "Bob Johnson",
            "email": "bob@example.com",
            "subject": "Question",
            "message": "Quick question about your work.",
            "created_at": datetime.utcnow(),
            "is_read": False
        }
    ]


@pytest.mark.unit
class TestContactSubmissionsAccess:
    """Test access control for contact submissions admin page."""

    async def test_contact_submissions_page_requires_auth(
        self, async_client: AsyncClient
    ):
        """Test that the contact submissions page requires authentication."""
        response = await async_client.get("/contact-submissions")
        # Should redirect or return 401/403
        assert response.status_code in [401, 403, 307, 302]

    @patch('auth.require_admin_auth')
    async def test_contact_submissions_page_loads_for_admin(
        self, mock_auth, async_client: AsyncClient
    ):
        """Test that the contact submissions page loads for authenticated admin."""
        # Mock admin authentication
        mock_auth.return_value = {
            "email": "admin@blackburnsystems.com",
            "authenticated": True
        }

        response = await async_client.get("/contact-submissions")
        assert response.status_code == 200
        assert "text/html" in response.headers['content-type']
        assert "Contact Submissions" in response.text or "contact-submissions" in response.text


@pytest.mark.unit
class TestContactSubmissionsData:
    """Test contact submissions data endpoint."""

    @patch('auth.require_admin_auth')
    @patch('database.database')
    async def test_data_endpoint_returns_empty_when_no_submissions(
        self, mock_db, mock_auth, async_client: AsyncClient
    ):
        """Test that data endpoint returns empty list when no submissions exist."""
        # Mock admin authentication
        mock_auth.return_value = {
            "email": "admin@blackburnsystems.com",
            "authenticated": True
        }

        # Mock empty database response
        mock_db.fetch_val.return_value = 0  # Total count
        mock_db.fetch_all.return_value = []  # No submissions

        response = await async_client.get("/contact-submissions/data")
        assert response.status_code == 200

        data = response.json()
        assert "submissions" in data
        assert len(data["submissions"]) == 0
        assert data["total_count"] == 0
        assert data["has_more"] is False

    @patch('auth.require_admin_auth')
    @patch('database.database')
    async def test_data_endpoint_returns_submissions(
        self, mock_db, mock_auth, async_client: AsyncClient,
        multiple_contact_submissions
    ):
        """Test that data endpoint returns contact submissions."""
        # Mock admin authentication
        mock_auth.return_value = {
            "email": "admin@blackburnsystems.com",
            "authenticated": True
        }

        # Mock database response
        mock_db.fetch_val.return_value = len(multiple_contact_submissions)
        mock_db.fetch_all.return_value = multiple_contact_submissions

        response = await async_client.get("/contact-submissions/data")
        assert response.status_code == 200

        data = response.json()
        assert "submissions" in data
        assert len(data["submissions"]) == 3
        assert data["total_count"] == 3
        assert data["submissions"][0]["name"] == "John Doe"
        assert data["submissions"][1]["name"] == "Jane Smith"

    @patch('auth.require_admin_auth')
    @patch('database.database')
    async def test_data_endpoint_supports_pagination(
        self, mock_db, mock_auth, async_client: AsyncClient,
        multiple_contact_submissions
    ):
        """Test that data endpoint supports pagination."""
        # Mock admin authentication
        mock_auth.return_value = {
            "email": "admin@blackburnsystems.com",
            "authenticated": True
        }

        # Mock database response with pagination
        mock_db.fetch_val.return_value = 3
        mock_db.fetch_all.return_value = multiple_contact_submissions[:2]

        response = await async_client.get(
            "/contact-submissions/data?offset=0&limit=2"
        )
        assert response.status_code == 200

        data = response.json()
        assert len(data["submissions"]) == 2
        assert data["total_count"] == 3
        assert data["has_more"] is True

    @patch('auth.require_admin_auth')
    @patch('database.database')
    async def test_data_endpoint_supports_search(
        self, mock_db, mock_auth, async_client: AsyncClient,
        multiple_contact_submissions
    ):
        """Test that data endpoint supports search filtering."""
        # Mock admin authentication
        mock_auth.return_value = {
            "email": "admin@blackburnsystems.com",
            "authenticated": True
        }

        # Mock database response with filtered results
        filtered = [s for s in multiple_contact_submissions if "Jane" in s["name"]]
        mock_db.fetch_val.return_value = len(filtered)
        mock_db.fetch_all.return_value = filtered

        response = await async_client.get(
            "/contact-submissions/data?search=Jane"
        )
        assert response.status_code == 200

        data = response.json()
        assert len(data["submissions"]) == 1
        assert data["submissions"][0]["name"] == "Jane Smith"

    @patch('auth.require_admin_auth')
    @patch('database.database')
    async def test_data_endpoint_supports_status_filter(
        self, mock_db, mock_auth, async_client: AsyncClient,
        multiple_contact_submissions
    ):
        """Test that data endpoint supports status filtering."""
        # Mock admin authentication
        mock_auth.return_value = {
            "email": "admin@blackburnsystems.com",
            "authenticated": True
        }

        # Mock database response with unread only
        unread = [s for s in multiple_contact_submissions if not s["is_read"]]
        mock_db.fetch_val.return_value = len(unread)
        mock_db.fetch_all.return_value = unread

        response = await async_client.get(
            "/contact-submissions/data?status=unread"
        )
        assert response.status_code == 200

        data = response.json()
        assert len(data["submissions"]) == 2
        assert all(not s["is_read"] for s in data["submissions"])


@pytest.mark.unit
class TestContactSubmissionsDeletion:
    """Test contact submission deletion functionality."""

    @patch('auth.require_admin_auth')
    @patch('database.database')
    async def test_delete_individual_submission(
        self, mock_db, mock_auth, async_client: AsyncClient,
        sample_contact_submission
    ):
        """Test deleting a single contact submission."""
        # Mock admin authentication
        mock_auth.return_value = {
            "email": "admin@blackburnsystems.com",
            "authenticated": True
        }

        # Mock database response
        mock_db.fetch_one.return_value = sample_contact_submission

        submission_id = sample_contact_submission["id"]
        response = await async_client.delete(
            f"/contact-submissions/delete/{submission_id}"
        )
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "deleted" in data["message"].lower()

    @patch('auth.require_admin_auth')
    @patch('database.database')
    async def test_delete_nonexistent_submission(
        self, mock_db, mock_auth, async_client: AsyncClient
    ):
        """Test deleting a non-existent submission returns 404."""
        # Mock admin authentication
        mock_auth.return_value = {
            "email": "admin@blackburnsystems.com",
            "authenticated": True
        }

        # Mock database response (no result)
        mock_db.fetch_one.return_value = None

        fake_id = str(uuid.uuid4())
        response = await async_client.delete(
            f"/contact-submissions/delete/{fake_id}"
        )
        assert response.status_code == 404

    @patch('auth.require_admin_auth')
    @patch('database.database')
    async def test_clear_all_submissions(
        self, mock_db, mock_auth, async_client: AsyncClient
    ):
        """Test clearing all contact submissions."""
        # Mock admin authentication
        mock_auth.return_value = {
            "email": "admin@blackburnsystems.com",
            "authenticated": True
        }

        # Mock database execute
        mock_db.execute.return_value = None

        response = await async_client.post("/contact-submissions/clear")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "cleared" in data["message"].lower()

        # Verify delete query was called
        mock_db.execute.assert_called_once()


@pytest.mark.unit
class TestContactSubmissionsReadStatus:
    """Test contact submission read/unread status functionality."""

    @patch('auth.require_admin_auth')
    @patch('database.database')
    async def test_mark_submission_as_read(
        self, mock_db, mock_auth, async_client: AsyncClient,
        sample_contact_submission
    ):
        """Test marking a submission as read."""
        # Mock admin authentication
        mock_auth.return_value = {
            "email": "admin@blackburnsystems.com",
            "authenticated": True
        }

        # Mock database response
        sample_contact_submission["is_read"] = True
        mock_db.fetch_one.return_value = sample_contact_submission

        submission_id = sample_contact_submission["id"]
        response = await async_client.post(
            f"/contact-submissions/mark-read/{submission_id}"
        )
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "read" in data["message"].lower()

    @patch('auth.require_admin_auth')
    @patch('database.database')
    async def test_mark_submission_as_unread(
        self, mock_db, mock_auth, async_client: AsyncClient,
        sample_contact_submission
    ):
        """Test marking a submission as unread."""
        # Mock admin authentication
        mock_auth.return_value = {
            "email": "admin@blackburnsystems.com",
            "authenticated": True
        }

        # Mock database response
        sample_contact_submission["is_read"] = False
        mock_db.fetch_one.return_value = sample_contact_submission

        submission_id = sample_contact_submission["id"]
        response = await async_client.post(
            f"/contact-submissions/mark-unread/{submission_id}"
        )
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "unread" in data["message"].lower()

    @patch('auth.require_admin_auth')
    @patch('database.database')
    async def test_mark_nonexistent_submission_read(
        self, mock_db, mock_auth, async_client: AsyncClient
    ):
        """Test marking a non-existent submission as read returns 404."""
        # Mock admin authentication
        mock_auth.return_value = {
            "email": "admin@blackburnsystems.com",
            "authenticated": True
        }

        # Mock database response (no result)
        mock_db.fetch_one.return_value = None

        fake_id = str(uuid.uuid4())
        response = await async_client.post(
            f"/contact-submissions/mark-read/{fake_id}"
        )
        assert response.status_code == 404


@pytest.mark.integration
class TestContactSubmissionsIntegration:
    """Integration tests for contact submissions workflow."""

    @patch('auth.require_admin_auth')
    @patch('database.database')
    async def test_complete_workflow(
        self, mock_db, mock_auth, async_client: AsyncClient,
        sample_contact_submission
    ):
        """Test complete workflow: view, mark read, delete."""
        # Mock admin authentication
        mock_auth.return_value = {
            "email": "admin@blackburnsystems.com",
            "authenticated": True
        }

        submission_id = sample_contact_submission["id"]

        # Step 1: Load submissions
        mock_db.fetch_val.return_value = 1
        mock_db.fetch_all.return_value = [sample_contact_submission]

        response = await async_client.get("/contact-submissions/data")
        assert response.status_code == 200
        data = response.json()
        assert len(data["submissions"]) == 1

        # Step 2: Mark as read
        mock_db.fetch_one.return_value = sample_contact_submission
        response = await async_client.post(
            f"/contact-submissions/mark-read/{submission_id}"
        )
        assert response.status_code == 200

        # Step 3: Delete submission
        mock_db.fetch_one.return_value = sample_contact_submission
        response = await async_client.delete(
            f"/contact-submissions/delete/{submission_id}"
        )
        assert response.status_code == 200

        # Step 4: Verify empty
        mock_db.fetch_val.return_value = 0
        mock_db.fetch_all.return_value = []
        response = await async_client.get("/contact-submissions/data")
        assert response.status_code == 200
        data = response.json()
        assert len(data["submissions"]) == 0
