"""
Tests for site configuration management.
"""
import pytest
from unittest.mock import patch
from site_config import SiteConfig


@pytest.mark.unit
class TestSiteConfigClass:
    """Test the SiteConfig class functionality."""

    def test_init_empty_config(self):
        """Test initialization with empty configuration."""
        config = SiteConfig({})
        assert config.data == {}

    def test_init_with_data(self):
        """Test initialization with configuration data."""
        test_data = {'full_name': 'Test User', 'tagline': 'Test Tagline'}
        config = SiteConfig(test_data)
        assert config.data == test_data

    def test_get_existing_key(self):
        """Test getting an existing configuration value."""
        test_data = {'full_name': 'Test User'}
        config = SiteConfig(test_data)
        assert config.get('full_name') == 'Test User'

    def test_get_missing_key_with_default(self):
        """Test getting a missing key with default value."""
        config = SiteConfig({})
        assert config.get('missing_key', 'default') == 'default'

    def test_get_missing_key_without_default(self):
        """Test getting a missing key without default."""
        config = SiteConfig({})
        assert config.get('missing_key') is None

    def test_set_value(self):
        """Test setting a configuration value."""
        config = SiteConfig({})
        config.set('test_key', 'test_value')
        assert config.get('test_key') == 'test_value'

    def test_update_existing_value(self):
        """Test updating an existing configuration value."""
        config = SiteConfig({'existing_key': 'old_value'})
        config.set('existing_key', 'new_value')
        assert config.get('existing_key') == 'new_value'

    def test_to_dict(self):
        """Test converting config to dictionary."""
        test_data = {'key1': 'value1', 'key2': 'value2'}
        config = SiteConfig(test_data)
        assert config.to_dict() == test_data

    def test_contains_method(self):
        """Test the __contains__ method."""
        config = SiteConfig({'existing_key': 'value'})
        assert 'existing_key' in config
        assert 'missing_key' not in config

    def test_iteration(self):
        """Test iterating over configuration keys."""
        test_data = {'key1': 'value1', 'key2': 'value2'}
        config = SiteConfig(test_data)
        keys = list(config)
        assert sorted(keys) == sorted(test_data.keys())


@pytest.mark.database
class TestSiteConfigDatabase:
    """Test site configuration database operations."""

    @patch('site_config.database')
    async def test_load_from_database(self, mock_db):
        """Test loading configuration from database."""
        mock_config_data = [
            {'key': 'full_name', 'value': 'Test User', 'category': 'personal'},
            {'key': 'tagline', 'value': 'Test Tagline', 'category': 'personal'}
        ]
        mock_db.fetch_all.return_value = mock_config_data

        # Import function that would load config from database
        from site_config import load_site_config
        config = await load_site_config('test-portfolio-id')

        assert config.get('full_name') == 'Test User'
        assert config.get('tagline') == 'Test Tagline'

    @patch('site_config.database')
    async def test_save_to_database(self, mock_db):
        """Test saving configuration to database."""
        mock_db.execute.return_value = None

        from site_config import save_site_config
        config = SiteConfig({'full_name': 'Updated User'})
        await save_site_config('test-portfolio-id', config)

        mock_db.execute.assert_called()

    @patch('site_config.database')
    async def test_load_empty_database(self, mock_db):
        """Test loading from empty database."""
        mock_db.fetch_all.return_value = []

        from site_config import load_site_config
        config = await load_site_config('test-portfolio-id')

        assert config.data == {}

    @patch('site_config.database')
    async def test_database_error_handling(self, mock_db):
        """Test handling database errors gracefully."""
        mock_db.fetch_all.side_effect = Exception("Database error")

        from site_config import load_site_config
        try:
            config = await load_site_config('test-portfolio-id')
            # Should return empty config on error
            assert config.data == {}
        except Exception:
            pytest.fail("Should handle database errors gracefully")


@pytest.mark.unit
class TestSiteConfigValidation:
    """Test site configuration validation."""

    def test_validate_personal_info(self):
        """Test validation of personal information fields."""
        config = SiteConfig({
            'full_name': 'Test User',
            'email': 'test@example.com',
            'phone': '+1234567890',
            'location': 'Test City'
        })

        # Check required personal fields
        assert config.get('full_name') is not None
        assert '@' in config.get('email', '')

    def test_validate_social_links(self):
        """Test validation of social media links."""
        config = SiteConfig({
            'linkedin_url': 'https://linkedin.com/in/testuser',
            'github_url': 'https://github.com/testuser',
            'twitter_url': 'https://twitter.com/testuser'
        })

        # Check social links are valid URLs
        linkedin = config.get('linkedin_url', '')
        github = config.get('github_url', '')
        assert linkedin.startswith('https://')
        assert github.startswith('https://')

    def test_validate_professional_info(self):
        """Test validation of professional information."""
        config = SiteConfig({
            'current_position': 'Software Engineer',
            'current_company': 'Test Company',
            'tagline': 'Building great software',
            'bio': 'Experienced developer...'
        })

        # Check professional fields
        assert len(config.get('tagline', '')) > 0
        assert len(config.get('bio', '')) > 0

    def test_validate_contact_settings(self):
        """Test validation of contact form settings."""
        config = SiteConfig({
            'contact_email': 'contact@example.com',
            'contact_form_enabled': True,
            'resume_url': 'https://example.com/resume.pdf'
        })

        # Check contact settings
        contact_email = config.get('contact_email', '')
        assert '@' in contact_email
        assert isinstance(config.get('contact_form_enabled'), bool)


@pytest.mark.unit
class TestSiteConfigCategories:
    """Test site configuration category management."""

    def test_personal_category(self):
        """Test personal information category."""
        config = SiteConfig({
            'full_name': 'Test User',
            'email': 'test@example.com',
            'phone': '+1234567890'
        })

        # Test personal info exists
        personal_fields = ['full_name', 'email', 'phone']
        for field in personal_fields:
            assert config.get(field) is not None

    def test_professional_category(self):
        """Test professional information category."""
        config = SiteConfig({
            'current_position': 'Developer',
            'current_company': 'Test Corp',
            'years_experience': '5'
        })

        # Test professional info exists
        professional_fields = ['current_position', 'current_company']
        for field in professional_fields:
            assert config.get(field) is not None

    def test_social_category(self):
        """Test social media links category."""
        config = SiteConfig({
            'linkedin_url': 'https://linkedin.com/in/test',
            'github_url': 'https://github.com/test',
            'portfolio_url': 'https://test.com'
        })

        # Test social links exist
        social_fields = ['linkedin_url', 'github_url', 'portfolio_url']
        for field in social_fields:
            url = config.get(field)
            assert url is not None
            assert url.startswith('https://')

    def test_mixed_categories(self):
        """Test configuration with mixed categories."""
        config = SiteConfig({
            'full_name': 'Test User',  # personal
            'current_position': 'Developer',  # professional
            'github_url': 'https://github.com/test',  # social
            'contact_form_enabled': True  # settings
        })

        # Test all categories represented
        assert config.get('full_name') is not None
        assert config.get('current_position') is not None
        assert config.get('github_url') is not None
        assert config.get('contact_form_enabled') is not None


@pytest.mark.integration
class TestSiteConfigIntegration:
    """Test site configuration integration scenarios."""

    @patch('site_config.database')
    async def test_full_config_lifecycle(self, mock_db):
        """Test complete configuration lifecycle."""
        # Mock database responses
        mock_db.fetch_all.return_value = [
            {'key': 'full_name', 'value': 'Test User', 'category': 'personal'}
        ]
        mock_db.execute.return_value = None

        from site_config import load_site_config, save_site_config

        # Load existing config
        config = await load_site_config('test-portfolio-id')
        assert config.get('full_name') == 'Test User'

        # Update config
        config.set('tagline', 'New tagline')
        await save_site_config('test-portfolio-id', config)

        # Verify save was called
        mock_db.execute.assert_called()

    @patch('site_config.database')
    async def test_config_migration(self, mock_db):
        """Test configuration migration scenarios."""
        # Mock old format data
        mock_db.fetch_all.return_value = [
            {'key': 'name', 'value': 'Old Name', 'category': 'personal'},
            {'key': 'title', 'value': 'Old Title', 'category': 'professional'}
        ]

        from site_config import load_site_config
        config = await load_site_config('test-portfolio-id')

        # Test that old keys can be accessed
        assert config.get('name') == 'Old Name'
        assert config.get('title') == 'Old Title'

    @patch('site_config.database')
    async def test_config_defaults(self, mock_db):
        """Test configuration with default values."""
        mock_db.fetch_all.return_value = []

        from site_config import load_site_config
        config = await load_site_config('test-portfolio-id')

        # Test default values
        assert config.get('contact_form_enabled', True) is True
        assert config.get('analytics_enabled', True) is True
        assert config.get('theme', 'default') == 'default'