// Projects Admin JavaScript using Dojo for CRUD operations
console.log('Projects Admin JS Loading...');

// Check if Dojo is available
if (typeof require === 'undefined' || typeof dojo === 'undefined') {
    console.error('Dojo is not loaded! Falling back to native dialog');
    // Fallback to native implementation
    initWithoutDojo();
} else {
    console.log('Dojo detected, initializing...');
    
    require([
        "dojo/ready",
        "dijit/Dialog", 
        "dijit/form/Button",
        "dijit/form/TextBox",
        "dijit/form/Textarea",
        "dijit/form/NumberTextBox",
        "dojo/parser"
    ], function(ready, Dialog, Button, TextBox, Textarea, NumberTextBox, parser) {
        console.log('Dojo modules loaded successfully');
        initWithDojo(ready, Dialog, Button, TextBox, Textarea, NumberTextBox, parser);
    }, function(error) {
        console.error('Error loading Dojo modules:', error);
        initWithoutDojo();
    });
}

function initWithDojo(ready, Dialog, Button, TextBox, Textarea, NumberTextBox, parser) {
    
    let projectDialog = null;
    let currentEditId = null;
    
    function createProjectDialog() {
        if (projectDialog) {
            projectDialog.destroyRecursive();
        }
        
        const dialogContent = `
            <style>
                /* Inline CSS for Dialog - Ensures styling regardless of external CSS loading */
                .dijitDialogPaneContentArea {
                    padding: 20px !important;
                    background: white !important;
                    color: #333 !important;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
                }
                .form-row {
                    display: flex !important;
                    gap: 15px !important;
                    margin-bottom: 15px !important;
                    align-items: flex-start !important;
                }
                .form-group {
                    flex: 1 !important;
                    display: flex !important;
                    flex-direction: column !important;
                }
                .form-group.full-width {
                    width: 100% !important;
                    flex: none !important;
                }
                .form-group label {
                    display: block !important;
                    margin-bottom: 5px !important;
                    font-weight: 600 !important;
                    color: #333 !important;
                    font-size: 14px !important;
                }
                .form-group input,
                .form-group textarea {
                    width: 100% !important;
                    box-sizing: border-box !important;
                    border: 1px solid #ccc !important;
                    padding: 8px 12px !important;
                    border-radius: 4px !important;
                    background: white !important;
                    color: #333 !important;
                    font-size: 14px !important;
                    font-family: inherit !important;
                }
                .form-group input:focus,
                .form-group textarea:focus {
                    border-color: #666 !important;
                    outline: none !important;
                    box-shadow: 0 0 0 2px rgba(102, 102, 102, 0.1) !important;
                }
                .form-note {
                    display: block !important;
                    font-size: 12px !important;
                    color: #666 !important;
                    margin-top: 4px !important;
                    font-style: italic !important;
                }
                .screenshots-section {
                    margin-top: 20px !important;
                    border-top: 1px solid #e0e0e0 !important;
                    padding-top: 20px !important;
                }
                .screenshots-list {
                    max-height: 300px !important;
                    overflow-y: auto !important;
                    border: 1px solid #e0e0e0 !important;
                    border-radius: 4px !important;
                    padding: 10px !important;
                    margin-bottom: 15px !important;
                    background: #f9f9f9 !important;
                }
                .screenshot-upload {
                    text-align: center !important;
                    padding: 15px !important;
                    border: 2px dashed #ccc !important;
                    border-radius: 4px !important;
                    background: #fafafa !important;
                }
                .screenshot-item {
                    display: flex !important;
                    align-items: center !important;
                    gap: 10px !important;
                    padding: 8px !important;
                    border: 1px solid #ddd !important;
                    border-radius: 4px !important;
                    margin-bottom: 8px !important;
                    background: white !important;
                }
                .screenshot-item img {
                    width: 60px !important;
                    height: 40px !important;
                    object-fit: cover !important;
                    border-radius: 4px !important;
                    border: 1px solid #ddd !important;
                }
                .screenshot-info {
                    flex: 1 !important;
                    display: flex !important;
                    flex-direction: column !important;
                    gap: 4px !important;
                }
                .screenshot-name {
                    font-weight: 600 !important;
                    color: #333 !important;
                    font-size: 14px !important;
                }
                .screenshot-filename {
                    font-size: 12px !important;
                    color: #666 !important;
                    font-style: italic !important;
                }
                .screenshot-actions {
                    display: flex !important;
                    gap: 5px !important;
                }
                .screenshot-actions button {
                    padding: 4px 8px !important;
                    font-size: 12px !important;
                    border: none !important;
                    border-radius: 3px !important;
                    cursor: pointer !important;
                }
                .screenshot-actions button.rename-btn {
                    background: #007bff !important;
                    color: white !important;
                }
                .screenshot-actions button.delete-btn {
                    background: #dc3545 !important;
                    color: white !important;
                }
                .screenshot-actions button:hover {
                    opacity: 0.8 !important;
                }
                .dijitDialogPaneActionBar {
                    padding: 15px 20px !important;
                    background-color: #f8f9fa !important;
                    border-top: 1px solid #dee2e6 !important;
                    text-align: right !important;
                }
                .dijitDialogPaneActionBar button {
                    margin-left: 10px !important;
                    background: #007bff !important;
                    color: white !important;
                    border: 1px solid #007bff !important;
                    padding: 8px 16px !important;
                    border-radius: 4px !important;
                    cursor: pointer !important;
                    font-size: 14px !important;
                }
                .dijitDialogPaneActionBar button:hover {
                    background: #0056b3 !important;
                    border-color: #0056b3 !important;
                }
                .dijitDialogPaneActionBar button[onclick*="hideDialog"] {
                    background: #6c757d !important;
                    border-color: #6c757d !important;
                }
                .dijitDialogPaneActionBar button[onclick*="hideDialog"]:hover {
                    background: #5a6268 !important;
                    border-color: #5a6268 !important;
                }
                @media (max-width: 768px) {
                    .form-row {
                        flex-direction: column !important;
                        gap: 0 !important;
                    }
                    .form-group {
                        margin-bottom: 15px !important;
                    }
                }
            </style>
            <div style="width: 580px; max-width: 90vw;">
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
            style: "width: 600px; max-width: 90vw;"
        });
        
        // Parse the Dojo widgets in the dialog after it's created
        require(["dojo/parser"], function(parser) {
            parser.parse(projectDialog.domNode);
        });
        
        // Enhanced styling application with multiple attempts
        const applyDialogStyling = () => {
            const dialogNode = projectDialog.domNode;
            if (dialogNode) {
                // Force comprehensive styling on the main dialog
                dialogNode.style.cssText += 'background-color: white !important; background-image: none !important; border-radius: 8px !important; box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important; border: 1px solid #dee2e6 !important;';
                
                // Style the title bar
                const titleBar = dialogNode.querySelector('.dijitDialogTitleBar');
                if (titleBar) {
                    titleBar.style.cssText += 'background-color: white !important; background-image: none !important; border-bottom: 1px solid #dee2e6 !important; padding: 15px 20px !important; color: #333 !important; font-weight: 600 !important;';
                }
                
                // Style the content area
                const contentArea = dialogNode.querySelector('.dijitDialogPaneContentArea');
                if (contentArea) {
                    contentArea.style.cssText += 'background-color: white !important; background-image: none !important; color: #333 !important; padding: 20px !important;';
                }
                
                // Style the action bar
                const actionBar = dialogNode.querySelector('.dijitDialogPaneActionBar');
                if (actionBar) {
                    actionBar.style.cssText += 'background-color: #f8f9fa !important; background-image: none !important; border-top: 1px solid #dee2e6 !important; padding: 15px 20px !important;';
                }
                
                // Style form elements
                const inputs = dialogNode.querySelectorAll('input, textarea, select');
                inputs.forEach(input => {
                    input.style.cssText += 'border: 1px solid #ccc !important; padding: 8px 12px !important; border-radius: 4px !important; background-color: white !important; color: #333 !important; font-size: 14px !important; width: 100% !important; box-sizing: border-box !important;';
                });
                
                // Style labels
                const labels = dialogNode.querySelectorAll('label');
                labels.forEach(label => {
                    label.style.cssText += 'display: block !important; margin-bottom: 5px !important; font-weight: 600 !important; color: #333 !important; font-size: 14px !important;';
                });
                
                // Remove any blue backgrounds
                const allElements = dialogNode.querySelectorAll('*');
                allElements.forEach(el => {
                    if (el.style.backgroundColor && (el.style.backgroundColor.includes('171, 214, 255') || el.style.backgroundColor.includes('#abd6ff'))) {
                        el.style.backgroundColor = 'white';
                    }
                    if (el.style.background && el.style.background.includes('#abd6ff')) {
                        el.style.background = 'white';
                    }
                });
            }
        };
        
        // Apply styling immediately and after delays
        setTimeout(applyDialogStyling, 10);
        setTimeout(applyDialogStyling, 50);
        setTimeout(applyDialogStyling, 100);
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
                    <div style="flex: 1; display: flex; flex-direction: column; gap: 4px;">
                        <input type="text" value="${screenshot.name}" 
                               style="flex: 1; padding: 5px 8px; border: 1px solid #ccc; border-radius: 3px; font-size: 14px;"
                               onchange="updateScreenshotName('${projectSlug}', '${screenshot.filename}', this.value)"
                               onkeypress="if(event.key==='Enter') updateScreenshotName('${projectSlug}', '${screenshot.filename}', this.value)"
                               placeholder="Enter display name">
                        <small style="color: #666; font-size: 11px;">File: ${screenshot.filename}</small>
                    </div>
                    <button type="button" onclick="deleteScreenshot('${projectSlug}', '${screenshot.filename}')" 
                            style="background: #dc3545; color: white; border: none; padding: 5px 10px; border-radius: 3px; cursor: pointer; font-size: 12px;"
                            title="Delete ${screenshot.filename}">Delete</button>
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
        if (!newName || newName.trim() === '') {
            alert('Please enter a valid name');
            // Reload to reset the name
            loadProjectScreenshots(dijit.byId("title").get("value"));
            return;
        }
        
        // Show visual feedback
        const inputElement = event?.target;
        if (inputElement) {
            inputElement.style.backgroundColor = '#fff3cd';
            inputElement.disabled = true;
        }
        
        fetch('/projects/update-screenshot-name', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                project_slug: projectSlug,
                filename: filename,
                new_name: newName.trim()
            })
        })
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                // Show success feedback
                if (inputElement) {
                    inputElement.style.backgroundColor = '#d4edda';
                    setTimeout(() => {
                        inputElement.style.backgroundColor = '';
                        inputElement.disabled = false;
                    }, 1000);
                }
                // Reload screenshots to show new filename
                loadProjectScreenshots(dijit.byId("title").get("value"));
            } else {
                alert('Failed to update name: ' + result.message);
                // Reload to reset the name
                loadProjectScreenshots(dijit.byId("title").get("value"));
            }
        })
        .catch(error => {
            console.error('Update error:', error);
            alert('Failed to update name: ' + error.message);
            // Reload to reset the name
            loadProjectScreenshots(dijit.byId("title").get("value"));
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
}

// Fallback implementation without Dojo
function initWithoutDojo() {
    console.log('Initializing without Dojo...');
    
    let currentEditId = null;
    
    function showAddDialog() {
        createNativeDialog();
    }
    
    function editItem(id) {
        currentEditId = id;
        fetch(`/projects/${id}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(item => {
                createNativeDialog(item);
            })
            .catch(error => {
                console.error('Error fetching project:', error);
                alert('Error loading project data: ' + error.message);
            });
    }
    
    function createNativeDialog(item = null) {
        // Remove any existing dialog
        const existingDialog = document.getElementById('nativeProjectDialog');
        if (existingDialog) {
            existingDialog.remove();
        }
        
        // Create modal overlay
        const overlay = document.createElement('div');
        overlay.id = 'nativeProjectDialog';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 9999;
        `;
        
        // Create dialog content
        const dialog = document.createElement('div');
        dialog.style.cssText = `
            background: white;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            max-width: 800px;
            width: 90vw;
            max-height: 90vh;
            overflow-y: auto;
        `;
        
        const isEdit = item !== null;
        
        dialog.innerHTML = `
            <div style="background: white; border-bottom: 1px solid #dee2e6; padding: 15px 20px; color: #333; font-weight: 600; font-size: 18px;">
                ${isEdit ? 'Edit Project' : 'Add Project'}
                <button onclick="hideNativeDialog()" style="float: right; background: none; border: none; font-size: 20px; cursor: pointer;">&times;</button>
            </div>
            <div style="padding: 20px; background: white;">
                <form id="nativeProjectForm">
                    <div style="margin-bottom: 15px;">
                        <label style="display: block; margin-bottom: 5px; font-weight: 600; color: #333; font-size: 14px;">Title *</label>
                        <input type="text" id="nativeTitle" name="title" required 
                               style="width: 100%; box-sizing: border-box; border: 1px solid #ccc; padding: 8px 12px; border-radius: 4px; background: white; color: #333; font-size: 14px;"
                               value="${item?.title || ''}" />
                    </div>
                    
                    <div style="margin-bottom: 15px;">
                        <label style="display: block; margin-bottom: 5px; font-weight: 600; color: #333; font-size: 14px;">Description *</label>
                        <textarea id="nativeDescription" name="description" required rows="4"
                                  style="width: 100%; box-sizing: border-box; border: 1px solid #ccc; padding: 8px 12px; border-radius: 4px; background: white; color: #333; font-size: 14px; resize: vertical;">${item?.description || ''}</textarea>
                    </div>
                    
                    <div style="display: flex; gap: 15px; margin-bottom: 15px;">
                        <div style="flex: 1;">
                            <label style="display: block; margin-bottom: 5px; font-weight: 600; color: #333; font-size: 14px;">Project URL</label>
                            <input type="url" id="nativeUrl" name="url"
                                   style="width: 100%; box-sizing: border-box; border: 1px solid #ccc; padding: 8px 12px; border-radius: 4px; background: white; color: #333; font-size: 14px;"
                                   value="${item?.url || ''}" />
                        </div>
                        <div style="flex: 1;">
                            <label style="display: block; margin-bottom: 5px; font-weight: 600; color: #333; font-size: 14px;">Image URL</label>
                            <input type="url" id="nativeImageUrl" name="image_url"
                                   style="width: 100%; box-sizing: border-box; border: 1px solid #ccc; padding: 8px 12px; border-radius: 4px; background: white; color: #333; font-size: 14px;"
                                   value="${item?.image_url || ''}" />
                        </div>
                    </div>
                    
                    <div style="display: flex; gap: 15px; margin-bottom: 15px;">
                        <div style="flex: 2;">
                            <label style="display: block; margin-bottom: 5px; font-weight: 600; color: #333; font-size: 14px;">Technologies</label>
                            <input type="text" id="nativeTechnologies" name="technologies"
                                   style="width: 100%; box-sizing: border-box; border: 1px solid #ccc; padding: 8px 12px; border-radius: 4px; background: white; color: #333; font-size: 14px;"
                                   value="${item?.technologies ? (Array.isArray(item.technologies) ? item.technologies.join(', ') : item.technologies) : ''}"
                                   placeholder="Enter technologies separated by commas" />
                            <small style="display: block; font-size: 12px; color: #666; margin-top: 4px; font-style: italic;">Enter technologies separated by commas</small>
                        </div>
                        <div style="flex: 1;">
                            <label style="display: block; margin-bottom: 5px; font-weight: 600; color: #333; font-size: 14px;">Sort Order</label>
                            <input type="number" id="nativeSortOrder" name="sort_order"
                                   style="width: 100%; box-sizing: border-box; border: 1px solid #ccc; padding: 8px 12px; border-radius: 4px; background: white; color: #333; font-size: 14px;"
                                   value="${item?.sort_order || 0}"
                                   placeholder="0" />
                            <small style="display: block; font-size: 12px; color: #666; margin-top: 4px; font-style: italic;">Lower numbers appear first</small>
                        </div>
                    </div>
                    
                    <div id="nativeScreenshotsSection" style="margin-bottom: 15px;">
                        <label style="display: block; margin-bottom: 10px; font-weight: 600; color: #333; font-size: 14px;">Project Screenshots</label>
                        <div id="nativeScreenshots" style="margin-bottom: 10px;"></div>
                        <input type="file" id="nativeScreenshotUpload" accept="image/*" style="margin-bottom: 10px;">
                        <button type="button" onclick="uploadNativeScreenshot()" 
                                style="background: #007bff; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-size: 14px;">
                            Upload Screenshot
                        </button>
                        <div style="margin-top: 10px; padding: 15px; background: #f8f9fa; border: 2px dashed #ccc; border-radius: 6px; text-align: center; color: #666; font-size: 14px;">
                            Upload PNG, JPEG or WebP images (max 2MB each)
                        </div>
                    </div>
                </form>
            </div>
            <div style="padding: 15px 20px; background-color: #f8f9fa; border-top: 1px solid #dee2e6; text-align: right;">
                <button onclick="submitNativeForm()" 
                        style="background: #007bff; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; font-size: 14px; margin-right: 10px;">
                    ${isEdit ? 'Update Project' : 'Add Project'}
                </button>
                <button onclick="hideNativeDialog()" 
                        style="background: #6c757d; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; font-size: 14px;">
                    Cancel
                </button>
            </div>
        `;
        
        overlay.appendChild(dialog);
        document.body.appendChild(overlay);
        
        // Load screenshots if editing
        if (item && item.title) {
            loadNativeScreenshots(item.title);
        }
        
        // Focus first input
        setTimeout(() => {
            document.getElementById('nativeTitle').focus();
        }, 100);
    }
    
    function hideNativeDialog() {
        const dialog = document.getElementById('nativeProjectDialog');
        if (dialog) {
            dialog.remove();
        }
        currentEditId = null;
    }
    
    function submitNativeForm() {
        const form = document.getElementById('nativeProjectForm');
        const formData = new FormData(form);
        
        // Convert technologies string to array
        const techString = formData.get('technologies');
        const technologies = techString ? techString.split(',').map(t => t.trim()).filter(t => t) : [];
        
        const projectData = {
            title: formData.get('title'),
            description: formData.get('description'), 
            url: formData.get('url'),
            image_url: formData.get('image_url'),
            technologies: technologies,
            sort_order: parseInt(formData.get('sort_order')) || 0,
            portfolio_id: window.PORTFOLIO_ID
        };
        
        const url = currentEditId ? `/projects/${currentEditId}` : '/projects';
        const method = currentEditId ? 'PUT' : 'POST';
        
        fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(projectData)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            hideNativeDialog();
            loadGrid();
            alert(currentEditId ? 'Project updated successfully!' : 'Project added successfully!');
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error saving project: ' + error.message);
        });
    }
    
    function loadNativeScreenshots(projectTitle) {
        // Implementation for loading screenshots in native mode
        // This would be similar to the Dojo version but simpler
    }
    
    function uploadNativeScreenshot() {
        // Implementation for uploading screenshots in native mode
        // This would be similar to the Dojo version but simpler
    }
    
    // Basic grid loading
    function loadGrid() {
        fetch('/projects')
            .then(response => response.json())
            .then(data => {
                const gridContainer = document.getElementById('grid');
                if (data.length === 0) {
                    gridContainer.innerHTML = '<p>No projects found.</p>';
                    return;
                }
                
                let html = `
                    <table style="width: 100%; border-collapse: collapse;">
                        <thead>
                            <tr style="background: #f8f9fa;">
                                <th style="text-align: left; padding: 12px; border: 1px solid #dee2e6;">Select</th>
                                <th style="text-align: left; padding: 12px; border: 1px solid #dee2e6;">Title</th>
                                <th style="text-align: left; padding: 12px; border: 1px solid #dee2e6;">Description</th>
                                <th style="text-align: left; padding: 12px; border: 1px solid #dee2e6;">URL</th>
                                <th style="text-align: left; padding: 12px; border: 1px solid #dee2e6;">Technologies</th>
                                <th style="text-align: left; padding: 12px; border: 1px solid #dee2e6;">Sort Order</th>
                                <th style="text-align: left; padding: 12px; border: 1px solid #dee2e6;">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                `;
                
                data.forEach(project => {
                    const technologies = Array.isArray(project.technologies) ? project.technologies.join(', ') : project.technologies || '';
                    html += `
                        <tr>
                            <td style="padding: 8px; border: 1px solid #dee2e6;">
                                <input type="checkbox" value="${project.id}" />
                            </td>
                            <td style="padding: 8px; border: 1px solid #dee2e6;">${project.title}</td>
                            <td style="padding: 8px; border: 1px solid #dee2e6;">${project.description}</td>
                            <td style="padding: 8px; border: 1px solid #dee2e6;">${project.url || ''}</td>
                            <td style="padding: 8px; border: 1px solid #dee2e6;">${technologies}</td>
                            <td style="padding: 8px; border: 1px solid #dee2e6;">${project.sort_order}</td>
                            <td style="padding: 8px; border: 1px solid #dee2e6;">
                                <button onclick="window.projectsAdmin.editItem('${project.id}')" 
                                        style="background: #007bff; color: white; border: none; padding: 4px 8px; border-radius: 4px; cursor: pointer; margin-right: 5px;">
                                    Edit
                                </button>
                            </td>
                        </tr>
                    `;
                });
                
                html += '</tbody></table>';
                gridContainer.innerHTML = html;
            })
            .catch(error => {
                console.error('Error loading projects:', error);
                document.getElementById('grid').innerHTML = '<p>Error loading projects: ' + error.message + '</p>';
            });
    }
    
    function deleteSelected() {
        const checkboxes = document.querySelectorAll('#grid input[type="checkbox"]:checked');
        if (checkboxes.length === 0) {
            alert('Please select projects to delete.');
            return;
        }
        
        if (!confirm(`Are you sure you want to delete ${checkboxes.length} project(s)?`)) {
            return;
        }
        
        const ids = Array.from(checkboxes).map(cb => cb.value);
        Promise.all(ids.map(id => 
            fetch(`/projects/${id}`, { method: 'DELETE' })
        ))
        .then(() => {
            loadGrid();
            alert('Projects deleted successfully!');
        })
        .catch(error => {
            console.error('Error deleting projects:', error);
            alert('Error deleting projects: ' + error.message);
        });
    }
    
    // Export native functions to global scope
    window.projectsAdmin = {
        showAddDialog: showAddDialog,
        editItem: editItem,
        deleteSelected: deleteSelected,
        handleFormSubmit: submitNativeForm,
        hideDialog: hideNativeDialog,
        loadGrid: loadGrid
    };
    
    // Make native dialog functions globally available
    window.hideNativeDialog = hideNativeDialog;
    window.submitNativeForm = submitNativeForm;
    window.uploadNativeScreenshot = uploadNativeScreenshot;
    
    // Initialize the grid
    document.addEventListener('DOMContentLoaded', function() {
        loadGrid();
        
        // Setup button event listeners
        document.getElementById('addBtn').addEventListener('click', showAddDialog);
        document.getElementById('deleteBtn').addEventListener('click', deleteSelected);
    });
}
