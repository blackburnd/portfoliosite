-- Add IP analysis fields to page_analytics table for enhanced bot detection
-- This extends the mouse_activity tracking with reverse DNS and visitor classification

-- Add reverse DNS hostname field
ALTER TABLE page_analytics 
ADD COLUMN IF NOT EXISTS reverse_dns VARCHAR(255);

-- Add visitor classification field
ALTER TABLE page_analytics 
ADD COLUMN IF NOT EXISTS visitor_type VARCHAR(20) DEFAULT 'unknown';

-- Add datacenter/hosting detection flag
ALTER TABLE page_analytics 
ADD COLUMN IF NOT EXISTS is_datacenter BOOLEAN DEFAULT FALSE;

-- Add ASN (Autonomous System Number) for network analysis
ALTER TABLE page_analytics 
ADD COLUMN IF NOT EXISTS asn VARCHAR(50);

-- Add organization/ISP name
ALTER TABLE page_analytics 
ADD COLUMN IF NOT EXISTS organization VARCHAR(255);

-- Create indexes for efficient filtering
CREATE INDEX IF NOT EXISTS idx_page_analytics_visitor_type ON page_analytics(visitor_type);
CREATE INDEX IF NOT EXISTS idx_page_analytics_is_datacenter ON page_analytics(is_datacenter);
CREATE INDEX IF NOT EXISTS idx_page_analytics_reverse_dns ON page_analytics(reverse_dns);
CREATE INDEX IF NOT EXISTS idx_page_analytics_asn ON page_analytics(asn);

-- Add comments to explain the new fields
COMMENT ON COLUMN page_analytics.reverse_dns IS 'Reverse DNS hostname for the IP address (e.g., googlebot.com, crawler.example.com)';
COMMENT ON COLUMN page_analytics.visitor_type IS 'Visitor classification: human, bot, suspicious, unknown';
COMMENT ON COLUMN page_analytics.is_datacenter IS 'True if IP belongs to a hosting/datacenter/VPS provider';
COMMENT ON COLUMN page_analytics.asn IS 'Autonomous System Number for network identification';
COMMENT ON COLUMN page_analytics.organization IS 'Organization/ISP name associated with the IP address';