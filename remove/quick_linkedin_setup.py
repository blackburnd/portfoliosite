#!/usr/bin/env python3
"""
Quick LinkedIn OAuth Setup
Just run this to configure LinkedIn OAuth for issue #25
"""
import asyncio
import os
import sys

async def setup_linkedin_oauth():
    """Simple LinkedIn OAuth configuration setup"""
    print("=== LinkedIn OAuth Setup ===")
    
    # We'll just create environment variables for now
    print("\nTo fix the LinkedIn connection, you need:")
    print("1. A LinkedIn Developer App with these settings:")
    print("   - App name: Portfolio Site")
    print("   - Redirect URL: https://www.blackburnsystems.com/linkedin/oauth/callback")
    print("   - Permissions: r_liteprofile, r_emailaddress")
    
    print("\n2. Add these to your .env file (I won't modify it, just telling you what's needed):")
    print("   LINKEDIN_CLIENT_ID=your_linkedin_client_id")
    print("   LINKEDIN_CLIENT_SECRET=your_linkedin_client_secret")
    
    print("\n3. Or temporarily set them now:")
    client_id = input("Enter LinkedIn Client ID (or press Enter to skip): ").strip()
    if client_id:
        os.environ["LINKEDIN_CLIENT_ID"] = client_id
        client_secret = input("Enter LinkedIn Client Secret: ").strip()
        if client_secret:
            os.environ["LINKEDIN_CLIENT_SECRET"] = client_secret
            print("✅ LinkedIn OAuth temporarily configured for this session")
            
            # Test the configuration
            print("\nTesting configuration...")
            try:
                from ttw_oauth_manager import TTWOAuthManager
                manager = TTWOAuthManager()
                # This will fail if not configured
                print("✅ LinkedIn OAuth manager initialized successfully")
            except Exception as e:
                print(f"❌ Configuration test failed: {e}")
        else:
            print("❌ Client secret required")
    else:
        print("❌ Setup skipped - LinkedIn OAuth still not configured")

if __name__ == "__main__":
    asyncio.run(setup_linkedin_oauth())
