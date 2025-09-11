-- Insert default site configuration values
-- Run this after creating the site_config table

-- Personal Information defaults
INSERT INTO site_config (portfolio_id, config_key, config_value, description, updated_at)
SELECT 
    portfolio_id,
    'full_name',
    'Your Name',
    'Full name as it appears on the site',
    NOW()
FROM portfolios
ON CONFLICT (portfolio_id, config_key) DO NOTHING;

INSERT INTO site_config (portfolio_id, config_key, config_value, description, updated_at)
SELECT 
    portfolio_id,
    'professional_title',
    'Professional Title',
    'Your job title or professional description',
    NOW()
FROM portfolios
ON CONFLICT (portfolio_id, config_key) DO NOTHING;

-- Site Settings defaults
INSERT INTO site_config (portfolio_id, config_key, config_value, description, updated_at)
SELECT 
    portfolio_id,
    'site_title',
    'Portfolio Website',
    'Main site title for browser tab and headers',
    NOW()
FROM portfolios
ON CONFLICT (portfolio_id, config_key) DO NOTHING;

INSERT INTO site_config (portfolio_id, config_key, config_value, description, updated_at)
SELECT 
    portfolio_id,
    'company_name',
    'Your Company',
    'Company or personal brand name',
    NOW()
FROM portfolios
ON CONFLICT (portfolio_id, config_key) DO NOTHING;

-- Navigation defaults
INSERT INTO site_config (portfolio_id, config_key, config_value, description, updated_at)
SELECT 
    portfolio_id,
    'nav_home_label',
    'Overview',
    'Label for home/overview navigation link',
    NOW()
FROM portfolios
ON CONFLICT (portfolio_id, config_key) DO NOTHING;

INSERT INTO site_config (portfolio_id, config_key, config_value, description, updated_at)
SELECT 
    portfolio_id,
    'nav_work_label',
    'Select Work',
    'Label for work/portfolio navigation link',
    NOW()
FROM portfolios
ON CONFLICT (portfolio_id, config_key) DO NOTHING;

INSERT INTO site_config (portfolio_id, config_key, config_value, description, updated_at)
SELECT 
    portfolio_id,
    'nav_projects_label',
    'Projects',
    'Label for projects navigation link',
    NOW()
FROM portfolios
ON CONFLICT (portfolio_id, config_key) DO NOTHING;

INSERT INTO site_config (portfolio_id, config_key, config_value, description, updated_at)
SELECT 
    portfolio_id,
    'nav_contact_label',
    'Contact',
    'Label for contact navigation link',
    NOW()
FROM portfolios
ON CONFLICT (portfolio_id, config_key) DO NOTHING;

-- Content defaults
INSERT INTO site_config (portfolio_id, config_key, config_value, description, updated_at)
SELECT 
    portfolio_id,
    'homepage_hero_title',
    'Welcome to My Portfolio',
    'Main hero section title on homepage',
    NOW()
FROM portfolios
ON CONFLICT (portfolio_id, config_key) DO NOTHING;

INSERT INTO site_config (portfolio_id, config_key, config_value, description, updated_at)
SELECT 
    portfolio_id,
    'homepage_hero_subtitle',
    'Discover my work and experience',
    'Hero section subtitle on homepage',
    NOW()
FROM portfolios
ON CONFLICT (portfolio_id, config_key) DO NOTHING;

INSERT INTO site_config (portfolio_id, config_key, config_value, description, updated_at)
SELECT 
    portfolio_id,
    'work_page_title',
    'My Work',
    'Title for the work/portfolio page',
    NOW()
FROM portfolios
ON CONFLICT (portfolio_id, config_key) DO NOTHING;

INSERT INTO site_config (portfolio_id, config_key, config_value, description, updated_at)
SELECT 
    portfolio_id,
    'projects_page_title',
    'My Projects',
    'Title for the projects page',
    NOW()
FROM portfolios
ON CONFLICT (portfolio_id, config_key) DO NOTHING;

-- Contact defaults
INSERT INTO site_config (portfolio_id, config_key, config_value, description, updated_at)
SELECT 
    portfolio_id,
    'contact_form_title',
    'Get In Touch',
    'Title for contact form section',
    NOW()
FROM portfolios
ON CONFLICT (portfolio_id, config_key) DO NOTHING;

INSERT INTO site_config (portfolio_id, config_key, config_value, description, updated_at)
SELECT 
    portfolio_id,
    'contact_success_message',
    'Thank you for your message! I will get back to you soon.',
    'Message shown after successful contact form submission',
    NOW()
FROM portfolios
ON CONFLICT (portfolio_id, config_key) DO NOTHING;

-- Verify insertion
SELECT 
    config_key,
    config_value,
    description
FROM site_config 
WHERE portfolio_id = (SELECT portfolio_id FROM portfolios LIMIT 1)
ORDER BY config_key;
