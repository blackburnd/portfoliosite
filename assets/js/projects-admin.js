// Projects Admin JavaScript using Dojo for CRUD operations
require([
    "dojo/ready",
    "dijit/Dialog",
    "dijit/form/Button",
    "dijit/form/TextBox",
    "dijit/form/Textarea",
    "dijit/form/NumberTextBox",
    "dojo/parser"
], function(ready, Dialog, Button, TextBox, Textarea, NumberTextBox, parser) {
    
    let projectDialog = null;
    let currentEditId = null;
    
    function createProjectDialog() {
        if (projectDialog) {
            projectDialog.destroyRecursive();
        }
        
        const dialogContent = `
            <div style="width: 580px;">
                <div class="form-row">
                    <div class="form-group">
                        <label for="title">Title *</label>
                        <input data-dojo-type="dijit/form/TextBox" 
                               id="title" 
                               name="title" 
                               placeholder="Project title"
                               required="true" />
                    </div>
                </div>
                
                <div class="form-row">
                    <div class="form-group">
                        <label for="description">Description *</label>
                        <textarea data-dojo-type="dijit/form/Textarea" 
                                  id="description" 
                                  name="description" 
                                  placeholder="Project description"
                                  rows="4"
                                  required="true"></textarea>
                    </div>
                </div>
                
                <div class="form-row">
                    <div class="form-group">
                        <label for="url">Project URL</label>
                        <input data-dojo-type="dijit/form/TextBox" 
                               id="url" 
                               name="url" 
                               placeholder="https://github.com/user/project" />
                    </div>
                    <div class="form-group">
                        <label for="image_url">Image URL</label>
                        <input data-dojo-type="dijit/form/TextBox" 
                               id="image_url" 
                               name="image_url" 
                               placeholder="https://example.com/image.jpg" />
                    </div>
                </div>
                
                <div class="form-row">
                    <div class="form-group">
                        <label for="technologies">Technologies</label>
                        <input data-dojo-type="dijit/form/TextBox" 
                               id="technologies" 
                               name="technologies" 
                               placeholder="Python, React, Node.js (comma-separated)" />
                        <span class="form-note">Enter technologies separated by commas</span>
                    </div>
                    <div class="form-group">
                        <label for="sort_order">Sort Order</label>
                        <input data-dojo-type="dijit/form/NumberTextBox" 
                               id="sort_order" 
                               name="sort_order" 
                               value="0"
                               constraints="{min:0,max:999}" />
                        <span class="form-note">Lower numbers appear first</span>
                    </div>
                </div>
                
                <div class="form-row screenshots-section" style="margin-top: 20px; border-top: 1px solid #e0e0e0; padding-top: 20px;">
                    <div class="form-group full-width" style="width: 100%;">
                        <label style="display: block; margin-bottom: 8px; font-weight: bold; color: #333;">Project Screenshots</label>
                        <div id="screenshotsContainer">
                            <div class="screenshots-list" id="screenshotsList" style="max-height: 300px; overflow-y: auto; border: 1px solid #e0e0e0; border-radius: 4px; padding: 10px; margin-bottom: 15px; background: #f9f9f9;">
                                <!-- Screenshots will be loaded here -->
                            </div>
                            <div class="screenshot-upload" style="text-align: center; padding: 15px; border: 2px dashed #ccc; border-radius: 4px; background: #fafafa;">
                                <input type="file" id="screenshotUpload" accept="image/png,image/jpeg,image/webp" multiple style="display: none;">
                                <button type="button" id="uploadScreenshotBtn" onclick="document.getElementById('screenshotUpload').click()" style="background: #007bff; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-size: 14px; margin-bottom: 8px;">
                                    Add Screenshot
                                </button>
                                <br>
                                <span class="form-note" style="font-size: 12px; color: #666; font-style: italic;">Upload PNG, JPEG, or WebP images (max 2MB each)</span>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="dijitDialogPaneActionBar">
                    <button data-dojo-type="dijit/form/Button" type="button" id="submitBtn" onclick="window.projectsAdmin.handleFormSubmit()">
                        Add Project
                    </button>
                    <button data-dojo-type="dijit/form/Button" type="button" onclick="window.projectsAdmin.hideDialog()">
                        Cancel
                    </button>
                </div>
            </div>
        `;
        
        projectDialog = new Dialog({
            title: "Add Project",
            content: dialogContent,
            style: "width: 600px;"
        });
        
        // Parse the Dojo widgets in the dialog after it's created
        require(["dojo/parser"], function(parser) {
            parser.parse(projectDialog.domNode);
        });
        
        // Force white background styling after dialog creation
        setTimeout(() => {
            const dialogNode = projectDialog.domNode;
            if (dialogNode) {
                // Force white background on the main dialog
                dialogNode.style.backgroundColor = 'white';
                dialogNode.style.backgroundImage = 'none';
                
                // Force white background on content area
                const contentArea = dialogNode.querySelector('.dijitDialogPaneContentArea');
                if (contentArea) {
                    contentArea.style.backgroundColor = 'white';
                    contentArea.style.backgroundImage = 'none';
                    contentArea.style.color = '#333';
                }
                
                // Force white background on all child elements
                const allElements = dialogNode.querySelectorAll('*');
                allElements.forEach(el => {
                    if (el.style.backgroundColor && el.style.backgroundColor.includes('171, 214, 255')) {
                        el.style.backgroundColor = 'white';
                    }
                    if (el.style.background && el.style.background.includes('#abd6ff')) {
                        el.style.background = 'white';
                    }
                });
            }
        }, 50);
    }
    
    function showAddDialog() {
        currentEditId = null;
        createProjectDialog();
        projectDialog.set("title", "Add Project");
        
        // Wait for widgets to be parsed before setting properties
        setTimeout(() => {
            dijit.byId("submitBtn").set("label", "Add Project");
            projectDialog.show();
            // Setup screenshot upload after dialog is shown
            setTimeout(setupScreenshotUpload, 200);
            // Force styling after showing
            forceDialogStyling();
        }, 100);
    }
    
    function editItem(id) {
        fetch('/projects/' + id)
            .then(response => {
                if (!response.ok) {
                    throw new Error('HTTP error! status: ' + response.status);
                }
                return response.json();
            })
            .then(item => {
                currentEditId = id;
                createProjectDialog();
                projectDialog.set("title", "Edit Project");
                
                // Wait for widgets to be parsed before setting properties and populating
                setTimeout(() => {
                    dijit.byId("submitBtn").set("label", "Update Project");
                    populateForm(item);
                    projectDialog.show();
                    // Setup screenshot upload after dialog is shown
                    setTimeout(setupScreenshotUpload, 200);
                    // Force styling after showing
                    forceDialogStyling();
                }, 100);
            })
            .catch(error => {
                console.error('Error fetching project:', error);
                showErrorMessage('Error loading project data: ' + error.message);
            });
    }
    
    function populateForm(item) {
        dijit.byId("title").set("value", item.title || "");
        dijit.byId("description").set("value", item.description || "");
        dijit.byId("url").set("value", item.url || "");
        dijit.byId("image_url").set("value", item.image_url || "");
        dijit.byId("sort_order").set("value", item.sort_order || 0);
        
        // Handle technologies array
        if (item.technologies && Array.isArray(item.technologies)) {
            dijit.byId("technologies").set("value", item.technologies.join(", "));
        } else {
            dijit.byId("technologies").set("value", "");
        }
        
        // Load screenshots for this project
        loadProjectScreenshots(item.title);
    }
    
    function loadProjectScreenshots(projectTitle) {
        const projectSlug = generateSlug(projectTitle);
        fetch(`/projects/screenshots/${projectSlug}`)
            .then(response => response.json())
            .then(screenshots => {
                displayScreenshots(screenshots, projectSlug);
            })
            .catch(error => {
                console.error('Error loading screenshots:', error);
                document.getElementById('screenshotsList').innerHTML = '<p>No screenshots found</p>';
            });
    }
    
    function generateSlug(title) {
        return title.toLowerCase()
            .replace(/\s+/g, '-')
            .replace(/&/g, 'and')
            .replace(/[^a-z0-9-]/g, '')
            .replace(/-+/g, '-')
            .replace(/^-|-$/g, '');
    }
    
    function displayScreenshots(screenshots, projectSlug) {
        const container = document.getElementById('screenshotsList');
        if (!screenshots || screenshots.length === 0) {
            container.innerHTML = '<p style="text-align: center; color: #666; font-style: italic; padding: 20px; margin: 0;">No screenshots uploaded yet</p>';
            return;
        }
        
        container.innerHTML = screenshots.map(screenshot => `
            <div style="display: flex; align-items: center; gap: 15px; padding: 10px; border: 1px solid #ddd; border-radius: 4px; margin-bottom: 10px; background: white;">
                <img src="/assets/screenshots/${projectSlug}/${screenshot.filename}" 
                     alt="${screenshot.filename}" 
                     style="width: 80px; height: 60px; object-fit: cover; border-radius: 4px; border: 1px solid #ccc;">
                <div style="flex: 1; display: flex; align-items: center; gap: 10px;">
                    <input type="text" value="${screenshot.name}" 
                           style="flex: 1; padding: 5px 8px; border: 1px solid #ccc; border-radius: 3px; font-size: 14px;"
                           onchange="updateScreenshotName('${projectSlug}', '${screenshot.filename}', this.value)">
                    <button type="button" onclick="deleteScreenshot('${projectSlug}', '${screenshot.filename}')" 
                            style="background: #dc3545; color: white; border: none; padding: 5px 10px; border-radius: 3px; cursor: pointer; font-size: 12px;">Delete</button>
                </div>
            </div>
        `).join('');
    }
    
    function setupScreenshotUpload() {
        const uploadInput = document.getElementById('screenshotUpload');
        if (uploadInput) {
            uploadInput.addEventListener('change', handleScreenshotUpload);
        }
    }
    
    function handleScreenshotUpload(event) {
        const files = event.target.files;
        if (!files || files.length === 0) return;
        
        const projectTitle = dijit.byId("title").get("value");
        if (!projectTitle) {
            alert('Please enter a project title first');
            return;
        }
        
        const projectSlug = generateSlug(projectTitle);
        
        for (let file of files) {
            if (file.size > 2 * 1024 * 1024) { // 2MB limit
                alert(`File ${file.name} is too large. Max size is 2MB.`);
                continue;
            }
            
            uploadScreenshotFile(file, projectSlug);
        }
        
        // Clear the input
        event.target.value = '';
    }
    
    function uploadScreenshotFile(file, projectSlug) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('project_slug', projectSlug);
        
        fetch('/projects/upload-screenshot', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                // Reload screenshots
                loadProjectScreenshots(dijit.byId("title").get("value"));
            } else {
                alert('Upload failed: ' + result.message);
            }
        })
        .catch(error => {
            console.error('Upload error:', error);
            alert('Upload failed: ' + error.message);
        });
    }
    
    function updateScreenshotName(projectSlug, filename, newName) {
        fetch('/projects/update-screenshot-name', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                project_slug: projectSlug,
                filename: filename,
                new_name: newName
            })
        })
        .then(response => response.json())
        .then(result => {
            if (!result.success) {
                alert('Failed to update name: ' + result.message);
                // Reload to reset the name
                loadProjectScreenshots(dijit.byId("title").get("value"));
            }
        })
        .catch(error => {
            console.error('Update error:', error);
            alert('Failed to update name: ' + error.message);
        });
    }
    
    function deleteScreenshot(projectSlug, filename) {
        if (!confirm(`Are you sure you want to delete ${filename}?`)) {
            return;
        }
        
        fetch('/projects/delete-screenshot', {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                project_slug: projectSlug,
                filename: filename
            })
        })
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                // Reload screenshots
                loadProjectScreenshots(dijit.byId("title").get("value"));
            } else {
                alert('Delete failed: ' + result.message);
            }
        })
        .catch(error => {
            console.error('Delete error:', error);
            alert('Delete failed: ' + error.message);
        });
    }
    
    function hideDialog() {
        if (projectDialog) {
            projectDialog.hide();
        }
    }
    
    function handleFormSubmit() {
        // Simple validation - only require title and description
        const title = dijit.byId("title").get("value");
        const description = dijit.byId("description").get("value");
        
        if (!title || !description) {
            showErrorMessage("Please enter both Title and Description.");
            return;
        }
        
        // Get form values
        const project = {
            portfolio_id: window.PORTFOLIO_ID, // This should always be set
            title: title,
            description: description
        };
        
        // Ensure portfolio_id is available
        if (!project.portfolio_id) {
            alert('Portfolio ID not found. Please refresh the page.');
            return;
        }

        // Add optional fields only if they have values
        const url = dijit.byId("url").get("value");
        if (url) project.url = url;

        const imageUrl = dijit.byId("image_url").get("value");
        if (imageUrl) project.image_url = imageUrl;

        const sortOrder = dijit.byId("sort_order").get("value");
        if (sortOrder) project.sort_order = parseInt(sortOrder);

        // Handle technologies
        const technologiesStr = dijit.byId("technologies").get("value");
        if (technologiesStr) {
            project.technologies = technologiesStr.split(',').map(tech => tech.trim()).filter(tech => tech.length > 0);
        }
        
        const isEdit = currentEditId !== null;
        const url_endpoint = isEdit ? '/projects/' + currentEditId : '/projects';
        const method = isEdit ? 'PUT' : 'POST';
        
        dijit.byId("submitBtn").set("disabled", true);
        dijit.byId("submitBtn").set("label", isEdit ? "Updating..." : "Adding...");
        
        fetch(url_endpoint, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(project)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('HTTP error! status: ' + response.status);
            }
            return response.json();
        })
        .then(response => {
            console.log((isEdit ? 'Updated' : 'Added') + ' project:', response);
            loadGrid();
            projectDialog.hide();
            showSuccessMessage('Project ' + (isEdit ? 'updated' : 'added') + ' successfully!');
        })
        .catch(error => {
            console.error('Error ' + (isEdit ? 'updating' : 'adding') + ' project:', error);
            showErrorMessage('Error ' + (isEdit ? 'updating' : 'adding') + ' project: ' + error.message);
        })
        .finally(() => {
            dijit.byId("submitBtn").set("disabled", false);
            dijit.byId("submitBtn").set("label", isEdit ? "Update Project" : "Add Project");
        });
    }
    
    function loadGrid() {
        document.getElementById('grid').innerHTML = '<div class="loading">Loading projects...</div>';
        
        fetch('/projects')
            .then(response => {
                if (!response.ok) {
                    throw new Error('HTTP error! status: ' + response.status);
                }
                return response.json();
            })
            .then(data => {
                console.log("Loaded projects:", data);
                let gridHtml = '<table class="projects-table">' +
                    '<thead><tr>' +
                    '<th>Select</th><th>Title</th><th>Description</th><th>URL</th>' +
                    '<th>Technologies</th><th>Sort Order</th><th>Actions</th></tr></thead><tbody>';
                
                if (data && data.length > 0) {
                    data.forEach(item => {
                        const technologies = Array.isArray(item.technologies) ? item.technologies.join(', ') : '';
                        const url = item.url ? `<a href="${item.url}" target="_blank">View</a>` : '';
                        
                        gridHtml += `<tr data-id="${item.id}">
                            <td><input type="checkbox" class="select-row"></td>
                            <td>${item.title || ''}</td>
                            <td>${(item.description || '').substring(0, 100)}${item.description && item.description.length > 100 ? '...' : ''}</td>
                            <td>${url}</td>
                            <td>${technologies}</td>
                            <td>${item.sort_order || 0}</td>
                            <td>
                                <button onclick="window.projectsAdmin.editItem('${item.id}')">Edit</button>
                            </td>
                        </tr>`;
                    });
                } else {
                    gridHtml += '<tr><td colspan="7">No projects found</td></tr>';
                }
                
                gridHtml += '</tbody></table>';
                document.getElementById('grid').innerHTML = gridHtml;
            })
            .catch(error => {
                console.error('Error loading projects:', error);
                document.getElementById('grid').innerHTML = '<div class="error">Error loading projects: ' + error.message + '</div>';
            });
    }
    
    function deleteSelected() {
        const selected = document.querySelectorAll('.select-row:checked');
        if (selected.length === 0) {
            showErrorMessage('Please select projects to delete.');
            return;
        }
        
        if (!confirm(`Are you sure you want to delete ${selected.length} project(s)?`)) {
            return;
        }
        
        const deletePromises = [];
        selected.forEach(checkbox => {
            const row = checkbox.closest('tr');
            const id = row.dataset.id;
            deletePromises.push(
                fetch('/projects/' + id, { method: 'DELETE' })
                    .then(response => {
                        if (!response.ok) {
                            throw new Error('HTTP error! status: ' + response.status);
                        }
                        return response.json();
                    })
            );
        });
        
        Promise.all(deletePromises)
            .then(() => {
                loadGrid();
                showSuccessMessage('Projects deleted successfully!');
            })
            .catch(error => {
                console.error('Error deleting projects:', error);
                showErrorMessage('Error deleting projects: ' + error.message);
                loadGrid(); // Refresh to show current state
            });
    }
    
    // Initialize when page loads
    ready(function() {
        loadGrid();
        
        // Bind event handlers
        const addBtn = document.getElementById('addBtn');
        if (addBtn) {
            addBtn.addEventListener('click', showAddDialog);
        }
        
        const deleteBtn = document.getElementById('deleteBtn');
        if (deleteBtn) {
            deleteBtn.addEventListener('click', deleteSelected);
        }
    });
    
    // Status message utility functions
    function showStatusMessage(message, type = 'info', duration = 5000) {
        const container = document.getElementById('statusMessages');
        if (!container) return;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `status-message ${type}`;
        messageDiv.innerHTML = `
            ${message}
            <button class="close-btn" onclick="this.parentElement.remove()" aria-label="Close message">&times;</button>
        `;
        
        container.appendChild(messageDiv);
        
        // Auto-remove after specified duration
        if (duration > 0) {
            setTimeout(() => {
                if (messageDiv.parentElement) {
                    messageDiv.classList.add('fade-out');
                    setTimeout(() => {
                        if (messageDiv.parentElement) {
                            messageDiv.remove();
                        }
                    }, 300);
                }
            }, duration);
        }
    }
    
    function showSuccessMessage(message, duration = 4000) {
        showStatusMessage(message, 'success', duration);
    }
    
    function showErrorMessage(message, duration = 0) {
        showStatusMessage(message, 'error', duration);
    }
    
    function showInfoMessage(message, duration = 5000) {
        showStatusMessage(message, 'info', duration);
    }
    
    // Function to force proper dialog styling
    function forceDialogStyling() {
        if (!projectDialog || !projectDialog.domNode) return;
        
        const dialogNode = projectDialog.domNode;
        
        // Force white background on the main dialog
        dialogNode.style.setProperty('background-color', 'white', 'important');
        dialogNode.style.setProperty('background-image', 'none', 'important');
        dialogNode.style.setProperty('background', 'white', 'important');
        
        // Force white background on content area
        const contentArea = dialogNode.querySelector('.dijitDialogPaneContentArea');
        if (contentArea) {
            contentArea.style.setProperty('background-color', 'white', 'important');
            contentArea.style.setProperty('background-image', 'none', 'important');
            contentArea.style.setProperty('background', 'white', 'important');
            contentArea.style.setProperty('color', '#333', 'important');
            contentArea.style.setProperty('padding', '20px', 'important');
        }
        
        // Force styling on title bar
        const titleBar = dialogNode.querySelector('.dijitDialogTitleBar');
        if (titleBar) {
            titleBar.style.setProperty('background-color', '#f8f9fa', 'important');
            titleBar.style.setProperty('background-image', 'none', 'important');
            titleBar.style.setProperty('background', '#f8f9fa', 'important');
            titleBar.style.setProperty('color', '#333', 'important');
        }
        
        // Style form elements
        const formRows = dialogNode.querySelectorAll('.form-row');
        formRows.forEach(row => {
            row.style.setProperty('display', 'flex', 'important');
            row.style.setProperty('gap', '15px', 'important');
            row.style.setProperty('margin-bottom', '15px', 'important');
        });
        
        const formGroups = dialogNode.querySelectorAll('.form-group');
        formGroups.forEach(group => {
            group.style.setProperty('flex', '1', 'important');
            group.style.setProperty('display', 'flex', 'important');
            group.style.setProperty('flex-direction', 'column', 'important');
        });
        
        const labels = dialogNode.querySelectorAll('label');
        labels.forEach(label => {
            label.style.setProperty('margin-bottom', '5px', 'important');
            label.style.setProperty('font-weight', 'bold', 'important');
            label.style.setProperty('color', '#333', 'important');
            label.style.setProperty('display', 'block', 'important');
        });
        
        const inputs = dialogNode.querySelectorAll('input, textarea');
        inputs.forEach(input => {
            input.style.setProperty('padding', '8px', 'important');
            input.style.setProperty('border', '1px solid #ccc', 'important');
            input.style.setProperty('border-radius', '4px', 'important');
            input.style.setProperty('background', 'white', 'important');
            input.style.setProperty('color', '#333', 'important');
        });
        
        const buttons = dialogNode.querySelectorAll('button');
        buttons.forEach(button => {
            if (button.textContent.includes('Add Project') || button.textContent.includes('Update Project')) {
                button.style.setProperty('background', '#007bff', 'important');
                button.style.setProperty('color', 'white', 'important');
                button.style.setProperty('border', 'none', 'important');
                button.style.setProperty('padding', '10px 20px', 'important');
                button.style.setProperty('border-radius', '4px', 'important');
                button.style.setProperty('cursor', 'pointer', 'important');
            } else if (button.textContent.includes('Cancel')) {
                button.style.setProperty('background', '#6c757d', 'important');
                button.style.setProperty('color', 'white', 'important');
                button.style.setProperty('border', 'none', 'important');
                button.style.setProperty('padding', '10px 20px', 'important');
                button.style.setProperty('border-radius', '4px', 'important');
                button.style.setProperty('cursor', 'pointer', 'important');
            }
        });
        
        // Force white background on all elements that might have blue
        const allElements = dialogNode.querySelectorAll('*');
        allElements.forEach(el => {
            const computedStyle = window.getComputedStyle(el);
            const bgColor = computedStyle.backgroundColor;
            
            // Check for the specific blue color and override it
            if (bgColor === 'rgb(171, 214, 255)' || bgColor === '#abd6ff') {
                el.style.setProperty('background-color', 'white', 'important');
                el.style.setProperty('background-image', 'none', 'important');
                el.style.setProperty('background', 'white', 'important');
            }
        });
        
        // Also check for inline styles
        allElements.forEach(el => {
            if (el.style.backgroundColor && el.style.backgroundColor.includes('171, 214, 255')) {
                el.style.setProperty('background-color', 'white', 'important');
            }
            if (el.style.background && el.style.background.includes('#abd6ff')) {
                el.style.setProperty('background', 'white', 'important');
            }
        });
    }
    
    // Export functions to global scope
    window.projectsAdmin = {
        showAddDialog: showAddDialog,
        editItem: editItem,
        deleteSelected: deleteSelected,
        handleFormSubmit: handleFormSubmit,
        hideDialog: hideDialog,
        loadGrid: loadGrid
    };
});
