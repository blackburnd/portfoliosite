-- Site Configuration Migration SQL
-- Run this manually to create the site_config table and infrastructure
-- Safe to run multiple times (uses IF NOT EXISTS)

-- Step 1: Create the site_config table
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

-- Step 2: Create index for performance
CREATE INDEX IF NOT EXISTS idx_site_config_portfolio_key 
ON site_config(portfolio_id, config_key);

-- Step 3: Create update trigger function
CREATE OR REPLACE FUNCTION update_site_config_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Step 4: Create the trigger (drop first to avoid conflicts)
DROP TRIGGER IF EXISTS update_site_config_updated_at ON site_config;
CREATE TRIGGER update_site_config_updated_at
    BEFORE UPDATE ON site_config
    FOR EACH ROW
    EXECUTE FUNCTION update_site_config_updated_at();

-- Step 5: Insert default configuration values for existing portfolio
-- Note: This uses the first portfolio found, or you can replace with specific portfolio_id
INSERT INTO site_config (portfolio_id, config_key, config_value, description) VALUES
-- Site branding
((SELECT portfolio_id FROM portfolios LIMIT 1), 'site_title', 'Blackburn Systems Portfolio', 'Main site title shown in browser tab and headers'),
((SELECT portfolio_id FROM portfolios LIMIT 1), 'site_tagline', 'Building Better Solutions Through Experience', 'Hero section tagline'),
((SELECT portfolio_id FROM portfolios LIMIT 1), 'company_name', 'Blackburn Systems', 'Company/brand name used throughout site'),
((SELECT portfolio_id FROM portfolios LIMIT 1), 'copyright_name', 'Blackburn', 'Name used in copyright footer'),

-- Page titles
((SELECT portfolio_id FROM portfolios LIMIT 1), 'work_page_title', 'Featured projects, and work - daniel blackburn', 'Work page title'),
((SELECT portfolio_id FROM portfolios LIMIT 1), 'projects_page_title', 'Projects - Daniel Blackburn', 'Projects page title'),
((SELECT portfolio_id FROM portfolios LIMIT 1), 'admin_work_title', 'Work Items Admin - Daniel Blackburn', 'Work admin page title'),
((SELECT portfolio_id FROM portfolios LIMIT 1), 'admin_projects_title', 'Projects Admin - Daniel Blackburn', 'Projects admin page title'),

-- Hero content
((SELECT portfolio_id FROM portfolios LIMIT 1), 'hero_heading', 'Building Better Solutions Through Experience', 'Main hero section heading'),
((SELECT portfolio_id FROM portfolios LIMIT 1), 'hero_description', 'With experience that expands throughout University IT departments, corporate banking environments, and agile remote startup companies, I have learned that foundational knowledge combined with effective communication creates a lasting impact. I thrive by embracing continuous growth and approaching every challenge with the mindset of a lifelong learner.', 'Hero section description'),
((SELECT portfolio_id FROM portfolios LIMIT 1), 'hero_quote', 'Building is easy. Building better is rewarding. Evidence-based performance enhancements are the ultimate motivator.', 'Hero section inspirational quote'),

-- About section
((SELECT portfolio_id FROM portfolios LIMIT 1), 'about_heading', 'About Me', 'About section heading'),
((SELECT portfolio_id FROM portfolios LIMIT 1), 'about_paragraph1', 'With over two decades of experience solving problems and architecting solutions, I appreciate the deep knowledge that comes from curiosity, trial, and hands-on problem solving. My career has taken me through diverse environments where I''ve learned that the best solutions often require looking beyond the obvious tools.', 'First about paragraph'),
((SELECT portfolio_id FROM portfolios LIMIT 1), 'about_paragraph2', 'I enjoy working with forward-thinking, collaborative teams to create time-saving toolsets and validate confidence through comprehensive test coverage. Practicing continuous improvement with clear communication, kindness, and empathy helps me work smarter and more sustainably. Equally important is appreciating the strengths and limitations of my environment and team, which provides invaluable perspective.', 'Second about paragraph'),

-- Current focus section
((SELECT portfolio_id FROM portfolios LIMIT 1), 'focus_heading', 'Embracing the AI Revolution', 'Current focus section heading'),
((SELECT portfolio_id FROM portfolios LIMIT 1), 'focus_description', 'Things are changing fast, and it''s an incredibly exciting time to be skilled in software development—especially when you have a clear sense of what ''correct'' looks like. I think of using AI as a pair programmer like working with a mischievous djinn: it''s resourceful but often unreliable, yet with clear guardrails, good oversight, and thoughtful follow-up, it can provide surprisingly valuable solutions.', 'Current focus description'),

-- File paths and assets
((SELECT portfolio_id FROM portfolios LIMIT 1), 'profile_image_path', '/assets/files/daniel2.png', 'Path to profile image'),
((SELECT portfolio_id FROM portfolios LIMIT 1), 'profile_image_alt', 'Daniel Blackburn', 'Alt text for profile image'),
((SELECT portfolio_id FROM portfolios LIMIT 1), 'resume_filename', 'danielblackburn.pdf', 'Resume file name'),

-- OAuth and system messages
((SELECT portfolio_id FROM portfolios LIMIT 1), 'oauth_success_message', 'You have successfully logged in to Blackburn Systems portfolio.', 'OAuth success message'),
((SELECT portfolio_id FROM portfolios LIMIT 1), 'oauth_source_name', 'Blackburn Systems OAuth API', 'OAuth API source name'),

-- Service configuration
((SELECT portfolio_id FROM portfolios LIMIT 1), 'service_description', 'Daniel Blackburn''s Portfolio FastAPI Application', 'Systemd service description'),
((SELECT portfolio_id FROM portfolios LIMIT 1), 'service_user', 'blackburnd', 'System user for running the service')

-- Use ON CONFLICT to avoid errors if re-running
ON CONFLICT (portfolio_id, config_key) DO UPDATE SET
    config_value = EXCLUDED.config_value,
    description = EXCLUDED.description,
    updated_at = NOW();

-- Step 6: Verify the migration worked
SELECT 
    COUNT(*) as total_configs,
    portfolio_id
FROM site_config 
GROUP BY portfolio_id;

-- Optional: View all configurations
-- SELECT config_key, config_value, description FROM site_config ORDER BY config_key;
