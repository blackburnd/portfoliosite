#!/usr/bin/env python3

import re

# Read the file
with open('templates/index.html', 'r') as f:
    content = f.read()

# Remove edit-controls blocks using regex
# This pattern matches the entire edit-controls block including the surrounding if/endif
pattern = r'\s*{% if user_authenticated %}\s*<div class="edit-controls">.*?</div>\s*{% endif %}'
cleaned_content = re.sub(pattern, '', content, flags=re.DOTALL)

# Write back the cleaned content
with open('templates/index.html', 'w') as f:
    f.write(cleaned_content)

print("Removed all edit-controls blocks")
