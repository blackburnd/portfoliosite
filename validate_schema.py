#!/usr/bin/env python3
"""
Script to validate GraphQL schema and catch type definition conflicts early.
"""
import sys
import os

def validate_schema():
    """Validate the GraphQL schema and report any issues."""
    try:
        # Set dummy DATABASE_URL if not provided
        if not os.getenv('DATABASE_URL'):
            os.environ['DATABASE_URL'] = 'postgresql://dummy:dummy@localhost/dummy'
        
        # Import the schema
        from app.resolvers import schema
        
        # Try to introspect the schema to catch any issues
        introspection = schema.introspect()
        
        print("✓ GraphQL schema validation passed")
        print(f"✓ Schema contains {len(introspection.get('types', []))} types")
        
        return True
        
    except Exception as e:
        print(f"✗ GraphQL schema validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = validate_schema()
    sys.exit(0 if success else 1)
