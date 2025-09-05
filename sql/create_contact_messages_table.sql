-- Create contact_messages table
CREATE TABLE IF NOT EXISTS contact_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    subject VARCHAR(500),
    message TEXT NOT NULL,
    ip_address INET,
    user_agent TEXT,
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_read BOOLEAN DEFAULT FALSE,
    admin_notes TEXT
);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_contact_messages_submitted_at ON contact_messages(submitted_at DESC);
CREATE INDEX IF NOT EXISTS idx_contact_messages_is_read ON contact_messages(is_read);
CREATE INDEX IF NOT EXISTS idx_contact_messages_email ON contact_messages(email);

-- Add comment
COMMENT ON TABLE contact_messages IS 'Stores contact form submissions from the website';
