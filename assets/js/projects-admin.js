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
            projectDialog.destroyRecursively();
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
                    // Force styling after showing
                    forceDialogStyling();
                }, 100);
            })
            .catch(error => {
                console.error('Error fetching project:', error);
                alert('Error loading project data: ' + error.message);
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
            alert("Please enter both Title and Description.");
            return;
        }
        
        // Get form values
        const project = {
            portfolio_id: "daniel-blackburn",
            title: title,
            description: description
        };

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
            alert('Project ' + (isEdit ? 'updated' : 'added') + ' successfully!');
        })
        .catch(error => {
            console.error('Error ' + (isEdit ? 'updating' : 'adding') + ' project:', error);
            alert('Error ' + (isEdit ? 'updating' : 'adding') + ' project: ' + error.message);
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
            alert('Please select projects to delete.');
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
                alert('Projects deleted successfully!');
            })
            .catch(error => {
                console.error('Error deleting projects:', error);
                alert('Error deleting projects: ' + error.message);
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
        }
        
        // Force styling on title bar
        const titleBar = dialogNode.querySelector('.dijitDialogTitleBar');
        if (titleBar) {
            titleBar.style.setProperty('background-color', '#f8f9fa', 'important');
            titleBar.style.setProperty('background-image', 'none', 'important');
            titleBar.style.setProperty('background', '#f8f9fa', 'important');
            titleBar.style.setProperty('color', '#333', 'important');
        }
        
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
