"""
Tests for database operations and models.
"""
import pytest
import uuid
from unittest.mock import patch
from database import (
    init_database,
    close_database,
    get_portfolio_id,
    add_log,
    database
)


@pytest.mark.database
class TestDatabaseConnection:
    """Test database connection and initialization."""

    @patch('database.database.connect')
    async def test_init_database(self, mock_connect):
        """Test database initialization."""
        mock_connect.return_value = None
        await init_database()
        mock_connect.assert_called_once()

    @patch('database.database.disconnect')
    async def test_close_database(self, mock_disconnect):
        """Test database connection closure."""
        mock_disconnect.return_value = None
        await close_database()
        mock_disconnect.assert_called_once()

    @patch('database.database')
    async def test_get_portfolio_id(self, mock_db):
        """Test portfolio ID retrieval."""
        expected_id = "3fc521ad-660c-4067-b416-17dc388e66eb"
        mock_db.fetch_val.return_value = expected_id
        
        portfolio_id = await get_portfolio_id()
        assert portfolio_id == expected_id


@pytest.mark.database
class TestLoggingDatabase:
    """Test database logging functionality."""

    @patch('database.database')
    async def test_add_log_success(self, mock_db):
        """Test successful log entry addition."""
        mock_db.execute.return_value = None
        
        await add_log(
            level="INFO",
            message="Test log message",
            module="test_module",
            function="test_function",
            request_id="test-request-123"
        )
        
        mock_db.execute.assert_called_once()
        call_args = mock_db.execute.call_args
        assert "INSERT INTO logs" in call_args[0][0]

    @patch('database.database')
    async def test_add_log_with_traceback(self, mock_db):
        """Test log entry with traceback information."""
        mock_db.execute.return_value = None
        
        await add_log(
            level="ERROR",
            message="Test error message",
            module="test_module",
            function="test_function",
            request_id="test-request-123",
            traceback="Test traceback information"
        )
        
        mock_db.execute.assert_called_once()
        call_args = mock_db.execute.call_args
        values = call_args[1]
        assert values["traceback"] == "Test traceback information"

    @patch('database.database')
    async def test_add_log_database_error(self, mock_db):
        """Test log addition when database is unavailable."""
        mock_db.execute.side_effect = Exception("Database connection error")
        
        # Should not raise exception even if database fails
        try:
            await add_log(
                level="INFO",
                message="Test message",
                module="test_module"
            )
        except Exception as e:
            pytest.fail(f"add_log should handle database errors: {e}")


@pytest.mark.database
class TestWorkItemsDatabase:
    """Test work items database operations."""

    @patch('database.database')
    async def test_fetch_work_items(self, mock_db):
        """Test fetching work items from database."""
        mock_work_items = [
            {
                'id': str(uuid.uuid4()),
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
        mock_db.fetch_all.return_value = mock_work_items
        
        # Test the query that would be used in the actual endpoint
        query = """
        SELECT * FROM work_experience
        WHERE portfolio_id = :portfolio_id
        ORDER BY sort_order, start_date DESC
        """
        result = await database.fetch_all(
            query,
            {"portfolio_id": "3fc521ad-660c-4067-b416-17dc388e66eb"}
        )
        
        assert len(result) == 1
        assert result[0]['company'] == 'Test Company'

    @patch('database.database')
    async def test_insert_work_item(self, mock_db):
        """Test inserting new work item."""
        mock_db.execute.return_value = None
        
        work_item_data = {
            'id': str(uuid.uuid4()),
            'portfolio_id': '3fc521ad-660c-4067-b416-17dc388e66eb',
            'company': 'New Company',
            'position': 'Senior Developer',
            'location': 'New York',
            'start_date': '2024-01-01',
            'end_date': None,
            'description': 'New position description',
            'is_current': True,
            'company_url': 'https://newcompany.com',
            'sort_order': 1
        }
        
        await database.execute(
            """
            INSERT INTO work_experience
            (id, portfolio_id, company, position, location, start_date,
             end_date, description, is_current, company_url, sort_order)
            VALUES (:id, :portfolio_id, :company, :position, :location,
                   :start_date, :end_date, :description, :is_current,
                   :company_url, :sort_order)
            """,
            work_item_data
        )
        
        mock_db.execute.assert_called_once()


@pytest.mark.database
class TestProjectsDatabase:
    """Test projects database operations."""

    @patch('database.database')
    async def test_fetch_projects(self, mock_db):
        """Test fetching projects from database."""
        mock_projects = [
            {
                'id': str(uuid.uuid4()),
                'portfolio_id': '3fc521ad-660c-4067-b416-17dc388e66eb',
                'title': 'Test Project',
                'description': 'Test project description',
                'url': 'https://github.com/test/project',
                'image_url': '/assets/test-project.jpg',
                'technologies': ['Python', 'FastAPI', 'PostgreSQL'],
                'sort_order': 1
            }
        ]
        mock_db.fetch_all.return_value = mock_projects
        
        query = """
        SELECT * FROM projects
        WHERE portfolio_id = :portfolio_id
        ORDER BY sort_order
        """
        result = await database.fetch_all(
            query,
            {"portfolio_id": "3fc521ad-660c-4067-b416-17dc388e66eb"}
        )
        
        assert len(result) == 1
        assert result[0]['title'] == 'Test Project'

    @patch('database.database')
    async def test_insert_project(self, mock_db):
        """Test inserting new project."""
        mock_db.execute.return_value = None
        
        project_data = {
            'id': str(uuid.uuid4()),
            'portfolio_id': '3fc521ad-660c-4067-b416-17dc388e66eb',
            'title': 'New Project',
            'description': 'New project description',
            'url': 'https://github.com/test/newproject',
            'image_url': '/assets/new-project.jpg',
            'technologies': ['React', 'TypeScript', 'Node.js'],
            'sort_order': 2
        }
        
        await database.execute(
            """
            INSERT INTO projects
            (id, portfolio_id, title, description, url, image_url,
             technologies, sort_order)
            VALUES (:id, :portfolio_id, :title, :description, :url,
                   :image_url, :technologies, :sort_order)
            """,
            project_data
        )
        
        mock_db.execute.assert_called_once()


@pytest.mark.database
class TestSiteConfigDatabase:
    """Test site configuration database operations."""

    @patch('database.database')
    async def test_fetch_site_config(self, mock_db):
        """Test fetching site configuration."""
        mock_config = [
            {
                'key': 'full_name',
                'value': 'Daniel Blackburn',
                'category': 'personal'
            },
            {
                'key': 'tagline',
                'value': 'Innovation through collaboration',
                'category': 'personal'
            }
        ]
        mock_db.fetch_all.return_value = mock_config
        
        query = """
        SELECT key, value, category FROM site_config
        WHERE portfolio_id = :portfolio_id
        """
        result = await database.fetch_all(
            query,
            {"portfolio_id": "3fc521ad-660c-4067-b416-17dc388e66eb"}
        )
        
        assert len(result) == 2
        config_dict = {item['key']: item['value'] for item in result}
        assert config_dict['full_name'] == 'Daniel Blackburn'

    @patch('database.database')
    async def test_update_site_config(self, mock_db):
        """Test updating site configuration."""
        mock_db.execute.return_value = None
        
        config_data = {
            'portfolio_id': '3fc521ad-660c-4067-b416-17dc388e66eb',
            'key': 'tagline',
            'value': 'Updated tagline',
            'category': 'personal'
        }
        
        await database.execute(
            """
            INSERT INTO site_config (portfolio_id, key, value, category)
            VALUES (:portfolio_id, :key, :value, :category)
            ON CONFLICT (portfolio_id, key)
            DO UPDATE SET value = EXCLUDED.value
            """,
            config_data
        )
        
        mock_db.execute.assert_called_once()


@pytest.mark.database
class TestAnalyticsDatabase:
    """Test analytics database operations."""

    @patch('database.database')
    async def test_record_page_view(self, mock_db):
        """Test recording page view analytics."""
        mock_db.execute.return_value = None
        
        analytics_data = {
            'page_path': '/',
            'user_agent': 'Test Browser',
            'ip_address': '127.0.0.1',
            'referer': 'https://google.com',
            'timestamp': '2024-01-01 12:00:00'
        }
        
        await database.execute(
            """
            INSERT INTO analytics
            (page_path, user_agent, ip_address, referer, timestamp)
            VALUES (:page_path, :user_agent, :ip_address,
                   :referer, :timestamp)
            """,
            analytics_data
        )
        
        mock_db.execute.assert_called_once()

    @patch('database.database')
    async def test_fetch_analytics_summary(self, mock_db):
        """Test fetching analytics summary."""
        mock_analytics = [
            {'page_path': '/', 'view_count': 100},
            {'page_path': '/contact/', 'view_count': 50},
            {'page_path': '/work/', 'view_count': 75}
        ]
        mock_db.fetch_all.return_value = mock_analytics
        
        query = """
        SELECT page_path, COUNT(*) as view_count
        FROM analytics
        GROUP BY page_path
        ORDER BY view_count DESC
        """
        result = await database.fetch_all(query)
        
        assert len(result) == 3
        assert result[0]['view_count'] == 100


@pytest.mark.unit
class TestDatabaseUtilities:
    """Test database utility functions."""

    def test_uuid_string_conversion(self):
        """Test UUID to string conversion for API responses."""
        test_uuid = uuid.uuid4()
        uuid_str = str(test_uuid)
        
        # Test that conversion works both ways
        assert len(uuid_str) == 36
        assert uuid.UUID(uuid_str) == test_uuid

    def test_json_serialization(self):
        """Test JSON serialization for technologies field."""
        import json
        
        technologies = ["Python", "FastAPI", "PostgreSQL"]
        json_str = json.dumps(technologies)
        
        # Test round-trip serialization
        parsed = json.loads(json_str)
        assert parsed == technologies
        assert isinstance(parsed, list)