-- Site Configuration Schema for De-personalization
-- This allows each portfolio to have configurable site-wide settings

-- Site Configuration Table
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

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_site_config_portfolio_key ON site_config(portfolio_id, config_key);

-- Insert default configuration values for existing portfolio
INSERT INTO site_config (portfolio_id, config_key, config_value, description) VALUES
-- Site branding
((SELECT portfolio_id FROM portfolios LIMIT 1), 'site_title', 'Professional Portfolio', 'Main site title shown in browser tab and headers'),
((SELECT portfolio_id FROM portfolios LIMIT 1), 'site_tagline', 'Building Better Solutions Through Experience', 'Hero section tagline'),
((SELECT portfolio_id FROM portfolios LIMIT 1), 'company_name', 'Portfolio Systems', 'Company/brand name used throughout site'),
((SELECT portfolio_id FROM portfolios LIMIT 1), 'copyright_name', 'Portfolio Owner', 'Name used in copyright footer'),

-- Page titles
((SELECT portfolio_id FROM portfolios LIMIT 1), 'work_page_title', 'Featured projects and work experience', 'Work page title'),
((SELECT portfolio_id FROM portfolios LIMIT 1), 'projects_page_title', 'Featured Projects', 'Projects page title'),
((SELECT portfolio_id FROM portfolios LIMIT 1), 'admin_work_title', 'Work Items Admin', 'Work admin page title'),
((SELECT portfolio_id FROM portfolios LIMIT 1), 'admin_projects_title', 'Projects Admin', 'Projects admin page title'),

-- Hero content
((SELECT portfolio_id FROM portfolios LIMIT 1), 'hero_heading', 'Building Better Solutions Through Experience', 'Main hero section heading'),
((SELECT portfolio_id FROM portfolios LIMIT 1), 'hero_description', 'With experience that expands throughout diverse environments, I have learned that foundational knowledge combined with effective communication creates a lasting impact. I thrive by embracing continuous growth and approaching every challenge with the mindset of a lifelong learner.', 'Hero section description'),
((SELECT portfolio_id FROM portfolios LIMIT 1), 'hero_quote', 'Building is easy. Building better is rewarding. Evidence-based performance enhancements are the ultimate motivator.', 'Hero section inspirational quote'),

-- About section
((SELECT portfolio_id FROM portfolios LIMIT 1), 'about_heading', 'About Me', 'About section heading'),
((SELECT portfolio_id FROM portfolios LIMIT 1), 'about_paragraph1', 'With extensive experience solving problems and architecting solutions, I appreciate the deep knowledge that comes from curiosity, trial, and hands-on problem solving. My career has taken me through diverse environments where I''ve learned that the best solutions often require looking beyond the obvious tools.', 'First about paragraph'),
((SELECT portfolio_id FROM portfolios LIMIT 1), 'about_paragraph2', 'I enjoy working with forward-thinking, collaborative teams to create time-saving toolsets and validate confidence through comprehensive test coverage. Practicing continuous improvement with clear communication, kindness, and empathy helps me work smarter and more sustainably.', 'Second about paragraph'),

-- Current focus section
((SELECT portfolio_id FROM portfolios LIMIT 1), 'focus_heading', 'Embracing Innovation', 'Current focus section heading'),
((SELECT portfolio_id FROM portfolios LIMIT 1), 'focus_description', 'Technology is evolving rapidly, and it''s an exciting time to be skilled in software development. I focus on leveraging modern tools and methodologies while maintaining strong fundamentals and best practices to deliver robust, scalable solutions.', 'Current focus description'),

-- File paths and assets
((SELECT portfolio_id FROM portfolios LIMIT 1), 'profile_image_path', '/assets/files/profile.png', 'Path to profile image'),
((SELECT portfolio_id FROM portfolios LIMIT 1), 'profile_image_alt', 'Professional headshot', 'Alt text for profile image'),
((SELECT portfolio_id FROM portfolios LIMIT 1), 'resume_filename', 'resume.pdf', 'Resume file name'),

-- OAuth and system messages
((SELECT portfolio_id FROM portfolios LIMIT 1), 'oauth_success_message', 'You have successfully logged in to your portfolio.', 'OAuth success message'),
((SELECT portfolio_id FROM portfolios LIMIT 1), 'oauth_source_name', 'Portfolio OAuth API', 'OAuth API source name'),

-- Service configuration
((SELECT portfolio_id FROM portfolios LIMIT 1), 'service_description', 'Professional Portfolio FastAPI Application', 'Systemd service description'),
((SELECT portfolio_id FROM portfolios LIMIT 1), 'service_user', 'portfolio', 'System user for running the service')

ON CONFLICT (portfolio_id, config_key) DO NOTHING;

-- Add trigger to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_site_config_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_site_config_updated_at
    BEFORE UPDATE ON site_config
    FOR EACH ROW
    EXECUTE FUNCTION update_site_config_updated_at();
