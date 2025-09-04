-- Insert default LinkedIn OAuth scopes

INSERT INTO linkedin_oauth_scopes (scope_name, display_name, description, data_access_description, is_required, sort_order) VALUES
('r_liteprofile', 'Basic Profile', 'Access to basic profile information', 'First name, last name, profile picture, headline', true, 1),
('r_emailaddress', 'Email Address', 'Access to primary email address', 'Primary email address associated with LinkedIn account', true, 2),
('r_basicprofile', 'Full Profile', 'Access to full profile information', 'Complete profile including summary, location, industry', false, 3),
('rw_company_admin', 'Company Administration', 'Access to company pages (if admin)', 'Company page information for pages you admin', false, 4),
('w_member_social', 'Share Content', 'Ability to share content on behalf of user', 'Post updates and share content to LinkedIn feed', false, 5)
ON CONFLICT (scope_name) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    data_access_description = EXCLUDED.data_access_description,
    is_required = EXCLUDED.is_required,
    sort_order = EXCLUDED.sort_order;
