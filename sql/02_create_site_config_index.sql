-- Step 2: Create index for performance
CREATE INDEX IF NOT EXISTS idx_site_config_portfolio_key 
ON site_config(portfolio_id, config_key);
