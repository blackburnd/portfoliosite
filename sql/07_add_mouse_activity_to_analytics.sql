-- Add mouse_activity field to page_analytics table for bot filtering
-- This field will track whether the visit included mouse movement (true = human, false/null = likely bot)

-- Add the new column with default false
ALTER TABLE page_analytics 
ADD COLUMN IF NOT EXISTS mouse_activity BOOLEAN DEFAULT FALSE;

-- Create index for filtering by mouse activity
CREATE INDEX IF NOT EXISTS idx_page_analytics_mouse_activity ON page_analytics(mouse_activity);

-- Add comment to explain the field
COMMENT ON COLUMN page_analytics.mouse_activity IS 'Tracks whether mouse movement was detected during the visit (true = human interaction, false/null = likely bot)';