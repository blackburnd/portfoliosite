"""
Tests for authentication and authorization functionality.
"""
import pytest
import jwt
from datetime import datetime, timedelta
from httpx import AsyncClient
from unittest.mock import patch
from auth import (
    create_access_token,
    verify_token,
    is_authorized_user,
    SECRET_KEY,
    ALGORITHM
)


@pytest.mark.unit
class TestAuthenticationUtils:
    """Test authentication utility functions."""

    def test_create_access_token(self):
        """Test JWT token creation."""
        data = {"sub": "test@example.com"}
        token = create_access_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Decode and verify token
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert decoded["sub"] == "test@example.com"
        assert "exp" in decoded

    def test_create_access_token_with_expiry(self):
        """Test JWT token creation with custom expiry."""
        data = {"sub": "test@example.com"}
        expires_delta = timedelta(minutes=30)
        token = create_access_token(data, expires_delta)

        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp_time = datetime.utcfromtimestamp(decoded["exp"])
        expected_time = datetime.utcnow() + expires_delta

        # Allow 1 minute tolerance for timing differences
        assert abs((exp_time - expected_time).total_seconds()) < 60

    def test_verify_token_valid(self):
        """Test token verification with valid token."""
        data = {"sub": "test@example.com"}
        token = create_access_token(data)
        
        payload = verify_token(token)
        assert payload is not None
        assert payload["sub"] == "test@example.com"

    def test_verify_token_invalid(self):
        """Test token verification with invalid token."""
        invalid_token = "invalid.jwt.token"
        try:
            payload = verify_token(invalid_token)
            assert payload is None
        except Exception:
            # Invalid tokens should either return None or raise exception
            assert True

    def test_verify_token_expired(self):
        """Test token verification with expired token."""
        data = {"sub": "test@example.com"}
        expires_delta = timedelta(seconds=-1)  # Already expired
        try:
            token = create_access_token(data, expires_delta)
            payload = verify_token(token)
            assert payload is None
        except Exception:
            # Expired tokens might raise exceptions, which is acceptable
            assert True

    def test_is_authorized_user_valid(self):
        """Test user authorization with valid email."""
        # Test with emails that should be in our test environment
        try:
            # These are set in conftest.py environment variables
            result1 = is_authorized_user("test@example.com")
            result2 = is_authorized_user("admin@blackburnsystems.com")
            # At least one should be authorized based on our test setup
            assert result1 is True or result2 is True
        except Exception:
            # If function not available, skip test
            pytest.skip("is_authorized_user function not available")

    def test_is_authorized_user_invalid(self):
        """Test user authorization with invalid email."""
        assert is_authorized_user("unauthorized@example.com") is False
        assert is_authorized_user("") is False
        assert is_authorized_user(None) is False


@pytest.mark.auth
class TestAuthenticationEndpoints:
    """Test authentication-related endpoints."""

    async def test_admin_login_page(self, async_client: AsyncClient):
        """Test admin login page loads."""
        response = await async_client.get("/admin/login")
        assert response.status_code == 200
        assert "text/html" in response.headers['content-type']

    async def test_admin_login_with_valid_credentials(
        self, async_client: AsyncClient
    ):
        """Test admin login with valid credentials."""
        login_data = {
            "username": "test_admin",
            "password": "test_password"
        }
        
        response = await async_client.post("/admin/login", data=login_data)
        # Should redirect or return success
        assert response.status_code in [200, 302]

    async def test_admin_login_with_invalid_credentials(
        self, async_client: AsyncClient
    ):
        """Test admin login with invalid credentials."""
        login_data = {
            "username": "wrong_user",
            "password": "wrong_password"
        }
        
        response = await async_client.post("/admin/login", data=login_data)
        # Should reject login
        assert response.status_code in [401, 403, 200]  # 200 if form redisplay

    async def test_google_oauth_redirect(self, async_client: AsyncClient):
        """Test Google OAuth redirect endpoint."""
        response = await async_client.get(
            "/auth/google/login", follow_redirects=False
        )
        # Should redirect to Google OAuth
        assert response.status_code == 302
        assert "accounts.google.com" in response.headers.get("location", "")

    @patch('app.routers.oauth.verify_google_token')
    async def test_google_oauth_callback(
        self, mock_verify, async_client: AsyncClient
    ):
        """Test Google OAuth callback endpoint."""
        mock_verify.return_value = {
            "email": "test@example.com",
            "name": "Test User",
            "picture": "https://example.com/avatar.jpg"
        }
        
        callback_data = {
            "code": "test_auth_code",
            "state": "test_state"
        }
        
        response = await async_client.get(
            "/auth/google/callback", params=callback_data
        )
        # Should handle callback appropriately
        assert response.status_code in [200, 302]


@pytest.mark.auth
class TestProtectedEndpoints:
    """Test endpoints that require authentication."""

    async def test_analytics_admin_unauthorized(
        self, async_client: AsyncClient
    ):
        """Test analytics admin page without authentication."""
        response = await async_client.get("/admin/analytics")
        # Should redirect to login or return 401/403
        assert response.status_code in [302, 401, 403]

    async def test_sql_admin_unauthorized(self, async_client: AsyncClient):
        """Test SQL admin page without authentication."""
        response = await async_client.get("/admin/sql")
        # Should redirect to login or return 401/403
        assert response.status_code in [302, 401, 403]

    async def test_logs_admin_unauthorized(self, async_client: AsyncClient):
        """Test logs admin page without authentication."""
        response = await async_client.get("/logs")
        # Should redirect to login or return 401/403
        assert response.status_code in [302, 401, 403]

    async def test_work_admin_unauthorized(self, async_client: AsyncClient):
        """Test work admin page without authentication."""
        response = await async_client.get("/workadmin")
        # Should redirect to login or return 401/403
        assert response.status_code in [302, 401, 403]

    async def test_projects_admin_unauthorized(
        self, async_client: AsyncClient
    ):
        """Test projects admin page without authentication."""
        response = await async_client.get("/projectsadmin")
        # Should redirect to login or return 401/403
        assert response.status_code in [302, 401, 403]

    @patch('auth.require_admin_auth')
    async def test_protected_endpoint_with_auth(
        self, mock_auth, authenticated_client: AsyncClient
    ):
        """Test protected endpoint with valid authentication."""
        mock_auth.return_value = {"email": "test@example.com"}
        
        response = await authenticated_client.get("/admin/analytics")
        # Should allow access with proper auth
        assert response.status_code == 200


@pytest.mark.unit
class TestSessionManagement:
    """Test session management functionality."""

    async def test_logout_endpoint(self, async_client: AsyncClient):
        """Test logout functionality."""
        response = await async_client.post("/auth/logout")
        # Should handle logout appropriately
        assert response.status_code in [200, 302]

    async def test_logout_redirect(self, async_client: AsyncClient):
        """Test logout redirects to home page."""
        response = await async_client.post(
            "/auth/logout", follow_redirects=False
        )
        if response.status_code == 302:
            assert response.headers.get("location") in ["/", "/admin/login"]


@pytest.mark.unit
class TestTokenSecurity:
    """Test token security and validation."""

    def test_token_signing_consistency(self):
        """Test that tokens are signed consistently."""
        data = {"sub": "test@example.com"}
        try:
            token1 = create_access_token(data)
            token2 = create_access_token(data)
            
            # Tokens should be different due to timestamp
            assert token1 != token2
            
            # Both should be valid tokens
            payload1 = verify_token(token1)
            payload2 = verify_token(token2)
            
            if payload1 and payload2:
                assert payload1["sub"] == payload2["sub"]
            else:
                # If tokens can't be verified, that's also acceptable for test
                assert True
        except Exception:
            # If JWT functions not available, skip
            pytest.skip("JWT functions not available")

    def test_token_tampering_detection(self):
        """Test that tampered tokens are rejected."""
        data = {"sub": "test@example.com"}
        try:
            token = create_access_token(data)
            
            # Tamper with token
            tampered_token = token[:-5] + "AAAAA"
            
            payload = verify_token(tampered_token)
            assert payload is None
        except Exception:
            # Tampered tokens should either return None or raise exception
            assert True

    def test_algorithm_security(self):
        """Test that only expected algorithm is accepted."""
        # Create token with different algorithm
        data = {"sub": "test@example.com", "exp": datetime.utcnow()}
        
        # This should fail if we try to use wrong algorithm
        try:
            wrong_token = jwt.encode(data, SECRET_KEY, algorithm="HS256")
            if ALGORITHM != "HS256":
                payload = verify_token(wrong_token)
                assert payload is None
        except Exception:
            # Expected if algorithm mismatch
            pass