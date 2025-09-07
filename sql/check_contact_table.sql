-- Check if contact_messages table exists and its structure
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns 
WHERE table_name = 'contact_messages'
ORDER BY ordinal_position;

-- Also check if the table exists at all
SELECT table_name 
FROM information_schema.tables 
WHERE table_name = 'contact_messages';
