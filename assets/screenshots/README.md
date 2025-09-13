# Screenshots Directory

This directory contains screenshots for portfolio showcase pages.

## Structure

```
screenshots/
├── portfoliosite/
│   ├── sql-admin-interface.png      - SQL admin with ERD generation
│   ├── google-oauth-config.png      - OAuth configuration interface
│   └── logs-admin-grid.png          - Logs administration with filtering
└── pypgsvg/
    ├── generated-erd-diagram.png    - Complex database ERD output
    ├── interactive-hover-demo.png   - SVG with hover effects active
    └── command-line-execution.png   - Terminal showing pypgsvg usage
```

## Guidelines

- **Format**: PNG (lossless, good for UI screenshots)
- **Resolution**: 1920x1080 or higher for crisp display
- **File Size**: Optimize for web (aim for <500KB per image)
- **Content**: Include browser chrome/window borders for context
- **Focus**: Highlight the specific feature being demonstrated

## Usage in Templates

Screenshots are referenced in showcase templates using relative paths:
```html
<img src="/assets/screenshots/{project}/{filename}.png" alt="Description">
```

Replace placeholder files with actual screenshots maintaining the same filename structure.