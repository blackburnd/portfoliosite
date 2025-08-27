#!/usr/bin/env python3
"""
Simple test script to verify GraphQL FastAPI setup
"""
import asyncio
import json
from typing import Dict, Any
import sys
import os

# Mock database responses for testing without actual DB connection
class MockPortfolioDatabase:
    @staticmethod
    async def get_portfolio(portfolio_id: str = "daniel-blackburn") -> Dict[str, Any]:
        """Mock portfolio data"""
        return {
            'id': portfolio_id,
            'name': 'Daniel Blackburn',
            'title': 'Software Developer & Cloud Engineer',
            'bio': 'Passionate software developer with expertise in cloud technologies.',
            'tagline': 'Building innovative solutions with modern technology',
            'profile_image': '/assets/img/daniel-blackburn.jpg',
            'email': 'daniel@blackburn.dev',
            'phone': '555-123-4567',
            'vcard': 'Daniel Blackburn.vcf',
            'resume_url': 'linkedin.com/in/danielblackburn',
            'resume_download': 'danielblackburn-resume.pdf',
            'github': '@blackburnd',
            'twitter': '@danielblackburn',
            'skills': '["Python", "FastAPI", "GraphQL", "PostgreSQL", "CI/CD"]',
            'created_at': '2023-01-01T00:00:00',
            'updated_at': '2023-12-01T00:00:00',
            'work_experience': [
                {
                    'id': '123e4567-e89b-12d3-a456-426614174000',
                    'company': 'Test Company',
                    'position': 'Software Engineer',
                    'location': 'Remote',
                    'start_date': '2023',
                    'end_date': None,
                    'description': 'Building innovative solutions',
                    'is_current': True,
                    'company_url': 'https://testcompany.com'
                }
            ],
            'projects': [
                {
                    'id': '456e7890-e89b-12d3-a456-426614174001',
                    'title': 'Cloud Machine Project',
                    'description': 'Automated cloud infrastructure',
                    'url': 'https://github.com/blackburnd/cloud_machine_repo',
                    'image_url': None,
                    'technologies': '["Python", "FastAPI", "GraphQL"]'
                }
            ]
        }
    
    @staticmethod
    async def get_messages(portfolio_id: str = "daniel-blackburn"):
        """Mock messages"""
        return []
    
    @staticmethod
    async def update_portfolio(portfolio_id: str, updates: Dict[str, Any]):
        """Mock update"""
        portfolio = await MockPortfolioDatabase.get_portfolio(portfolio_id)
        portfolio.update(updates)
        return portfolio
    
    @staticmethod
    async def add_work_experience(portfolio_id: str, work_data: Dict[str, Any]):
        """Mock add work experience"""
        return {
            'id': '789e0123-e89b-12d3-a456-426614174002',
            **work_data
        }
    
    @staticmethod
    async def add_project(portfolio_id: str, project_data: Dict[str, Any]):
        """Mock add project"""
        return {
            'id': '012e3456-e89b-12d3-a456-426614174003',
            **project_data
        }
    
    @staticmethod
    async def save_message(portfolio_id: str, message_data: Dict[str, Any]):
        """Mock save message"""
        from datetime import datetime
        return {
            'id': '345e6789-e89b-12d3-a456-426614174004',
            'created_at': datetime.now(),
            'is_read': False,
            **message_data
        }


async def test_graphql_resolvers():
    """Test GraphQL resolvers without database connection"""
    print("Testing GraphQL FastAPI setup...")
    
    # Monkey patch the database class for testing
    import resolvers
    original_db = resolvers.PortfolioDatabase
    resolvers.PortfolioDatabase = MockPortfolioDatabase
    
    try:
        # Test the Query resolvers
        query = resolvers.Query()
        
        print("✓ Testing portfolio query...")
        portfolio = await query.portfolio()
        assert portfolio is not None
        assert portfolio.name == "Daniel Blackburn"
        assert len(portfolio.skills) > 0
        print(f"  Portfolio: {portfolio.name} - {portfolio.title}")
        
        print("✓ Testing work experience query...")
        work_exp = await query.work_experience()
        assert len(work_exp) > 0
        print(f"  Work Experience: {len(work_exp)} entries")
        
        print("✓ Testing projects query...")
        projects = await query.projects()
        assert len(projects) > 0
        print(f"  Projects: {len(projects)} entries")
        
        print("✓ Testing messages query...")
        messages = await query.messages()
        assert isinstance(messages, list)
        print(f"  Messages: {len(messages)} entries")
        
        # Test the Mutation resolvers
        mutation = resolvers.Mutation()
        
        print("✓ Testing update portfolio mutation...")
        from resolvers import PortfolioUpdateInput
        update_input = PortfolioUpdateInput(name="Daniel Test", title="Test Engineer")
        updated = await mutation.update_portfolio("daniel-blackburn", update_input)
        assert updated.name == "Daniel Test"
        print(f"  Updated portfolio name to: {updated.name}")
        
        print("✓ Testing add work experience mutation...")
        from resolvers import WorkExperienceInput
        work_input = WorkExperienceInput(
            company="New Company",
            position="Senior Engineer",
            is_current=True
        )
        new_work = await mutation.add_work_experience("daniel-blackburn", work_input)
        assert new_work.company == "New Company"
        print(f"  Added work experience: {new_work.company}")
        
        print("\n🎉 All GraphQL resolver tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Restore original database class
        resolvers.PortfolioDatabase = original_db


def test_import_structure():
    """Test that all imports work correctly"""
    print("Testing import structure...")
    
    try:
        print("✓ Testing main.py imports...")
        # We can't import main directly due to the startup event, but we can test components
        
        print("✓ Testing resolvers.py imports...")
        import resolvers
        assert hasattr(resolvers, 'schema')
        assert hasattr(resolvers, 'Query')
        assert hasattr(resolvers, 'Mutation')
        print("  GraphQL schema created successfully")
        
        print("✓ Testing database.py imports...")
        import database
        assert hasattr(database, 'PortfolioDatabase')
        assert hasattr(database, 'init_database')
        assert hasattr(database, 'close_database')
        print("  Database module imported successfully")
        
        print("\n🎉 All import tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("=== GraphQL FastAPI Test Suite ===\n")
    
    import_success = test_import_structure()
    resolver_success = await test_graphql_resolvers()
    
    if import_success and resolver_success:
        print("\n✅ All tests passed! GraphQL FastAPI setup is working correctly.")
        print("\nNext steps:")
        print("1. Ensure PostgreSQL database is accessible at the configured URL")
        print("2. Run the database schema from sql/schema.sql")
        print("3. Start the application with: python3 main.py")
        print("4. Test GraphQL endpoints at http://localhost:8000/graphql")
        print("5. Use GraphQL Playground at http://localhost:8000/playground")
        return 0
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)