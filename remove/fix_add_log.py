#!/usr/bin/env python3
"""
Fix all add_log() calls in main.py to use the correct signature: (level, source, message)
"""

import re

def fix_add_log_calls():
    with open('/workspaces/portfoliosite/main.py', 'r') as f:
        content = f.read()
    
    # Pattern to find add_log calls with the wrong signature
    # Matches: add_log("event_type", f"message")
    pattern = r'add_log\("([^"]+)", f"([^"]+)"\)'
    
    def replace_func(match):
        event_type = match.group(1)
        message = match.group(2)
        
        # Determine appropriate log level based on event type
        if any(keyword in event_type.lower() for keyword in ['error', 'failure', 'failed']):
            level = 'ERROR'
        elif any(keyword in event_type.lower() for keyword in ['warning', 'warn']):
            level = 'WARNING'
        else:
            level = 'INFO'
        
        # Convert to correct format: add_log("LEVEL", "source", f"message")
        return f'add_log("{level}", "{event_type}", f"{message}")'
    
    # Apply the replacement
    new_content = re.sub(pattern, replace_func, content)
    
    # Write back to file
    with open('/workspaces/portfoliosite/main.py', 'w') as f:
        f.write(new_content)
    
    print("Fixed all add_log() calls in main.py")

if __name__ == "__main__":
    fix_add_log_calls()
