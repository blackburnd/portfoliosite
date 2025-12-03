// Global variables
let allSubmissions = [];
let filteredSubmissions = [];
let currentOffset = 0;
let pageSize = 50;
let isLoading = false;
let hasMoreSubmissions = true;
let intersectionObserver;
let backendTotalCount = 0;
let currentSortField = 'created_at';
let currentSortOrder = 'desc';

window.refreshSubmissions = function() {
    currentOffset = 0;
    allSubmissions = [];
    filteredSubmissions = [];
    hasMoreSubmissions = true;
    document.getElementById('submissionsTableBody').innerHTML = '';
    loadSubmissions();
};

window.clearAllSubmissions = async function() {
    if (confirm('Are you sure you want to delete ALL contact submissions? This cannot be undone.')) {
        try {
            const cacheBust = Date.now() + Math.random();
            const response = await fetch(`/contact-submissions/clear?v=${cacheBust}`, {
                method: 'POST',
                headers: {
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache'
                }
            });
            if (response.ok) {
                refreshSubmissions();
                alert('All submissions cleared successfully');
            } else {
                alert('Failed to clear submissions');
            }
        } catch (error) {
            alert('Failed to clear submissions: ' + error.message);
        }
    }
};

window.deleteSubmission = async function(submissionId) {
    if (confirm('Are you sure you want to delete this submission?')) {
        try {
            const cacheBust = Date.now() + Math.random();
            const response = await fetch(`/contact-submissions/delete/${submissionId}?v=${cacheBust}`, {
                method: 'DELETE',
                headers: {
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache'
                }
            });
            if (response.ok) {
                refreshSubmissions();
            } else {
                alert('Failed to delete submission');
            }
        } catch (error) {
            alert('Failed to delete submission: ' + error.message);
        }
    }
};

window.toggleReadStatus = async function(submissionId, currentStatus) {
    try {
        const endpoint = currentStatus ? 'mark-unread' : 'mark-read';
        const cacheBust = Date.now() + Math.random();
        const response = await fetch(`/contact-submissions/${endpoint}/${submissionId}?v=${cacheBust}`, {
            method: 'POST',
            headers: {
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache'
            }
        });
        if (response.ok) {
            refreshSubmissions();
        } else {
            alert('Failed to update status');
        }
    } catch (error) {
        alert('Failed to update status: ' + error.message);
    }
};

window.clearFilters = function() {
    document.getElementById('searchBox').value = '';
    document.getElementById('statusFilter').value = '';
    document.getElementById('timeFilter').value = '';
    reloadSubmissionsWithFilters();
};

// Check if any filters are active
function hasActiveFilters() {
    const searchValue = document.getElementById('searchBox').value.trim();
    const statusFilter = document.getElementById('statusFilter').value;
    const timeFilter = document.getElementById('timeFilter').value;

    return searchValue !== '' || statusFilter !== '' || timeFilter !== '';
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

// Load submissions with pagination
async function loadSubmissions(append = false) {
    if (isLoading) return;

    isLoading = true;
    document.getElementById('loadingIndicator').style.display = 'block';

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
        const statusFilter = document.getElementById('statusFilter').value;
        const timeFilter = document.getElementById('timeFilter').value;

        if (searchValue) params.append('search', searchValue);
        if (statusFilter) params.append('status', statusFilter);
        if (timeFilter) params.append('time_filter', timeFilter);

        const cacheBust = Date.now() + Math.random();
        const response = await fetch(`/contact-submissions/data?${params}&v=${cacheBust}`, {
            headers: {
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache'
            }
        });
        const data = await response.json();

        // Extra validation for the data structure
        if (typeof data !== 'object' || data === null) {
            throw new Error('Invalid response format - not an object');
        }
        if (!('submissions' in data)) {
            throw new Error('Response missing submissions property');
        }
        if (!('has_more' in data)) {
            data.has_more = false;
        }

        // Store backend total count for accurate statistics
        backendTotalCount = data.total_count || 0;

        if (!data.submissions || data.submissions.length === 0) {
            hasMoreSubmissions = false;
            document.getElementById('noMoreSubmissions').style.display = 'block';
            if (!append) {
                allSubmissions = [];
                filteredSubmissions = [];
                updateDisplay();
                updateStats();
            }
        } else {
            if (append) {
                allSubmissions = allSubmissions.concat(data.submissions);
            } else {
                allSubmissions = data.submissions;
                currentOffset = 0;
            }

            currentOffset += data.submissions.length;
            hasMoreSubmissions = data.has_more;

            filteredSubmissions = allSubmissions;

            updatePagination(data.pagination || {});
            updateDisplay();
            updateStats();
        }

        console.log('Submissions loaded successfully. Total submissions:', allSubmissions.length);
    } catch (error) {
        console.error('Failed to load submissions:', error);
        alert('Failed to load submissions: ' + error.message);
    } finally {
        isLoading = false;
        document.getElementById('loadingIndicator').style.display = 'none';
    }
}

// Reload submissions with current filters
function reloadWithFilters() {
    currentOffset = 0;
    allSubmissions = [];
    filteredSubmissions = [];
    hasMoreSubmissions = true;
    document.getElementById('submissionsTableBody').innerHTML = '';
    document.getElementById('noMoreSubmissions').style.display = 'none';
    loadSubmissions(false);
}

// Apply filters by reloading data from backend
function applyFilters() {
    reloadWithFilters();
}

// Update the table display
function updateDisplay() {
    const tbody = document.getElementById('submissionsTableBody');
    tbody.innerHTML = '';

    if (filteredSubmissions.length === 0) {
        const row = document.createElement('tr');
        row.innerHTML = '<td colspan="8" style="text-align: center; padding: 20px;">No submissions found</td>';
        tbody.appendChild(row);
        return;
    }

    filteredSubmissions.forEach((submission) => {
        const row = document.createElement('tr');

        // Compute age
        const now = Date.now();
        const submissionTime = new Date(submission.created_at).getTime();
        let ageMs = now - submissionTime;
        let ageStr = '';
        if (ageMs < 60000) {
            ageStr = Math.floor(ageMs / 1000) + 's';
        } else if (ageMs < 3600000) {
            ageStr = Math.floor(ageMs / 60000) + 'm';
        } else if (ageMs < 86400000) {
            ageStr = Math.floor(ageMs / 3600000) + 'h';
        } else {
            const days = Math.floor(ageMs / 86400000);
            ageStr = days + 'd';
        }

        const dateStr = new Date(submission.created_at).toLocaleDateString();
        const timeStr = new Date(submission.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'});

        row.className = submission.is_read ? 'read' : 'unread';
        row.innerHTML = `
            <td class="log-timestamp">${dateStr} ${timeStr}</td>
            <td class="log-age">${ageStr}</td>
            <td>${escapeHtml(submission.name)}</td>
            <td>${escapeHtml(submission.email)}</td>
            <td>${escapeHtml(submission.subject)}</td>
            <td class="log-message">
                <div class="message-content">
                    ${needsExpand(submission.message) ? '<button class="expand-btn" onclick="toggleMessageExpand(this)">▶</button>' : ''}
                    <span class="message-text" data-full-message="${escapeHtml(submission.message)}">${escapeHtml(truncateMessage(submission.message))}</span>
                    <button class="copy-btn" data-copy-text="${escapeHtml(submission.message)}" title="Copy message to clipboard">
                        <span class="copy-icon">📋</span>
                    </button>
                </div>
            </td>
            <td>
                <span class="status-badge ${submission.is_read ? 'status-read' : 'status-unread'}">
                    ${submission.is_read ? 'Read' : 'Unread'}
                </span>
            </td>
            <td>
                <button class="compact-btn" onclick="toggleReadStatus('${submission.id}', ${submission.is_read})" title="${submission.is_read ? 'Mark as Unread' : 'Mark as Read'}">
                    ${submission.is_read ? '📭' : '📬'}
                </button>
                <button class="compact-btn" onclick="deleteSubmission('${submission.id}')" title="Delete">🗑️</button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

// Update stats display
function updateStats() {
    const totalCount = backendTotalCount || 0;
    document.getElementById('totalCount').textContent = `Total: ${totalCount}`;

    const loadedCount = filteredSubmissions.length;
    document.getElementById('filteredSubmissions').textContent = `Loaded: ${loadedCount}`;

    const unreadCount = filteredSubmissions.filter(s => !s.is_read).length;
    const readCount = filteredSubmissions.filter(s => s.is_read).length;

    document.getElementById('unreadCount').textContent = `Unread: ${unreadCount}`;
    document.getElementById('readCount').textContent = `Read: ${readCount}`;
}

// Update pagination info
function updatePagination(pagination) {
    console.log('Pagination info:', pagination);

    if (pagination.total !== undefined) {
        backendTotalCount = pagination.total;
    }

    if (pagination.total !== undefined) {
        document.getElementById('filteredSubmissions').textContent = `Showing: ${allSubmissions.length} of ${pagination.total}`;
    }

    if (pagination.page && pagination.pages) {
        hasMoreSubmissions = pagination.page < pagination.pages;
    }
}

// Reload submissions from backend when filters change
function reloadSubmissionsWithFilters() {
    console.log('Reloading submissions with new filters');
    currentOffset = 0;
    allSubmissions = [];
    filteredSubmissions = [];
    hasMoreSubmissions = true;
    backendTotalCount = 0;
    document.getElementById('submissionsTableBody').innerHTML = '';
    loadSubmissions();
}

// Setup event listeners
function setupEventListeners() {
    // Search box
    document.getElementById('searchBox').addEventListener('keyup', debounce(() => {
        applyFilters();
        updateClearFiltersButtonVisibility();
    }, 300));

    // Filter dropdowns
    document.getElementById('statusFilter').addEventListener('change', () => {
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

            if (currentSortField === sortField) {
                currentSortOrder = currentSortOrder === 'asc' ? 'desc' : 'asc';
            } else {
                currentSortField = sortField;
                currentSortOrder = 'desc';
            }

            updateSortIndicators();
            applyFilters();
        });
    });

    updateSortIndicators();

    // Intersection Observer for infinite scroll
    intersectionObserver = new IntersectionObserver((entries) => {
        if (entries[0].isIntersecting && hasMoreSubmissions && !isLoading) {
            console.log('Loading more submissions due to scroll');
            loadSubmissions(true);
        }
    }, {
        threshold: 0.1
    });

    intersectionObserver.observe(document.getElementById('scrollTrigger'));

    // Event delegation for copy buttons
    document.addEventListener('click', function(e) {
        if (e.target.closest('.copy-btn')) {
            const button = e.target.closest('.copy-btn');
            const textToCopy = button.getAttribute('data-copy-text');
            if (textToCopy) {
                copyToClipboard(textToCopy, button);
            }
        }
    });
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
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = text;
    const decodedText = tempDiv.textContent || tempDiv.innerText || '';

    navigator.clipboard.writeText(decodedText).then(() => {
        const originalIcon = button.innerHTML;
        button.innerHTML = '<span class="copy-icon">✓</span>';
        button.classList.add('copied');

        setTimeout(() => {
            button.innerHTML = originalIcon;
            button.classList.remove('copied');
        }, 1000);
    }).catch(err => {
        console.error('Failed to copy text: ', err);
        const textArea = document.createElement('textarea');
        textArea.value = decodedText;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);

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
    document.querySelectorAll('.logs-table th').forEach(th => {
        th.classList.remove('sorted-asc', 'sorted-desc');
    });

    const currentTh = document.querySelector(`.logs-table th[data-sort="${currentSortField}"]`);
    if (currentTh) {
        currentTh.classList.add(currentSortOrder === 'asc' ? 'sorted-asc' : 'sorted-desc');
    }
}

// Toggle message expansion for long messages
window.toggleMessageExpand = function(button) {
    const row = button.closest('tr');
    const messageText = row.querySelector('.message-text');
    const fullMessage = messageText.getAttribute('data-full-message');

    if (button.textContent === '▶') {
        messageText.textContent = fullMessage;
        button.textContent = '▼';
        button.title = 'Collapse message';
    } else {
        const truncated = fullMessage.length > 100 ? fullMessage.substring(0, 100) + '...' : fullMessage;
        messageText.textContent = truncated;
        button.textContent = '▶';
        button.title = 'Expand message';
    }
};

// Helper functions for message truncation
function needsExpand(message) {
    if (!message) return false;
    return message.length > 100 || message.includes('\n');
}

function truncateMessage(message) {
    if (!message) return '';
    if (message.length <= 100 && !message.includes('\n')) return message;
    if (message.includes('\n')) {
        const lines = message.split('\n');
        if (lines.length <= 2) return message;
        return lines.slice(0, 2).join('\n') + '\n... (' + (lines.length - 2) + ' more lines)';
    }
    return message.substring(0, 100) + '...';
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing contact submissions interface');
    setupEventListeners();

    // Set default status filter to "unread"
    document.getElementById('statusFilter').value = 'unread';

    updateClearFiltersButtonVisibility();
    loadSubmissions();
});
