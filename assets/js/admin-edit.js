/**
 * Inline content editing functionality for admin users
 * Handles click-to-edit functionality for content management
 */

let originalContent = {};

// Initialize editing functionality when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    const editableElements = document.querySelectorAll('.editable-content');
    
    // Add click-to-edit functionality to each editable element
    editableElements.forEach(element => {
        element.addEventListener('click', function(e) {
            // Don't start editing if already editing or if clicking on controls
            if (element.classList.contains('editing') || e.target.closest('.edit-controls')) {
                return;
            }
            startEdit(element);
        });
        
        // Add hover cursor styling
        element.style.cursor = 'pointer';
    });
});

function startEdit(element) {
    const configKey = element.getAttribute('data-config-key');
    
    // Get current text content directly from the element (excluding any existing controls)
    const clone = element.cloneNode(true);
    const existingControls = clone.querySelector('.edit-controls');
    if (existingControls) {
        existingControls.remove();
    }
    const currentText = clone.textContent.trim();
    
    // Store original content for canceling
    originalContent[configKey] = currentText;
    
    // Add editing class
    element.classList.add('editing');
    
    // Create editing interface directly
    let editingHTML;
    if (element.tagName.toLowerCase() === 'p') {
        editingHTML = `
            <textarea class="content-textarea">${currentText}</textarea>
            <div class="edit-controls">
                <button class="edit-btn save-btn" onclick="saveContent(this)">Save</button>
                <button class="edit-btn cancel-btn" onclick="cancelEdit(this)">Cancel</button>
            </div>`;
    } else {
        editingHTML = `
            <input type="text" class="content-input" value="${currentText}">
            <div class="edit-controls">
                <button class="edit-btn save-btn" onclick="saveContent(this)">Save</button>
                <button class="edit-btn cancel-btn" onclick="cancelEdit(this)">Cancel</button>
            </div>`;
    }
    
    element.innerHTML = editingHTML;
    
    // Focus the input
    const input = element.querySelector('.content-input, .content-textarea');
    if (input) {
        input.focus();
        input.select();
        
        // Add keyboard event listeners
        input.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                const saveBtn = element.querySelector('.save-btn');
                if (saveBtn) saveContent(saveBtn);
            } else if (e.key === 'Escape') {
                const cancelBtn = element.querySelector('.cancel-btn');
                if (cancelBtn) cancelEdit(cancelBtn);
            }
        });
    }
}

async function saveContent(button) {
    const element = button.closest('.editable-content');
    if (!element) {
        console.error('Could not find editable element for button:', button);
        return;
    }
    
    const configKey = element.getAttribute('data-config-key');
    const input = element.querySelector('input, textarea');
    const newValue = input.value.trim();
    
    if (!newValue) {
        alert('Content cannot be empty');
        return;
    }
    
    // Show saving state
    button.textContent = 'Saving...';
    button.disabled = true;
    
    try {
        const response = await fetch('/admin/update-content', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                key: configKey,
                value: newValue
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Update the display content
            element.classList.remove('editing');
            
            // Restore content with proper formatting
            if (element.tagName.toLowerCase().startsWith('h')) {
                element.innerHTML = newValue;
            } else if (configKey === 'home_hero_tagline') {
                element.innerHTML = '<em>' + newValue + '</em>';
            } else {
                element.innerHTML = newValue;
            }
            
            // Show success feedback
            showFeedback('Content updated successfully!', 'success');
        } else {
            throw new Error(result.message);
        }
    } catch (error) {
        console.error('Save failed:', error);
        showFeedback('Failed to save: ' + error.message, 'error');
        
        // Restore original content on error
        cancelEdit(button.parentElement.querySelector('.cancel-btn'));
    } finally {
        button.textContent = 'Save';
        button.disabled = false;
    }
}

function cancelEdit(button) {
    const element = button.closest('.editable-content');
    if (!element) {
        console.error('Could not find editable element for button:', button);
        return;
    }
    
    const configKey = element.getAttribute('data-config-key');
    const originalText = originalContent[configKey];
    
    // Remove editing class
    element.classList.remove('editing');
    
    // Restore original content
    if (element.tagName.toLowerCase().startsWith('h')) {
        element.innerHTML = originalText;
    } else if (configKey === 'home_hero_tagline') {
        element.innerHTML = '<em>' + originalText + '</em>';
    } else {
        element.innerHTML = originalText;
    }
}

function showFeedback(message, type) {
    // Create feedback element
    const feedback = document.createElement('div');
    feedback.className = `feedback-message ${type}`;
    feedback.textContent = message;
    
    document.body.appendChild(feedback);
    
    // Animate in
    setTimeout(() => {
        feedback.classList.add('show');
    }, 100);
    
    // Remove after 3 seconds
    setTimeout(() => {
        feedback.classList.remove('show');
        setTimeout(() => {
            if (document.body.contains(feedback)) {
                document.body.removeChild(feedback);
            }
        }, 300);
    }, 3000);
}