import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import Mock, patch, MagicMock
from httpx import AsyncClient

# Set a dummy DATABASE_URL before importing to avoid import-time errors
os.environ['DATABASE_URL'] = 'postgresql://test:test@localhost/test'

from main import app
from linkedin_sync import LinkedInSync, LinkedInSyncError

# Clear startup/shutdown events to prevent database connection attempts
app.dependency_overrides = {}
app.router.startup_event_handlers = []
app.router.shutdown_event_handlers = []


class TestLinkedInSync:
    """Test cases for LinkedIn synchronization functionality"""
    
    def setup_method(self):
        """Set up test environment for each test"""
        self.linkedin_sync = LinkedInSync()
    
    def test_linkedin_sync_init(self):
        """Test LinkedIn sync initialization"""
        assert self.linkedin_sync.portfolio_id == "daniel-blackburn"
        assert hasattr(self.linkedin_sync, 'linkedin_username')
        assert hasattr(self.linkedin_sync, 'linkedin_password')
        assert hasattr(self.linkedin_sync, 'target_profile_id')
    
    def test_get_sync_status(self):
        """Test getting sync configuration status"""
        status = self.linkedin_sync.get_sync_status()
        
        assert 'linkedin_configured' in status
        assert 'target_profile_id' in status
        assert 'portfolio_id' in status
        assert status['portfolio_id'] == "daniel-blackburn"
    
    @patch.dict(os.environ, {'LINKEDIN_USERNAME': '', 'LINKEDIN_PASSWORD': ''})
    def test_linkedin_client_no_credentials(self):
        """Test LinkedIn client creation without credentials"""
        sync = LinkedInSync()
        
        with pytest.raises(LinkedInSyncError) as exc_info:
            sync._get_linkedin_client()
        
        assert "LinkedIn credentials not configured" in str(exc_info.value)
    
    @patch.dict(os.environ, {
        'LINKEDIN_USERNAME': 'test@example.com', 
        'LINKEDIN_PASSWORD': 'testpass'
    })
    @patch('linkedin_sync.Linkedin')
    def test_linkedin_client_with_credentials(self, mock_linkedin):
        """Test LinkedIn client creation with credentials"""
        sync = LinkedInSync()
        mock_client = Mock()
        mock_linkedin.return_value = mock_client
        
        client = sync._get_linkedin_client()
        
        assert client == mock_client
        mock_linkedin.assert_called_once_with('test@example.com', 'testpass')
    
    @patch.dict(os.environ, {
        'LINKEDIN_USERNAME': 'test@example.com', 
        'LINKEDIN_PASSWORD': 'testpass'
    })
    @patch('linkedin_sync.Linkedin')
    def test_fetch_profile_data_success(self, mock_linkedin):
        """Test successful profile data fetching"""
        sync = LinkedInSync()
        mock_client = Mock()
        mock_linkedin.return_value = mock_client
        
        mock_profile = {
            'firstName': 'John',
            'lastName': 'Doe', 
            'headline': 'Software Engineer',
            'summary': 'Experienced developer',
            'locationName': 'San Francisco, CA'
        }
        mock_client.get_profile.return_value = mock_profile
        
        result = sync.fetch_profile_data()
        
        assert result == mock_profile
        mock_client.get_profile.assert_called_once_with(sync.target_profile_id)
    
    @patch.dict(os.environ, {
        'LINKEDIN_USERNAME': 'test@example.com', 
        'LINKEDIN_PASSWORD': 'testpass'
    })
    @patch('linkedin_sync.Linkedin')
    def test_fetch_experience_data_success(self, mock_linkedin):
        """Test successful experience data fetching"""
        sync = LinkedInSync()
        mock_client = Mock()
        mock_linkedin.return_value = mock_client
        
        mock_experiences = [
            {
                'companyName': 'Tech Corp',
                'title': 'Senior Developer',
                'description': 'Building amazing software',
                'locationName': 'San Francisco, CA',
                'timePeriod': {
                    'startDate': {'year': 2020, 'month': 1},
                    'endDate': {'year': 2023, 'month': 12}
                }
            }
        ]
        mock_client.get_profile_experiences.return_value = mock_experiences
        
        result = sync.fetch_experience_data()
        
        assert result == mock_experiences
        mock_client.get_profile_experiences.assert_called_once_with(sync.target_profile_id)
    
    def test_map_profile_data(self):
        """Test mapping LinkedIn profile data to portfolio schema"""
        sync = LinkedInSync()
        
        linkedin_profile = {
            'firstName': 'John',
            'lastName': 'Doe',
            'headline': 'Software Engineer at Tech Corp',
            'summary': 'Experienced software developer with 5+ years experience.',
            'locationName': 'San Francisco, CA'
        }
        
        mapped = sync._map_profile_data(linkedin_profile)
        
        assert mapped['name'] == 'John Doe'
        assert mapped['title'] == 'Software Engineer at Tech Corp'
        assert mapped['bio'] == 'Experienced software developer with 5+ years experience.'
        assert mapped['tagline'] == 'Software Engineer at Tech Corp'
        assert mapped['location'] == 'San Francisco, CA'
    
    def test_map_experience_data(self):
        """Test mapping LinkedIn experience data to work_experience schema"""
        sync = LinkedInSync()
        
        linkedin_experiences = [
            {
                'companyName': 'Tech Corp',
                'title': 'Senior Developer',
                'description': 'Building scalable web applications',
                'locationName': 'San Francisco, CA',
                'timePeriod': {
                    'startDate': {'year': 2020, 'month': 1},
                    'endDate': {'year': 2023, 'month': 12}
                }
            },
            {
                'companyName': 'StartupXYZ',
                'title': 'Lead Engineer',
                'description': 'Leading development team',
                'locationName': 'Remote',
                'timePeriod': {
                    'startDate': {'year': 2023, 'month': 12}
                    # No endDate - current position
                }
            }
        ]
        
        mapped = sync._map_experience_data(linkedin_experiences)
        
        assert len(mapped) == 2
        
        # First experience (completed)
        exp1 = mapped[0]
        assert exp1['company'] == 'Tech Corp'
        assert exp1['position'] == 'Senior Developer'
        assert exp1['location'] == 'San Francisco, CA'
        assert exp1['start_date'] == '2020-01'
        assert exp1['end_date'] == '2023-12'
        assert exp1['is_current'] == False
        assert exp1['sort_order'] == 1
        
        # Second experience (current)
        exp2 = mapped[1]
        assert exp2['company'] == 'StartupXYZ'
        assert exp2['position'] == 'Lead Engineer'
        assert exp2['location'] == 'Remote'
        assert exp2['start_date'] == '2023-12'
        assert exp2['end_date'] is None
        assert exp2['is_current'] == True
        assert exp2['sort_order'] == 2


class TestLinkedInSyncEndpoints:
    """Test cases for LinkedIn sync API endpoints"""
    
    @pytest.mark.asyncio
    async def test_linkedin_status_endpoint_unauthorized(self):
        """Test LinkedIn status endpoint without authentication"""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get("/linkedin/status")
        
        # Should require authentication
        assert response.status_code in [401, 403, 422]  # Various auth failure codes
    
    @pytest.mark.asyncio
    async def test_linkedin_sync_profile_unauthorized(self):
        """Test LinkedIn profile sync endpoint without authentication"""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post("/linkedin/sync/profile")
        
        # Should require authentication
        assert response.status_code in [401, 403, 422]
    
    @pytest.mark.asyncio
    async def test_linkedin_sync_experience_unauthorized(self):
        """Test LinkedIn experience sync endpoint without authentication"""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post("/linkedin/sync/experience")
        
        # Should require authentication
        assert response.status_code in [401, 403, 422]
    
    @pytest.mark.asyncio
    async def test_linkedin_sync_full_unauthorized(self):
        """Test LinkedIn full sync endpoint without authentication"""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post("/linkedin/sync/full")
        
        # Should require authentication
        assert response.status_code in [401, 403, 422]
    
    @pytest.mark.asyncio
    async def test_linkedin_admin_page_unauthorized(self):
        """Test LinkedIn admin page without authentication"""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get("/linkedin")
        
        # Should require authentication
        assert response.status_code in [401, 403, 422]


class TestLinkedInSyncIntegration:
    """Integration tests for LinkedIn sync functionality"""
    
    @patch('linkedin_sync.database')
    @patch.dict(os.environ, {
        'LINKEDIN_USERNAME': 'test@example.com', 
        'LINKEDIN_PASSWORD': 'testpass'
    })
    @patch('linkedin_sync.Linkedin')
    @pytest.mark.asyncio
    async def test_sync_profile_data_integration(self, mock_linkedin, mock_database):
        """Test full profile sync integration"""
        sync = LinkedInSync()
        
        # Mock LinkedIn API
        mock_client = Mock()
        mock_linkedin.return_value = mock_client
        mock_client.get_profile.return_value = {
            'firstName': 'John',
            'lastName': 'Doe',
            'headline': 'Software Engineer',
            'summary': 'Experienced developer'
        }
        
        # Mock database with async mock
        from unittest.mock import AsyncMock
        mock_database.fetch_one = AsyncMock()
        mock_database.fetch_one.return_value = {
            'id': 'daniel-blackburn',
            'name': 'John Doe',
            'title': 'Software Engineer',
            'bio': 'Experienced developer',
            'tagline': 'Software Engineer'
        }
        
        result = await sync.sync_profile_data()
        
        assert result['status'] == 'success'
        assert 'updated_fields' in result
        assert 'profile_data' in result
        mock_database.fetch_one.assert_called_once()
    
    @patch('linkedin_sync.database')
    @patch.dict(os.environ, {
        'LINKEDIN_USERNAME': 'test@example.com', 
        'LINKEDIN_PASSWORD': 'testpass'
    })
    @patch('linkedin_sync.Linkedin')
    @pytest.mark.asyncio
    async def test_sync_experience_data_integration(self, mock_linkedin, mock_database):
        """Test full experience sync integration"""
        sync = LinkedInSync()
        
        # Mock LinkedIn API
        mock_client = Mock()
        mock_linkedin.return_value = mock_client
        mock_client.get_profile_experiences.return_value = [
            {
                'companyName': 'Tech Corp',
                'title': 'Developer',
                'description': 'Building software',
                'timePeriod': {
                    'startDate': {'year': 2020, 'month': 1}
                }
            }
        ]
        
        # Mock database operations with async mocks
        from unittest.mock import AsyncMock
        mock_database.execute = AsyncMock()  # For DELETE
        mock_database.fetch_one = AsyncMock()  # For INSERT
        mock_database.fetch_one.return_value = {
            'id': 'some-uuid',
            'portfolio_id': 'daniel-blackburn',
            'company': 'Tech Corp',
            'position': 'Developer'
        }
        
        result = await sync.sync_experience_data()
        
        assert result['status'] == 'success'
        assert 'experiences_count' in result
        assert result['experiences_count'] == 1
        mock_database.execute.assert_called_once()  # DELETE called
        mock_database.fetch_one.assert_called_once()  # INSERT called