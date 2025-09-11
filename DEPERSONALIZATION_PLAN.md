# Portfolio Platform De-Personalization Plan

## 🎯 **Objective**
Transform the current personal portfolio into a generic, configurable platform that anyone can use by removing all hardcoded personal information and making site content configurable through environment variables and database settings.

## 📋 **Current Hardcoded Elements Found**

### **Personal Information**
- Name: "Daniel Blackburn" / "Daniel" / "Blackburn"
- Email: daniel@blackburn.dev
- Company: "Blackburn Systems"
- Resume filename: danielblackburn.pdf
- Image paths: daniel-blackburn.jpg, daniel2.png
- Social handles: @blackburnd, @danielblackburn

### **Site Content**
- Page titles and meta descriptions
- Hero section text and taglines
- About section paragraphs
- Company branding throughout
- OAuth success messages
- Copyright notices
- Service descriptions

### **File Locations**
- `main.py` - Site title and descriptions
- `app/routers/work.py` - Page titles, resume paths
- `app/routers/projects.py` - Page titles, hardcoded portfolio references
- `app/routers/oauth.py` - Success messages, company references
- `templates/*.html` - All template content
- `assets/js/*.js` - Fallback portfolio IDs
- `portfolio.service` - Service description and user
- `sql/schema.sql` - Sample data

## 🏗️ **Implementation Strategy**

### **Phase 1: Database Schema ✅ READY**
- [x] Created `site_config` table for configurable values
- [x] Created `SiteConfigManager` class for config management
- [x] Created `TemplateContextProcessor` for template injection
- [x] Created migration script `migrate_site_config.py`

### **Phase 2: Template Updates** 
- [ ] Update `base.html` to use configurable site title
- [ ] Update `index.html` to use configurable hero content
- [ ] Update admin templates to use configurable titles
- [ ] Update navigation to use configurable company name
- [ ] Update footer copyright to use configurable name

### **Phase 3: Route Updates**
- [ ] Update all route handlers to use `create_template_context()`
- [ ] Remove hardcoded titles and descriptions
- [ ] Make resume filename dynamic
- [ ] Update OAuth messages to use configuration

### **Phase 4: Asset Management**
- [ ] Create generic asset naming convention
- [ ] Make profile image path configurable
- [ ] Update image alt text to be configurable
- [ ] Create asset upload/management system

### **Phase 5: Environment Configuration**
- [ ] Add environment variable support for all config
- [ ] Create `.env.example` with all configurable values
- [ ] Update documentation for setup
- [ ] Create configuration admin interface

## 🔧 **Configuration Categories**

### **Site Branding**
```
SITE_TITLE=Professional Portfolio
SITE_TAGLINE=Building Better Solutions Through Experience
COMPANY_NAME=Portfolio Systems
COPYRIGHT_NAME=Portfolio Owner
```

### **Page Content**
```
HERO_HEADING=Building Better Solutions Through Experience
HERO_DESCRIPTION=Your professional journey description...
ABOUT_HEADING=About Me
FOCUS_HEADING=Current Focus
```

### **File Assets**
```
PROFILE_IMAGE_PATH=/assets/files/profile.png
PROFILE_IMAGE_ALT=Professional headshot
RESUME_FILENAME=resume.pdf
```

### **System Configuration**
```
SERVICE_DESCRIPTION=Professional Portfolio FastAPI Application
SERVICE_USER=portfolio
OAUTH_SUCCESS_MESSAGE=You have successfully logged in
```

## 📁 **New Files Created**

1. **`sql/site_configuration_schema.sql`** - Database schema for configuration
2. **`site_config.py`** - Configuration manager class
3. **`template_context.py`** - Template context processor
4. **`migrate_site_config.py`** - Migration script

## 🚀 **Next Steps**

1. **Run Migration**: Apply database schema changes
2. **Update Templates**: Replace hardcoded content with template variables
3. **Update Routes**: Use new template context system
4. **Test Configuration**: Verify all content is configurable
5. **Create Admin Interface**: Build UI for managing site configuration
6. **Documentation**: Update setup instructions

## 💡 **Benefits After Implementation**

- ✅ **Fully Generic**: No hardcoded personal information
- ✅ **Easy Setup**: New users just configure environment variables
- ✅ **Database Driven**: All content manageable through admin interface
- ✅ **Maintainable**: Centralized configuration management
- ✅ **Scalable**: Supports multiple portfolios with different branding
- ✅ **Professional**: Clean, configurable platform ready for any user

## 🔄 **Migration Path**

For existing installations:
1. Run `python migrate_site_config.py` to add configuration table
2. Deploy updated code with new template system
3. Customize configuration through admin interface or environment variables
4. Replace personal assets (images, resume) with generic ones

This transformation will make the portfolio platform truly reusable while maintaining all existing functionality!
