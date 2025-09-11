"""
Migration script to add site configuration support
Run this to de-personalize the portfolio platform
"""
import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import database, get_portfolio_id


async def run_migration():
    """Apply site configuration schema migration"""
    
    print("🚀 Starting site configuration migration...")
    
    try:
        # Connect to database
        await database.connect()
        print("✅ Connected to database")
        
        # Get portfolio ID
        portfolio_id = get_portfolio_id()
        if not portfolio_id:
            print("❌ No portfolio ID found. Cannot apply migration.")
            return False
        
        print(f"📋 Using portfolio ID: {portfolio_id}")
        
        # Create site_config table
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS site_config (
            id SERIAL PRIMARY KEY,
            portfolio_id UUID NOT NULL REFERENCES portfolios(portfolio_id) ON DELETE CASCADE,
            config_key VARCHAR(100) NOT NULL,
            config_value TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(portfolio_id, config_key)
        );
        """
        
        await database.execute(create_table_sql)
        print("✅ Created site_config table")
        
        # Create index
        index_sql = """
        CREATE INDEX IF NOT EXISTS idx_site_config_portfolio_key 
        ON site_config(portfolio_id, config_key);
        """
        
        await database.execute(index_sql)
        print("✅ Created index")
        
        # Insert default configuration
        config_values = [
            ('site_title', 'Professional Portfolio', 'Main site title'),
            ('site_tagline', 'Building Better Solutions Through Experience', 'Hero tagline'),
            ('company_name', 'Portfolio Systems', 'Company/brand name'),
            ('copyright_name', 'Portfolio Owner', 'Copyright name'),
            ('work_page_title', 'Featured projects and work experience', 'Work page title'),
            ('projects_page_title', 'Featured Projects', 'Projects page title'),
            ('admin_work_title', 'Work Items Admin', 'Work admin page title'),
            ('admin_projects_title', 'Projects Admin', 'Projects admin page title'),
            ('hero_heading', 'Building Better Solutions Through Experience', 'Hero heading'),
            ('about_heading', 'About Me', 'About section heading'),
            ('focus_heading', 'Embracing Innovation', 'Focus section heading'),
            ('profile_image_path', '/assets/files/profile.png', 'Profile image path'),
            ('profile_image_alt', 'Professional headshot', 'Profile image alt text'),
            ('resume_filename', 'resume.pdf', 'Resume filename'),
            ('oauth_success_message', 'You have successfully logged in to your portfolio.', 'OAuth success message'),
            ('oauth_source_name', 'Portfolio OAuth API', 'OAuth source name'),
        ]
        
        insert_sql = """
        INSERT INTO site_config (portfolio_id, config_key, config_value, description)
        VALUES (:portfolio_id, :config_key, :config_value, :description)
        ON CONFLICT (portfolio_id, config_key) DO NOTHING
        """
        
        for config_key, config_value, description in config_values:
            await database.execute(insert_sql, {
                "portfolio_id": portfolio_id,
                "config_key": config_key,
                "config_value": config_value,
                "description": description
            })
        
        print(f"✅ Inserted {len(config_values)} configuration values")
        
        # Create update trigger
        trigger_sql = """
        CREATE OR REPLACE FUNCTION update_site_config_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';

        DROP TRIGGER IF EXISTS update_site_config_updated_at ON site_config;
        CREATE TRIGGER update_site_config_updated_at
            BEFORE UPDATE ON site_config
            FOR EACH ROW
            EXECUTE FUNCTION update_site_config_updated_at();
        """
        
        await database.execute(trigger_sql)
        print("✅ Created update trigger")
        
        print("🎉 Migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False
    
    finally:
        await database.disconnect()
        print("📡 Disconnected from database")


if __name__ == "__main__":
    asyncio.run(run_migration())
