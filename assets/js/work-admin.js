/**
 * Work Admin JavaScript
 * Handles work items administration functionality
 */

class WorkAdmin {
    constructor() {
        this.currentEditId = null;
        this.init();
    }

    init() {
        this.loadGrid();
        this.bindEventHandlers();
    }

    bindEventHandlers() {
        document.getElementById('addBtn').addEventListener('click', () => this.showAddForm());
        document.getElementById('deleteBtn').addEventListener('click', () => this.deleteSelected());
        document.getElementById('cancelBtn').addEventListener('click', () => this.hideForm());
        document.getElementById('workItemForm').addEventListener('submit', (e) => this.handleFormSubmit(e));
    }

    loadGrid() {
        document.getElementById('grid').innerHTML = '<div class="loading">Loading work items...</div>';
        
        fetch('/workitems')
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log("Loaded work items:", data);
                this.renderGrid(data);
            })
            .catch(error => {
                console.error("Error loading work items:", error);
                document.getElementById('grid').innerHTML = '<div class="error">Error loading work items: ' + error.message + '</div>';
            });
    }

    renderGrid(data) {
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
                        <button class="btn btn-small" onclick="workAdmin.editItem('${item.id}')">Edit</button>
                    </td>
                </tr>`;
            });
        } else {
            gridHtml += '<tr><td colspan="8">No work items found</td></tr>';
        }
        gridHtml += '</tbody></table>';
        document.getElementById('grid').innerHTML = gridHtml;
    }

    showAddForm() {
        this.currentEditId = null;
        this.resetForm();
        document.getElementById('formTitle').textContent = 'Add Work Item';
        document.getElementById('submitBtn').textContent = 'Add Work Item';
        document.getElementById('workItemFormContainer').style.display = 'block';
        document.getElementById('company').focus();
    }

    editItem(id) {
        // Find the item data from the current grid
        const row = document.querySelector(`tr[data-id="${id}"]`);
        if (!row) return;

        // Fetch the complete item data from the server
        fetch(`/workitems/${id}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(item => {
                this.currentEditId = id;
                this.populateForm(item);
                document.getElementById('formTitle').textContent = 'Edit Work Item';
                document.getElementById('submitBtn').textContent = 'Update Work Item';
                document.getElementById('workItemFormContainer').style.display = 'block';
                document.getElementById('company').focus();
            })
            .catch(error => {
                console.error("Error loading work item:", error);
                alert("Error loading work item: " + error.message);
            });
    }

    populateForm(item) {
        document.getElementById('company').value = item.company || '';
        document.getElementById('position').value = item.position || '';
        document.getElementById('location').value = item.location || '';
        document.getElementById('company_url').value = item.company_url || '';
        document.getElementById('start_date').value = item.start_date || '';
        document.getElementById('end_date').value = item.end_date || '';
        document.getElementById('description').value = item.description || '';
        document.getElementById('is_current').checked = item.is_current || false;
        document.getElementById('sort_order').value = item.sort_order || 0;
    }

    resetForm() {
        document.getElementById('workItemForm').reset();
        document.getElementById('is_current').checked = false;
        document.getElementById('sort_order').value = 0;
    }

    hideForm() {
        document.getElementById('workItemFormContainer').style.display = 'none';
        this.currentEditId = null;
        this.resetForm();
    }

    handleFormSubmit(event) {
        event.preventDefault();
        
        const formData = new FormData(event.target);
        const workItem = {
            portfolio_id: "daniel-blackburn",
            company: formData.get('company'),
            position: formData.get('position'),
            location: formData.get('location'),
            company_url: formData.get('company_url') || null,
            start_date: formData.get('start_date'),
            end_date: formData.get('end_date') || null,
            description: formData.get('description'),
            is_current: formData.get('is_current') === 'on',
            sort_order: parseInt(formData.get('sort_order')) || 0
        };

        // Validate required fields
        if (!workItem.company || !workItem.position || !workItem.start_date) {
            alert('Please fill in all required fields (Company, Position, Start Date)');
            return;
        }

        const isEdit = this.currentEditId !== null;
        const url = isEdit ? `/workitems/${this.currentEditId}` : '/workitems';
        const method = isEdit ? 'PUT' : 'POST';

        document.getElementById('submitBtn').disabled = true;
        document.getElementById('submitBtn').textContent = isEdit ? 'Updating...' : 'Adding...';

        fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(workItem)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(response => {
            console.log(`${isEdit ? 'Updated' : 'Added'} work item:`, response);
            this.loadGrid(); // Refresh the grid
            this.hideForm();
            this.showMessage(`Work item ${isEdit ? 'updated' : 'added'} successfully!`, 'success');
        })
        .catch(error => {
            console.error(`Error ${isEdit ? 'updating' : 'adding'} work item:`, error);
            this.showMessage(`Error ${isEdit ? 'updating' : 'adding'} work item: ` + error.message, 'error');
        })
        .finally(() => {
            document.getElementById('submitBtn').disabled = false;
            document.getElementById('submitBtn').textContent = isEdit ? 'Update Work Item' : 'Add Work Item';
        });
    }

    deleteSelected() {
        const selected = document.querySelectorAll('.select-row:checked');
        if (selected.length === 0) {
            alert("Please select items to delete.");
            return;
        }
        
        if (confirm(`Are you sure you want to delete ${selected.length} item(s)?`)) {
            const deletePromises = [];
            selected.forEach(checkbox => {
                const row = checkbox.closest('tr');
                const id = row.getAttribute('data-id');
                deletePromises.push(
                    fetch(`/workitems/${id}`, {
                        method: 'DELETE'
                    })
                    .then(response => {
                        if (!response.ok) {
                            throw new Error(`HTTP error! status: ${response.status}`);
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
                    this.loadGrid(); // Refresh the grid
                    this.showMessage("Items deleted successfully!", 'success');
                })
                .catch(error => {
                    this.showMessage("Error deleting some items: " + error.message, 'error');
                    this.loadGrid(); // Refresh anyway to show current state
                });
        }
    }

    showMessage(message, type = 'info') {
        // Create or update message element
        let messageEl = document.getElementById('message');
        if (!messageEl) {
            messageEl = document.createElement('div');
            messageEl.id = 'message';
            document.querySelector('.work-admin-content').insertBefore(messageEl, document.getElementById('grid'));
        }
        
        messageEl.className = `message ${type}`;
        messageEl.textContent = message;
        messageEl.style.display = 'block';
        
        // Auto-hide after 3 seconds
        setTimeout(() => {
            messageEl.style.display = 'none';
        }, 3000);
    }
}

// Initialize when DOM is ready
let workAdmin;
document.addEventListener('DOMContentLoaded', function() {
    workAdmin = new WorkAdmin();
});
