-- Create database: daniel_portfolio
-- Run this first: CREATE DATABASE daniel_portfolio;

-- Connect to the daniel_portfolio database and run the following:

-- Portfolio table
CREATE TABLE IF NOT EXISTS portfolios (
    id VARCHAR(100) PRIMARY KEY,
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
    portfolio_id VARCHAR(100) NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
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
    portfolio_id VARCHAR(100) NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
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
    portfolio_id VARCHAR(100) NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL,
    subject VARCHAR(300),
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_work_experience_portfolio_id ON work_experience(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_work_experience_sort_order ON work_experience(sort_order);
CREATE INDEX IF NOT EXISTS idx_projects_portfolio_id ON projects(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_projects_sort_order ON projects(sort_order);
CREATE INDEX IF NOT EXISTS idx_contact_messages_portfolio_id ON contact_messages(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_contact_messages_created_at ON contact_messages(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_contact_messages_is_read ON contact_messages(is_read);

-- Insert initial data for Daniel Blackburn
INSERT INTO portfolios (
    id, name, title, bio, tagline, profile_image,
    email, phone, vcard, resume_url, resume_download, github, twitter,
    skills
) VALUES (
    'daniel-blackburn',
    'Daniel',
    'Software Developer & Cloud Engineer',
    'Passionate software developer with expertise in cloud technologies, automation, and modern web development. Experienced in building scalable applications and robust CI/CD pipelines.',
    'Building innovative solutions with modern technology',
    '/assets/img/daniel-blackburn.jpg',
    'daniel@blackburn.dev',
    '555-123-4567',
    'Daniel Blackburn.vcf',
    'linkedin.com/in/danielblackburn',
    'danielblackburn-resume.pdf',
    '@blackburnd',
    '@danielblackburn',
    '["Python", "FastAPI", "GraphQL", "PostgreSQL", "CI/CD", "Cloud Computing", "JavaScript", "React", "Docker"]'::jsonb
) ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    title = EXCLUDED.title,
    bio = EXCLUDED.bio,
    tagline = EXCLUDED.tagline,
    email = EXCLUDED.email,
    phone = EXCLUDED.phone,
    skills = EXCLUDED.skills,
    updated_at = NOW();

-- Insert sample work experience
INSERT INTO work_experience (
    portfolio_id, company, position, location, start_date, end_date,
    description, is_current, company_url, sort_order
) VALUES 
(
    'daniel-blackburn',
    'Your Current Company',
    'Software Engineer/Developer',
    'Remote',
    '2023',
    NULL,
    'Building innovative solutions with modern technologies including FastAPI, GraphQL, and cloud infrastructure. Leading development of automated deployment pipelines and scalable web applications.',
    TRUE,
    'https://yourcompany.com',
    1
),
(
    'daniel-blackburn',
    'Previous Company',
    'Developer',
    'City, State',
    '2021',
    '2023',
    'Developed and maintained web applications using modern frameworks. Collaborated with cross-functional teams to deliver high-quality software solutions.',
    FALSE,
    NULL,
    2
) ON CONFLICT DO NOTHING;

-- Insert sample projects
INSERT INTO projects (
    portfolio_id, title, description, url, technologies, sort_order
) VALUES 
(
    'daniel-blackburn',
    'Cloud Machine Project',
    'Automated cloud infrastructure and deployment pipeline with CI/CD integration. Features include automated testing, deployment orchestration, and monitoring.',
    'https://github.com/blackburnd/cloud_machine_repo',
    '["Python", "FastAPI", "GraphQL", "CI/CD", "PostgreSQL", "Docker"]'::jsonb,
    1
),
(
    'daniel-blackburn',
    'Portfolio API',
    'Modern portfolio website backend built with FastAPI and GraphQL. Features real-time contact forms, dynamic content management, and responsive design.',
    NULL,
    '["FastAPI", "GraphQL", "PostgreSQL", "HTML/CSS", "JavaScript"]'::jsonb,
    2
) ON CONFLICT DO NOTHING;

-- Create a function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers to automatically update updated_at
CREATE TRIGGER update_portfolios_updated_at 
    BEFORE UPDATE ON portfolios 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_work_experience_updated_at 
    BEFORE UPDATE ON work_experience 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_projects_updated_at 
    BEFORE UPDATE ON projects 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
