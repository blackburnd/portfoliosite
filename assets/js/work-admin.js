/**
 * Work Admin JavaScript - Dojo Implementation
 * Handles work items administration functionality using Dojo dialogs and widgets
 */

require([
    "dijit/Dialog",
    "dijit/form/Form",
    "dijit/form/TextBox",
    "dijit/form/Textarea",
    "dijit/form/DateTextBox",
    "dijit/form/CheckBox",
    "dijit/form/NumberTextBox",
    "dijit/form/Button",
    "dijit/form/ValidationTextBox",
    "dojo/domReady!"
], function(Dialog, Form, TextBox, Textarea, DateTextBox, CheckBox, NumberTextBox, Button, ValidationTextBox) {
    
    let workItemDialog;
    let currentEditId = null;
    
    // Create the work item dialog
    function createWorkItemDialog() {
        if (workItemDialog) {
            workItemDialog.destroyRecursive();
        }
        
        const dialogContent = `
            <div data-dojo-type="dijit/form/Form" id="workItemForm" encType="multipart/form-data" action="" method="">
                <div class="dijitDialogPaneContentArea">
                    <div class="form-row">
                        <div class="form-group">
                            <label for="company">Company *</label>
                            <input data-dojo-type="dijit/form/ValidationTextBox" 
                                   required="true" 
                                   name="company" 
                                   id="company" 
                                   placeholder="Company name">
                        </div>
                        <div class="form-group">
                            <label for="position">Position *</label>
                            <input data-dojo-type="dijit/form/ValidationTextBox" 
                                   required="true" 
                                   name="position" 
                                   id="position" 
                                   placeholder="Job title">
                        </div>
                    </div>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label for="location">Location</label>
                            <input data-dojo-type="dijit/form/TextBox" 
                                   name="location" 
                                   id="location" 
                                   placeholder="e.g., San Francisco, CA">
                        </div>
                        <div class="form-group">
                            <label for="company_url">Company URL</label>
                            <input data-dojo-type="dijit/form/TextBox" 
                                   name="company_url" 
                                   id="company_url" 
                                   placeholder="https://company.com">
                        </div>
                    </div>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label for="start_date">Start Date</label>
                            <input data-dojo-type="dijit/form/DateTextBox" 
                                   name="start_date" 
                                   id="start_date">
                        </div>
                        <div class="form-group">
                            <label for="end_date">End Date</label>
                            <input data-dojo-type="dijit/form/DateTextBox" 
                                   name="end_date" 
                                   id="end_date">
                            <small class="form-note">Leave empty if current position</small>
                        </div>
                    </div>
                    
                    <div class="form-group">
                        <label for="description">Description</label>
                        <textarea data-dojo-type="dijit/form/Textarea" 
                                 name="description" 
                                 id="description" 
                                 rows="4" 
                                 placeholder="Describe your role, responsibilities, and achievements..."></textarea>
                    </div>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label>
                                <input data-dojo-type="dijit/form/CheckBox" 
                                       name="is_current" 
                                       id="is_current"> Current Position
                            </label>
                        </div>
                        <div class="form-group">
                            <label for="sort_order">Sort Order</label>
                            <input data-dojo-type="dijit/form/NumberTextBox" 
                                   name="sort_order" 
                                   id="sort_order" 
                                   value="0" 
                                   constraints="{min:0}">
                            <small class="form-note">Lower numbers appear first</small>
                        </div>
                    </div>
                </div>
                
                <div class="dijitDialogPaneActionBar">
                    <button data-dojo-type="dijit/form/Button" type="button" id="submitBtn" onclick="window.workAdmin.handleFormSubmit()">
                        Add Work Item
                    </button>
                    <button data-dojo-type="dijit/form/Button" type="button" onclick="window.workAdmin.hideDialog()">
                        Cancel
                    </button>
                </div>
            </div>
        `;
        
        workItemDialog = new Dialog({
            title: "Add Work Item",
            content: dialogContent,
            style: "width: 600px;"
        });
        
        // Parse the Dojo widgets in the dialog after it's created
        require(["dojo/parser"], function(parser) {
            parser.parse(workItemDialog.domNode);
        });
    }
    
    function showAddDialog() {
        currentEditId = null;
        createWorkItemDialog();
        workItemDialog.set("title", "Add Work Item");
        
        // Wait for widgets to be parsed before setting properties
        setTimeout(() => {
            dijit.byId("submitBtn").set("label", "Add Work Item");
            workItemDialog.show();
        }, 100);
    }
    
    function editItem(id) {
        fetch('/workitems/' + id)
            .then(response => {
                if (!response.ok) {
                    throw new Error('HTTP error! status: ' + response.status);
                }
                return response.json();
            })
            .then(item => {
                currentEditId = id;
                createWorkItemDialog();
                workItemDialog.set("title", "Edit Work Item");
                
                // Wait for widgets to be parsed before setting properties and populating
                setTimeout(() => {
                    dijit.byId("submitBtn").set("label", "Update Work Item");
                    populateForm(item);
                    workItemDialog.show();
                }, 100);
            })
            .catch(error => {
                console.error("Error loading work item:", error);
                alert("Error loading work item: " + error.message);
            });
    }
    
    function populateForm(item) {
        dijit.byId("company").set("value", item.company || "");
        dijit.byId("position").set("value", item.position || "");
        dijit.byId("location").set("value", item.location || "");
        dijit.byId("company_url").set("value", item.company_url || "");
        dijit.byId("description").set("value", item.description || "");
        dijit.byId("is_current").set("checked", item.is_current || false);
        dijit.byId("sort_order").set("value", item.sort_order || 0);
        
        if (item.start_date) {
            dijit.byId("start_date").set("value", new Date(item.start_date));
        }
        if (item.end_date) {
            dijit.byId("end_date").set("value", new Date(item.end_date));
        }
    }
    
    function hideDialog() {
        if (workItemDialog) {
            workItemDialog.hide();
        }
    }
    
    function handleFormSubmit() {
        // Simple validation - only require company and position
        const company = dijit.byId("company").get("value");
        const position = dijit.byId("position").get("value");
        
        if (!company || !position) {
            alert("Please enter both Company and Position.");
            return;
        }
        
        // Get form values
        const workItem = {
            portfolio_id: "daniel-blackburn",
            company: company,
            position: position
        };

        // Add optional fields only if they have values
        const location = dijit.byId("location").get("value");
        if (location) workItem.location = location;

        const companyUrl = dijit.byId("company_url").get("value");
        if (companyUrl) workItem.company_url = companyUrl;

        const description = dijit.byId("description").get("value");
        if (description) workItem.description = description;

        workItem.is_current = dijit.byId("is_current").get("checked");

        const sortOrder = dijit.byId("sort_order").get("value");
        if (sortOrder) workItem.sort_order = parseInt(sortOrder);
        
        // Handle dates
        const startDate = dijit.byId("start_date").get("value");
        const endDate = dijit.byId("end_date").get("value");
        
        if (startDate) {
            workItem.start_date = startDate.toISOString().split('T')[0];
        }
        if (endDate) {
            workItem.end_date = endDate.toISOString().split('T')[0];
        }
        
        const isEdit = currentEditId !== null;
        const url = isEdit ? '/workitems/' + currentEditId : '/workitems';
        const method = isEdit ? 'PUT' : 'POST';
        
        dijit.byId("submitBtn").set("disabled", true);
        dijit.byId("submitBtn").set("label", isEdit ? "Updating..." : "Adding...");
        
        // Retry logic for network issues
        const maxRetries = 3;
        let retryCount = 0;
        
        const makeRequest = () => {
            return fetch(url, {
                method: method,
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(workItem)
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('HTTP error! status: ' + response.status);
                }
                return response.json();
            })
            .catch(error => {
                if (retryCount < maxRetries && (error.message.includes('Failed to fetch') || error.message.includes('CONNECTION_REFUSED'))) {
                    retryCount++;
                    console.log(`Retry attempt ${retryCount}/${maxRetries} for ${isEdit ? 'updating' : 'adding'} work item...`);
                    return new Promise(resolve => setTimeout(resolve, 1000 * retryCount)).then(makeRequest);
                }
                throw error;
            });
        };
        
        makeRequest()
        .then(response => {
            console.log((isEdit ? 'Updated' : 'Added') + ' work item:', response);
            loadGrid();
            workItemDialog.hide();
            alert('Work item ' + (isEdit ? 'updated' : 'added') + ' successfully!');
        })
        .catch(error => {
            console.error('Error ' + (isEdit ? 'updating' : 'adding') + ' work item:', error);
            if (error.message.includes('Failed to fetch') || error.message.includes('CONNECTION_REFUSED')) {
                alert('Network error: Unable to connect to server. Please check your connection and try again.');
            } else {
                alert('Error ' + (isEdit ? 'updating' : 'adding') + ' work item: ' + error.message);
            }
        })
        .finally(() => {
            dijit.byId("submitBtn").set("disabled", false);
            dijit.byId("submitBtn").set("label", isEdit ? "Update Work Item" : "Add Work Item");
        });
    }
    
    function loadGrid() {
        document.getElementById('grid').innerHTML = '<div class="loading">Loading work items...</div>';
        
        fetch('/workitems')
            .then(response => {
                if (!response.ok) {
                    throw new Error('HTTP error! status: ' + response.status);
                }
                return response.json();
            })
            .then(data => {
                console.log("Loaded work items:", data);
                let gridHtml = '<table class="work-items-table">' +
                    '<thead><tr>' +
                    '<th>Select</th><th>Company</th><th>Position</th><th>Location</th>' +
                    '<th>Start Date</th><th>End Date</th><th>Current</th><th>Actions</th></tr></thead><tbody>';
                
                if (data && data.length > 0) {
                    data.forEach(item => {
                        gridHtml += `<tr data-id="${item.id}">
                            <td><input type="checkbox" class="select-row"></td>
                            <td>${item.company || ''}</td>
                            <td>${item.position || ''}</td>
                            <td>${item.location || ''}</td>
                            <td>${item.start_date || ''}</td>
                            <td>${item.end_date || 'Present'}</td>
                            <td>${item.is_current ? '✓' : ''}</td>
                            <td>
                                <button class="btn btn-small" onclick="window.workAdmin.editItem('${item.id}')">Edit</button>
                            </td>
                        </tr>`;
                    });
                } else {
                    gridHtml += '<tr><td colspan="8">No work items found</td></tr>';
                }
                gridHtml += '</tbody></table>';
                document.getElementById('grid').innerHTML = gridHtml;
            })
            .catch(error => {
                console.error("Error loading work items:", error);
                document.getElementById('grid').innerHTML = '<div class="error">Error loading work items: ' + error.message + '</div>';
            });
    }
    
    function deleteSelected() {
        const selected = document.querySelectorAll('.select-row:checked');
        if (selected.length === 0) {
            alert("Please select items to delete.");
            return;
        }
        
        if (confirm('Are you sure you want to delete ' + selected.length + ' item(s)?')) {
            const deletePromises = [];
            selected.forEach(checkbox => {
                const row = checkbox.closest('tr');
                const id = row.getAttribute('data-id');
                deletePromises.push(
                    fetch('/workitems/' + id, {
                        method: 'DELETE'
                    })
                    .then(response => {
                        if (!response.ok) {
                            throw new Error('HTTP error! status: ' + response.status);
                        }
                        console.log("Deleted work item:", id);
                    })
                    .catch(error => {
                        console.error("Error deleting work item:", id, error);
                        throw error;
                    })
                );
            });
            
            Promise.all(deletePromises)
                .then(() => {
                    loadGrid();
                    alert("Items deleted successfully!");
                })
                .catch(error => {
                    alert("Error deleting some items: " + error.message);
                    loadGrid();
                });
        }
    }
    
    // Initialize when DOM is ready
    loadGrid();
    
    // Bind event handlers
    document.getElementById('addBtn').addEventListener('click', showAddDialog);
    document.getElementById('deleteBtn').addEventListener('click', deleteSelected);
    
    // Expose functions globally for onclick handlers
    window.workAdmin = {
        editItem: editItem,
        handleFormSubmit: handleFormSubmit,
        hideDialog: hideDialog
    };
});
