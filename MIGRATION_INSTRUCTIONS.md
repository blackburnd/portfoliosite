# Portfolio Data Migration Instructions

## Overview

This guide helps you migrate from hardcoded HTML template content to a fully dynamic, database-driven portfolio system. The migration extracts all current portfolio data and populates the database tables.

## Pre-Migration Checklist

1. **Backup Current Data**
   ```bash
   # Export current database
   gcloud sql export sql blackburn-portfolio-db gs://your-backup-bucket/portfolio_backup_$(date +%Y%m%d_%H%M%S).sql
   
   # Or create a local backup of templates
   cp -r templates templates_backup
   ```

2. **Verify Database Schema**
   - Ensure all required tables exist: `portfolios`, `work_experience`, `projects`, `site_config`
   - Check that TTW configuration system is working at `/admin`

3. **Check Current Portfolio ID**
   ```bash
   # SSH to production instance
   gcloud compute ssh your-instance-name
   
   # Check current portfolio ID
   python3 -c "
   import sys
   sys.path.append('/path/to/app')
   from database import get_portfolio_id
   print('Current portfolio_id:', get_portfolio_id())
   "
   ```

## Migration Steps

### Step 1: Review Migration Data

The `populate_portfolio_data.py` script contains extracted data from your current templates:

- **Portfolio Record**: Name, title, bio, contact info, skills
- **Work Experience**: Blackburn Systems + placeholder previous company
- **Projects**: Portfolio website, Cloud automation, Data analytics platform  
- **Site Configuration**: 35+ config values for navigation, content, social links

**Review and customize this data before running the migration.**

### Step 2: Customize Migration Data

Edit `populate_portfolio_data.py` to match your actual content:

```python
# Update portfolio_data with your actual information
portfolio_data = {
    "name": "Your Actual Name",
    "title": "Your Actual Title",
    "bio": "Your actual bio...",
    # ... update all fields
}

# Update work_experiences with your actual work history
work_experiences = [
    {
        "company": "Your Current Company",
        "position": "Your Position",
        # ... update all fields
    }
]

# Update projects with your actual projects
projects = [
    {
        "title": "Your Project Name",
        "description": "Your project description...",
        # ... update all fields
    }
]
```

### Step 3: Run Migration Locally (Optional Test)

```bash
# Test migration script syntax
python3 populate_portfolio_data.py --help

# Or run a dry-run check (if you add dry-run functionality)
```

### Step 4: Deploy and Run Migration

```bash
# Commit migration script
git add populate_portfolio_data.py
git commit -m "Add portfolio data migration script"
git push origin main

# Deploy to production
./deploy.sh

# SSH to production instance
gcloud compute ssh your-instance-name

# Navigate to application directory
cd /path/to/your/app

# Run migration
python3 populate_portfolio_data.py
```

**Expected Output:**
```
🎯 Populating portfolio data for portfolio_id: 3fc521ad-660c-4067-b416-17dc388e66eb
📝 Updating portfolio record...
   ✅ Updated portfolio record for Daniel Blackburn
💼 Adding work experience...
   ✅ Added: Senior Software Developer & Cloud Engineer at Blackburn Systems
   ✅ Added: Full Stack Developer at Previous Technology Company
🚀 Adding projects...
   ✅ Added: Portfolio Website & API
   ✅ Added: Cloud Infrastructure Automation
   ✅ Added: Data Analytics Platform
⚙️  Adding site configuration...
   ✅ Added 35 configuration items
✅ Portfolio data population completed!
```

### Step 5: Verify Migration Results

1. **Check Database Data**
   - Visit `/admin/sql` and run queries to verify data:
   ```sql
   SELECT * FROM portfolios WHERE portfolio_id = '3fc521ad-660c-4067-b416-17dc388e66eb';
   SELECT * FROM work_experience WHERE portfolio_id = '3fc521ad-660c-4067-b416-17dc388e66eb';
   SELECT * FROM projects WHERE portfolio_id = '3fc521ad-660c-4067-b416-17dc388e66eb';
   SELECT COUNT(*) FROM site_config;
   ```

2. **Test GraphQL API**
   - Visit `/work` and `/projects` pages
   - Verify all data displays correctly
   - Check admin interfaces work properly

3. **Verify Site Configuration**
   - Visit `/admin` and check all TTW configuration categories
   - Test saving/updating configuration values

### Step 6: Update Templates (Future Phase)

After migration is successful, you can update templates to use database values instead of hardcoded content:

```html
<!-- Instead of hardcoded: -->
<h1>Daniel Blackburn</h1>

<!-- Use site config: -->
<h1>{{ config.get('full_name', 'Default Name') }}</h1>

<!-- Instead of hardcoded portfolio data: -->
<p>Hardcoded bio here...</p>

<!-- Use GraphQL data: -->
<p>{{ portfolio.bio }}</p>
```

## Troubleshooting

### Migration Fails with Database Error

```bash
# Check database connection
python3 -c "
from database import database, init_database
import asyncio
async def test():
    await init_database()
    result = await database.fetch_one('SELECT NOW()')
    print('Database connected:', result)
asyncio.run(test())
"
```

### Portfolio ID Not Found

```bash
# Check portfolios table
python3 -c "
from database import database, init_database
import asyncio
async def test():
    await init_database()
    portfolios = await database.fetch_all('SELECT portfolio_id, name FROM portfolios')
    for p in portfolios:
        print(f'Portfolio: {p.portfolio_id} - {p.name}')
asyncio.run(test())
"
```

### Site Config Import Error

```bash
# Check if site_config.py exists and SiteConfigManager is available
python3 -c "
from site_config import SiteConfigManager
print('SiteConfigManager imported successfully')
"
```

### Rollback Migration

If you need to rollback:

```sql
-- Clear migrated data
DELETE FROM work_experience WHERE portfolio_id = '3fc521ad-660c-4067-b416-17dc388e66eb';
DELETE FROM projects WHERE portfolio_id = '3fc521ad-660c-4067-b416-17dc388e66eb';
DELETE FROM site_config WHERE description LIKE 'Migrated from HTML templates%';

-- Reset portfolio record to minimal data
UPDATE portfolios SET 
    name = NULL, title = NULL, bio = NULL, tagline = NULL,
    profile_image = NULL, email = NULL, phone = NULL,
    vcard = NULL, resume_url = NULL, resume_download = NULL,
    github = NULL, twitter = NULL, skills = NULL
WHERE portfolio_id = '3fc521ad-660c-4067-b416-17dc388e66eb';
```

## Post-Migration Benefits

After successful migration:

1. **Dynamic Content**: All portfolio content is now database-driven
2. **TTW Admin**: Full admin interface for managing content
3. **Multi-Portfolio Ready**: System supports multiple portfolios
4. **GraphQL API**: Clean API for frontend data consumption
5. **Site Configuration**: Centralized configuration management
6. **No Hardcoded Content**: Fully maintainable and scalable

## Next Steps

1. **Customize Content**: Use the admin interfaces to update your portfolio data
2. **Add More Projects**: Use the projects admin to add more work samples
3. **Configure Site Settings**: Use the TTW admin to customize site behavior
4. **Template Updates**: Gradually update templates to use dynamic data
5. **Additional Features**: Add new admin features as needed

---

**⚠️ Important**: Test the migration on a staging environment first if possible. Always backup your data before running migrations in production.
