// Global variables
let allLogs = [];
let filteredLogs = [];
let currentOffset = 0;
let pageSize = 50;
let isLoading = false;
let hasMoreLogs = true;
let intersectionObserver;
let backendTotalCount = 0; // Total count from backend including filters

// Sorting variables
let currentSortField = 'timestamp';
let currentSortOrder = 'desc'; // Default to newest first

// Global functions - defined immediately so buttons work
window.refreshLogs = function() {
    console.log('Refresh button clicked');
    currentOffset = 0;
    allLogs = [];
    filteredLogs = [];
    hasMoreLogs = true;
    document.getElementById('logsTableBody').innerHTML = '';
    loadLogs();
};

window.clearLogs = async function() {
    console.log('Clear button clicked');
    if (confirm('Are you sure you want to clear all logs?')) {
        try {
            const cacheBust = Date.now() + Math.random();
            const response = await fetch(`/logs/clear?v=${cacheBust}&cb=v2_1`, { 
                method: 'POST',
                headers: {
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache'
                }
            });
            if (response.ok) {
                refreshLogs();
            } else {
                alert('Failed to clear logs');
            }
        } catch (error) {
            alert('Failed to clear logs: ' + error.message);
        }
    }
};

window.clearFilters = function() {
    console.log('Clear filters button clicked');
    document.getElementById('searchBox').value = '';
    document.getElementById('levelFilter').value = '';
    document.getElementById('moduleFilter').value = '';
    document.getElementById('timeFilter').value = '';
    applyFilters();
    updateClearFiltersButtonVisibility();
};

// Check if any filters are active
function hasActiveFilters() {
    const searchValue = document.getElementById('searchBox').value.trim();
    const levelFilter = document.getElementById('levelFilter').value;
    const moduleFilter = document.getElementById('moduleFilter').value;
    const timeFilter = document.getElementById('timeFilter').value;
    
    return searchValue !== '' || levelFilter !== '' || moduleFilter !== '' || timeFilter !== '';
}

// Show or hide the clear filters button based on filter state
function updateClearFiltersButtonVisibility() {
    const clearBtn = document.getElementById('clearFiltersBtn');
    if (hasActiveFilters()) {
        clearBtn.style.display = 'block';
    } else {
        clearBtn.style.display = 'none';
    }
}

// Load logs with pagination
async function loadLogs(append = false) {
    if (isLoading) return;
    
    isLoading = true;
    document.getElementById('loadingIndicator').style.display = 'block';
    
    console.log('Loading logs. Append:', append, 'Current offset:', currentOffset);
    
    try {
        // Build URL with sorting and filter parameters
        const params = new URLSearchParams({
            offset: append ? currentOffset : 0,
            limit: pageSize,
            sort_field: currentSortField,
            sort_order: currentSortOrder
        });
        
        // Add filter parameters
        const searchValue = document.getElementById('searchBox').value.trim();
        const levelFilter = document.getElementById('levelFilter').value;
        const moduleFilter = document.getElementById('moduleFilter').value;
        const timeFilter = document.getElementById('timeFilter').value;
        
        if (searchValue) params.append('search', searchValue);
        if (levelFilter) params.append('level', levelFilter);
        if (moduleFilter) params.append('module', moduleFilter);
        if (timeFilter) params.append('time_filter', timeFilter);
        
        const cacheBust = Date.now() + Math.random();
        const response = await fetch(`/logs/data?${params}&v=${cacheBust}&cb=v2_1`, {
            headers: {
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache'
            }
        });
        const data = await response.json();
        
        console.log('Received data:', data);
        console.log('Data keys:', Object.keys(data));
        console.log('Data type:', typeof data);
        console.log('Has has_more?', 'has_more' in data);
        console.log('Has has_next?', 'has_next' in data);
        console.log('has_more value:', data.has_more);
        console.log('has_next value:', data.has_next);
        console.log('Logs count:', data.logs ? data.logs.length : 0);
        
        // Extra validation for the data structure
        if (typeof data !== 'object' || data === null) {
            throw new Error('Invalid response format - not an object');
        }
        if (!('logs' in data)) {
            throw new Error('Response missing logs property');
        }
        if (!('has_more' in data)) {
            console.warn('Response missing has_more property, assuming false');
            data.has_more = false;
        }
        
        // Store backend total count for accurate statistics
        backendTotalCount = data.total_count || 0;
        
        if (!data.logs || data.logs.length === 0) {
            hasMoreLogs = false;
            document.getElementById('noMoreLogs').style.display = 'block';
            if (!append) {
                // Clear the display if this is a fresh load with no results
                allLogs = [];
                filteredLogs = [];
                updateDisplay();
                updateStats();
            }
        } else {
            if (append) {
                allLogs = allLogs.concat(data.logs);
            } else {
                allLogs = data.logs;
                currentOffset = 0; // Reset offset for fresh loads
            }
            
            currentOffset += data.logs.length;
            hasMoreLogs = data.has_more;
            
            // Since backend handles filtering, filtered logs = all loaded logs
            filteredLogs = allLogs;
            
            updatePagination(data.pagination || {});
            updateModuleFilter();
            updateDisplay();
            updateStats();
        }
        
        console.log('Logs loaded successfully. Total logs:', allLogs.length);
    } catch (error) {
        console.error('Failed to load logs:', error);
        alert('Failed to load logs: ' + error.message);
    } finally {
        isLoading = false;
        document.getElementById('loadingIndicator').style.display = 'none';
    }
}

// Reload logs with current filters (called when filters change)
function reloadWithFilters() {
    console.log('Reloading logs with new filters');
    currentOffset = 0;
    allLogs = [];
    filteredLogs = [];
    hasMoreLogs = true;
    document.getElementById('logsTableBody').innerHTML = '';
    document.getElementById('noMoreLogs').style.display = 'none';
    loadLogs(false); // false = don't append, start fresh
}

// Apply filters by reloading data from backend
function applyFilters() {
    reloadWithFilters();
}

// Update the table display
function updateDisplay() {
    console.log('updateDisplay called with', filteredLogs.length, 'filtered logs');
    const tbody = document.getElementById('logsTableBody');
    tbody.innerHTML = '';
    
    if (filteredLogs.length === 0) {
        console.log('No filtered logs to display');
        const row = document.createElement('tr');
        row.innerHTML = '<td colspan="7" style="text-align: center; padding: 20px;">No logs found</td>';
        tbody.appendChild(row);
        return;
    }
    
    filteredLogs.forEach((log, index) => {
        console.log('Processing log', index, ':', log);
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="log-timestamp">${new Date(log.timestamp).toLocaleString()}</td>
            <td><span class="log-level log-level-${log.level || 'unknown'}">${escapeHtml(log.level || 'unknown')}</span></td>
            <td class="log-module">${escapeHtml(log.module || '')}</td>
            <td class="log-message">
                <div class="message-content">
                    <span class="message-text">${escapeHtml(log.message || '')}</span>
                    <button class="copy-btn" onclick="copyToClipboard('${escapeHtml(log.message || '').replace(/'/g, "\\'")}', this)" title="Copy message to clipboard">
                        <span class="copy-icon">⧉</span>
                    </button>
                </div>
            </td>
            <td class="log-function">${escapeHtml(log.function || '')}</td>
            <td class="log-line">${escapeHtml(log.line || '')}</td>
            <td class="log-ip">${escapeHtml(log.ip_address || 'N/A')}</td>
        `;
        tbody.appendChild(row);
    });
}

// Render logs without filtering (used for sorting)
function renderLogs() {
    const tbody = document.getElementById('logsTableBody');
    tbody.innerHTML = '';
    
    filteredLogs.forEach(log => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="log-timestamp">${new Date(log.timestamp).toLocaleString()}</td>
            <td><span class="log-level log-level-${log.level || 'unknown'}">${escapeHtml(log.level || 'unknown')}</span></td>
            <td class="log-module">${escapeHtml(log.module || '')}</td>
            <td class="log-message">
                <div class="message-content">
                    <span class="message-text">${escapeHtml(log.message || '')}</span>
                    <button class="copy-btn" onclick="copyToClipboard('${escapeHtml(log.message || '').replace(/'/g, "\\'")}', this)" title="Copy message to clipboard">
                        <span class="copy-icon">⧉</span>
                    </button>
                </div>
            </td>
            <td class="log-function">${escapeHtml(log.function || '')}</td>
            <td class="log-line">${escapeHtml(log.line || '')}</td>
            <td class="log-ip">${escapeHtml(log.ip_address || 'N/A')}</td>
        `;
        tbody.appendChild(row);
    });
}

// Update stats display
function updateStats() {
    // Use backend total count (total matching records in database with current filters)
    const totalCount = backendTotalCount || 0;
    document.getElementById('totalCount').textContent = `Total: ${totalCount}`;
    
    // Showing count is how many we've loaded so far
    const loadedCount = filteredLogs.length;
    document.getElementById('filteredLogs').textContent = `Loaded: ${loadedCount}`;
    
    // Count errors and warnings in loaded logs only
    const errorCount = filteredLogs.filter(log => log.level && log.level.toLowerCase() === 'error').length;
    const warningCount = filteredLogs.filter(log => log.level && log.level.toLowerCase() === 'warning').length;
    
    document.getElementById('errorCount').textContent = `Errors: ${errorCount}`;
    document.getElementById('warningCount').textContent = `Warnings: ${warningCount}`;
}

// Update pagination info
function updatePagination(pagination) {
    console.log('Pagination info:', pagination);
    
    // Store backend total count for accurate totals
    if (pagination.total !== undefined) {
        backendTotalCount = pagination.total;
    }
    
    // Update the log count display
    if (pagination.total !== undefined) {
        document.getElementById('filteredLogs').textContent = `Showing: ${allLogs.length} of ${pagination.total}`;
    }
    
    // Check if there are more pages
    if (pagination.page && pagination.pages) {
        hasMoreLogs = pagination.page < pagination.pages;
    }
}

// Update module filter options
function updateModuleFilter() {
    const moduleFilter = document.getElementById('moduleFilter');
    const currentValue = moduleFilter.value;
    const modules = [...new Set(allLogs.map(log => log.module).filter(Boolean))].sort();
    
    moduleFilter.innerHTML = '<option value="">All Modules</option>';
    modules.forEach(module => {
        const option = document.createElement('option');
        option.value = module;
        option.textContent = module;
        moduleFilter.appendChild(option);
    });
    
    moduleFilter.value = currentValue;
}

// Reload logs from backend when filters change
function reloadWithFilters() {
    console.log('Reloading logs with new filters');
    currentOffset = 0;
    allLogs = [];
    filteredLogs = [];
    hasMoreLogs = true;
    backendTotalCount = 0;
    document.getElementById('logsTableBody').innerHTML = '';
    loadLogs();
}

// Setup event listeners
function setupEventListeners() {
    // Search box
    document.getElementById('searchBox').addEventListener('keyup', debounce(() => {
        applyFilters();
        updateClearFiltersButtonVisibility();
    }, 300));
    
    // Filter dropdowns - reload data from backend when filters change
    document.getElementById('levelFilter').addEventListener('change', () => {
        applyFilters();
        updateClearFiltersButtonVisibility();
    });
    document.getElementById('moduleFilter').addEventListener('change', () => {
        applyFilters();
        updateClearFiltersButtonVisibility();
    });
    document.getElementById('timeFilter').addEventListener('change', () => {
        applyFilters();
        updateClearFiltersButtonVisibility();
    });
    
    // Column sorting
    document.querySelectorAll('.logs-table th[data-sort]').forEach(th => {
        th.addEventListener('click', () => {
            const sortField = th.getAttribute('data-sort');
            
            // Toggle sort order if clicking the same column, otherwise default to descending
            if (currentSortField === sortField) {
                currentSortOrder = currentSortOrder === 'asc' ? 'desc' : 'asc';
            } else {
                currentSortField = sortField;
                currentSortOrder = 'desc';
            }
            
            updateSortIndicators();
            applyFilters(); // Use consistent function for all reloads
        });
    });
    
    // Initialize sort indicators
    updateSortIndicators();
    
    // Intersection Observer for infinite scroll
    intersectionObserver = new IntersectionObserver((entries) => {
        if (entries[0].isIntersecting && hasMoreLogs && !isLoading) {
            console.log('Loading more logs due to scroll');
            loadLogs(true);
        }
    }, {
        threshold: 0.1
    });
    
    intersectionObserver.observe(document.getElementById('scrollTrigger'));
}

// Utility functions
function escapeHtml(text) {
    if (text === null || text === undefined) {
        return '';
    }
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Copy text to clipboard
function copyToClipboard(text, button) {
    navigator.clipboard.writeText(text).then(() => {
        // Show feedback
        const originalIcon = button.innerHTML;
        button.innerHTML = '<span class="copy-icon">✓</span>';
        button.classList.add('copied');
        
        setTimeout(() => {
            button.innerHTML = originalIcon;
            button.classList.remove('copied');
        }, 1000);
    }).catch(err => {
        console.error('Failed to copy text: ', err);
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        
        // Show feedback
        const originalIcon = button.innerHTML;
        button.innerHTML = '<span class="copy-icon">✓</span>';
        button.classList.add('copied');
        
        setTimeout(() => {
            button.innerHTML = originalIcon;
            button.classList.remove('copied');
        }, 1000);
    });
}

// Sorting functions
function updateSortIndicators() {
    // Remove all sort classes
    document.querySelectorAll('.logs-table th').forEach(th => {
        th.classList.remove('sorted-asc', 'sorted-desc');
    });
    
    // Add appropriate class to current sort column
    const currentTh = document.querySelector(`.logs-table th[data-sort="${currentSortField}"]`);
    if (currentTh) {
        currentTh.classList.add(currentSortOrder === 'asc' ? 'sorted-asc' : 'sorted-desc');
    }
}

function sortLogs(logs) {
    return logs.slice().sort((a, b) => {
        let aVal = a[currentSortField];
        let bVal = b[currentSortField];
        
        // Handle timestamp sorting
        if (currentSortField === 'timestamp') {
            aVal = new Date(aVal);
            bVal = new Date(bVal);
        } else if (typeof aVal === 'string') {
            aVal = aVal.toLowerCase();
            bVal = bVal.toLowerCase();
        }
        
        let comparison = 0;
        if (aVal < bVal) {
            comparison = -1;
        } else if (aVal > bVal) {
            comparison = 1;
        }
        
        return currentSortOrder === 'asc' ? comparison : -comparison;
    });
}

function sortAndRenderLogs() {
    // Backend handles sorting, so just reload with new sort parameters
    reloadWithFilters();
}

// Calculate and set the dynamic height for the logs table
function calculateAndSetTableHeight() {
    // Calculate the height of all elements above the table
    const navigation = document.querySelector('.site-header');
    const logsControls = document.querySelector('.logs-controls-row');
    const logsStats = document.querySelector('.logs-stats');
    
    let headerHeight = 20; // Base padding
    
    if (navigation) {
        headerHeight += navigation.offsetHeight;
    }
    if (logsControls) {
        headerHeight += logsControls.offsetHeight + 20; // Add margin
    }
    if (logsStats) {
        headerHeight += logsStats.offsetHeight + 20; // Add margin
    }
    
    // Set the CSS custom property
    document.documentElement.style.setProperty('--header-height', `${headerHeight}px`);
    
    console.log('Calculated header height:', headerHeight + 'px');
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing logs interface');
    calculateAndSetTableHeight();
    setupEventListeners();
    updateClearFiltersButtonVisibility(); // Check initial filter state
    loadLogs();
    
    // Recalculate on window resize
    window.addEventListener('resize', debounce(calculateAndSetTableHeight, 100));
});
