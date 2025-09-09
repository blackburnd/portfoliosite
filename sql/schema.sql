-- Portfolio table with UUID primary key and VARCHAR unique identifier
CREATE TABLE IF NOT EXISTS portfolios (
    portfolio_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    id VARCHAR(100) UNIQUE NOT NULL, -- Keep existing string id for compatibility
    name VARCHAR(100) NOT NULL,
    title VARCHAR(200) NOT NULL,
    bio TEXT NOT NULL,
    tagline VARCHAR(300),
    profile_image VARCHAR(300),
    email VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    vcard VARCHAR(100),
    resume_url VARCHAR(300),
    resume_download VARCHAR(300),
    github VARCHAR(100),
    twitter VARCHAR(100),
    skills JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Work Experience table
CREATE TABLE IF NOT EXISTS work_experience (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID NOT NULL REFERENCES portfolios(portfolio_id) ON DELETE CASCADE,
    company VARCHAR(200) NOT NULL,
    position VARCHAR(200) NOT NULL,
    location VARCHAR(200),
    start_date VARCHAR(20),
    end_date VARCHAR(20),
    description TEXT,
    is_current BOOLEAN DEFAULT FALSE,
    company_url VARCHAR(300),
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Projects table
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID NOT NULL REFERENCES portfolios(portfolio_id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    url VARCHAR(300),
    image_url VARCHAR(300),
    technologies JSONB DEFAULT '[]'::jsonb,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Contact Messages table
CREATE TABLE IF NOT EXISTS contact_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID NOT NULL REFERENCES portfolios(portfolio_id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL,
    subject VARCHAR(300),
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- OAuth Apps table (used by TTWOAuthManager)
CREATE TABLE IF NOT EXISTS oauth_apps (
    id SERIAL PRIMARY KEY,
    portfolio_id UUID NOT NULL REFERENCES portfolios(portfolio_id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL,
    client_id TEXT NOT NULL,
    client_secret TEXT NOT NULL,
    redirect_uri TEXT,
    scopes TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(portfolio_id, provider)
);

-- App Log table (used by log_capture.py)
CREATE TABLE IF NOT EXISTS app_log (
    id SERIAL PRIMARY KEY,
    portfolio_id UUID NOT NULL REFERENCES portfolios(portfolio_id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    level TEXT NOT NULL,
    message TEXT NOT NULL,
    module TEXT,
    function TEXT,
    line INTEGER,
    "user" TEXT,
    extra TEXT,
    ip_address VARCHAR(45),
    user_agent TEXT,
    traceback TEXT
);

-- Google OAuth Tokens table (used by database.py functions)
CREATE TABLE IF NOT EXISTS google_oauth_tokens (
    id SERIAL PRIMARY KEY,
    portfolio_id UUID NOT NULL REFERENCES portfolios(portfolio_id) ON DELETE CASCADE,
    admin_email VARCHAR(100) NOT NULL,
    access_token TEXT,
    refresh_token TEXT,
    token_expires_at TIMESTAMP WITH TIME ZONE,
    granted_scopes TEXT,
    requested_scopes TEXT,
    last_used_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(portfolio_id, admin_email)
);

-- OAuth State Management table for popup CSRF validation
CREATE TABLE IF NOT EXISTS oauth_states (
    state VARCHAR(100) PRIMARY KEY,
    portfolio_id UUID NOT NULL REFERENCES portfolios(portfolio_id) ON DELETE CASCADE,
    used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL
);

-- LinkedIn OAuth Config table
CREATE TABLE IF NOT EXISTS linkedin_oauth_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID NOT NULL REFERENCES portfolios(portfolio_id) ON DELETE CASCADE,
    app_name VARCHAR(200) NOT NULL DEFAULT 'Portfolio LinkedIn Integration',
    client_id VARCHAR(200) NOT NULL,
    client_secret TEXT NOT NULL,
    redirect_uri VARCHAR(500) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    configured_by_email VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- LinkedIn OAuth Connections table
CREATE TABLE IF NOT EXISTS linkedin_oauth_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID NOT NULL REFERENCES portfolios(portfolio_id) ON DELETE CASCADE,
    admin_email VARCHAR(100) NOT NULL,
    access_token TEXT,
    refresh_token TEXT,
    token_expires_at TIMESTAMP WITH TIME ZONE,
    granted_scopes TEXT,
    requested_scopes TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- LinkedIn OAuth Scopes table
CREATE TABLE IF NOT EXISTS linkedin_oauth_scopes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID NOT NULL REFERENCES portfolios(portfolio_id) ON DELETE CASCADE,
    scope_name VARCHAR(100) NOT NULL,
    display_name VARCHAR(200) NOT NULL,
    description TEXT,
    data_access_description TEXT,
    is_required BOOLEAN DEFAULT FALSE,
    is_enabled BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(portfolio_id, scope_name)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_work_experience_portfolio_id ON work_experience(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_work_experience_sort_order ON work_experience(sort_order);
CREATE INDEX IF NOT EXISTS idx_projects_portfolio_id ON projects(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_projects_sort_order ON projects(sort_order);
CREATE INDEX IF NOT EXISTS idx_contact_messages_portfolio_id ON contact_messages(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_contact_messages_created_at ON contact_messages(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_contact_messages_is_read ON contact_messages(is_read);
CREATE INDEX IF NOT EXISTS idx_oauth_apps_portfolio_id ON oauth_apps(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_oauth_apps_provider ON oauth_apps(provider);
CREATE INDEX IF NOT EXISTS idx_oauth_apps_active ON oauth_apps(is_active);
CREATE INDEX IF NOT EXISTS idx_app_log_portfolio_id ON app_log(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_app_log_timestamp ON app_log(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_google_oauth_tokens_portfolio_id ON google_oauth_tokens(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_google_oauth_tokens_admin_email ON google_oauth_tokens(admin_email);
CREATE INDEX IF NOT EXISTS idx_linkedin_oauth_config_portfolio_id ON linkedin_oauth_config(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_linkedin_oauth_connections_portfolio_id ON linkedin_oauth_connections(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_linkedin_oauth_scopes_portfolio_id ON linkedin_oauth_scopes(portfolio_id);

-- Insert default portfolio
INSERT INTO portfolios (id, name, title, bio, tagline, profile_image, email, phone, vcard, resume_url, resume_download, github, twitter, skills) VALUES 
('daniel-blackburn', 'Daniel', 'Software Developer & Cloud Engineer', 'Passionate software developer with expertise in cloud technologies, automation, and modern web development. Experienced in building scalable applications and robust CI/CD pipelines.', 'Building innovative solutions with modern technology', '/assets/img/daniel-blackburn.jpg', 'daniel@blackburn.dev', '555-123-4567', 'Daniel Blackburn.vcf', 'linkedin.com/in/danielblackburn', 'danielblackburn-resume.pdf', '@blackburnd', '@danielblackburn', '["Python", "FastAPI", "GraphQL", "PostgreSQL", "CI/CD", "Cloud Computing", "JavaScript", "React", "Docker"]'::jsonb)
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    title = EXCLUDED.title,
    bio = EXCLUDED.bio,
    tagline = EXCLUDED.tagline,
    email = EXCLUDED.email,
    phone = EXCLUDED.phone,
    skills = EXCLUDED.skills,
    updated_at = NOW();

-- Create triggers for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_portfolios_updated_at 
    BEFORE UPDATE ON portfolios 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_work_experience_updated_at 
    BEFORE UPDATE ON work_experience 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_projects_updated_at 
    BEFORE UPDATE ON projects 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_oauth_apps_updated_at 
    BEFORE UPDATE ON oauth_apps 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_google_oauth_tokens_updated_at 
    BEFORE UPDATE ON google_oauth_tokens 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_linkedin_oauth_config_updated_at 
    BEFORE UPDATE ON linkedin_oauth_config 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_linkedin_oauth_connections_updated_at 
    BEFORE UPDATE ON linkedin_oauth_connections 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();