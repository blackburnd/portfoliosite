#!/usr/bin/env python3
"""
Fix logs.js column mismatch issues.
This script fixes the JavaScript to match the 8-column template structure.
"""

def fix_logs_js():
    file_path = '/Users/danielblackburn/Documents/blackburnsystems/blackburnsystems/assets/js/logs.js'
    
    # Read the file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Fix 1: Change colspan from 9 to 8 for "No logs found"
    content = content.replace(
        'row.innerHTML = \'<td colspan="9" style="text-align: center; padding: 20px;">No logs found</td>\';',
        'row.innerHTML = \'<td colspan="8" style="text-align: center; padding: 20px;">No logs found</td>\';'
    )
    
    # Fix 2: Remove expand-col from updateDisplay function and move expand button to message column
    old_updateDisplay = '''        row.innerHTML = `
            <td class="expand-col">
                ${(log.message && (log.message.includes('\\n') || log.message.length > 100)) ? '<button class="expand-btn" onclick="toggleMessageExpand(this)">▶</button>' : ''}
            </td>
            <td class="log-timestamp">${dateStr}<br><small style="color: #666">${new Date(log.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'})}</small></td>
            <td class="log-age">${ageStr}</td>
            <td><span class="log-level log-level-${log.level || 'unknown'}">${escapeHtml(log.level || 'unknown')}</span></td>
            <td class="log-module">${escapeHtml(log.module || '')}</td>
            <td class="log-message">
                <div class="message-content">
                    <span class="message-text">${escapeHtml(log.message || '')}</span>
                    <button class="copy-btn" onclick="copyToClipboard('${escapeHtml(log.message || '').replace(/'/g, "\\\\"'")}', this)" title="Copy message to clipboard">
                        <span class="copy-icon">649</span>
                    </button>
                </div>
            </td>'''
    
    new_updateDisplay = '''        row.innerHTML = `
            <td class="log-timestamp">${dateStr}<br><small style="color: #666">${new Date(log.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'})}</small></td>
            <td class="log-age">${ageStr}</td>
            <td><span class="log-level log-level-${log.level || 'unknown'}">${escapeHtml(log.level || 'unknown')}</span></td>
            <td class="log-module">${escapeHtml(log.module || '')}</td>
            <td class="log-message">
                <div class="message-content">
                    ${(log.message && (log.message.includes('\\n') || log.message.length > 100)) ? '<button class="expand-btn" onclick="toggleMessageExpand(this)">▶</button>' : ''}
                    <span class="message-text">${escapeHtml(log.message || '')}</span>
                    <button class="copy-btn" onclick="copyToClipboard('${escapeHtml(log.message || '').replace(/'/g, "\\\\"'")}', this)" title="Copy message to clipboard">
                        <span class="copy-icon">📋</span>
                    </button>
                </div>
            </td>'''
    
    content = content.replace(old_updateDisplay, new_updateDisplay)
    
    # Fix 3: Remove expand-col from renderLogs function and move expand button to message column
    old_renderLogs = '''        row.innerHTML = `
            <td class="expand-col">
                ${(log.message && (log.message.includes('\\n') || log.message.length > 100)) ? '<button class="expand-btn" onclick="toggleMessageExpand(this)">▶</button>' : ''}
            </td>
            <td class="log-timestamp">${dateStr}<br><small style="color: #666">${timeStr}</small></td>
            <td class="log-age">${ageStr}</td>
            <td><span class="log-level log-level-${log.level || 'unknown'}">${escapeHtml(log.level || 'unknown')}</span></td>
            <td class="log-module">${escapeHtml(log.module || '')}</td>
            <td class="log-message">
                <div class="message-content">
                    <span class="message-text" data-full-message="${escapeHtml(log.message || '')}">${escapeHtml((log.message && log.message.length > 100) ? log.message.substring(0, 100) + '...' : (log.message || ''))}</span>
                    <button class="copy-btn" onclick="copyToClipboard('${escapeHtml(log.message || '').replace(/'/g, "\\\\"'")}', this)" title="Copy message to clipboard">
                        Copy
                    </button>
                </div>
            </td>'''
    
    new_renderLogs = '''        row.innerHTML = `
            <td class="log-timestamp">${dateStr}<br><small style="color: #666">${timeStr}</small></td>
            <td class="log-age">${ageStr}</td>
            <td><span class="log-level log-level-${log.level || 'unknown'}">${escapeHtml(log.level || 'unknown')}</span></td>
            <td class="log-module">${escapeHtml(log.module || '')}</td>
            <td class="log-message">
                <div class="message-content">
                    ${(log.message && (log.message.includes('\\n') || log.message.length > 100)) ? '<button class="expand-btn" onclick="toggleMessageExpand(this)">▶</button>' : ''}
                    <span class="message-text" data-full-message="${escapeHtml(log.message || '')}">${escapeHtml((log.message && log.message.length > 100) ? log.message.substring(0, 100) + '...' : (log.message || ''))}</span>
                    <button class="copy-btn" onclick="copyToClipboard('${escapeHtml(log.message || '').replace(/'/g, "\\\\"'")}', this)" title="Copy message to clipboard">
                        📋
                    </button>
                </div>
            </td>'''
    
    content = content.replace(old_renderLogs, new_renderLogs)
    
    # Write the fixed content back
    with open(file_path, 'w') as f:
        f.write(content)
    
    print("Successfully fixed logs.js column issues!")
    print("- Removed expand-col column from both functions")
    print("- Moved expand button into message column")
    print("- Fixed copy icons to use clipboard emoji")
    print("- Fixed colspan from 9 to 8")

if __name__ == '__main__':
    fix_logs_js()
