# LinkedIn OAuth Setup Guide

## Step 1: Create LinkedIn App

1. Go to https://developer.linkedin.com/
2. Click "Create App"
3. Fill in:
   - **App name**: "Daniel Blackburn Portfolio Site"
   - **LinkedIn Page**: Create a LinkedIn page for your business/personal brand
   - **App logo**: Upload a professional logo
   - **Legal agreement**: Accept terms

## Step 2: Configure OAuth Settings

1. In your LinkedIn app dashboard, go to **Auth** tab
2. Add Authorized redirect URLs:
   - Production: `https://www.blackburnsystems.com/admin/linkedin/callback`
   - Development: `http://localhost:8000/admin/linkedin/callback`

## Step 3: Request Required Permissions

You need to request these permissions from LinkedIn:

### Basic Permissions (Usually auto-approved):
- **r_liteprofile**: Basic profile info (name, headline, location)
- **r_emailaddress**: Email address

### Advanced Permissions (Require approval):
- **r_fullprofile**: Full profile including work experience, education, skills
- **r_1st_degree_connections**: Access to connections (if needed)

## Step 4: Get Your Credentials

1. Copy your **Client ID** 
2. Copy your **Client Secret**
3. Keep these secure - you'll configure them through the LinkedIn admin interface

## Step 5: Configure OAuth App

After getting approved:
- Login as admin at `/auth/login`
- Go to LinkedIn admin interface at `/linkedin`
- Configure your LinkedIn OAuth app through the web interface
- No environment variables needed!

## What Data Will Be Synced

1. **Profile Information**:
   - Name, headline, location
   - Profile picture URL
   - Summary/bio

2. **Work Experience**:
   - Company names, positions, dates
   - Job descriptions
   - Company logos

3. **Skills & Endorsements**:
   - Skill names
   - Endorsement counts

4. **Education** (if r_fullprofile approved):
   - Schools, degrees, dates
   - Descriptions

All data will be stored in your local database and can be edited after import.
