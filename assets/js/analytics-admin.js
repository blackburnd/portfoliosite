// Global variables for analytics
let allVisits = [];
let filteredVisits = [];
let currentOffset = 0;
let pageSize = 50;
let isLoading = false;
let hasMoreVisits = true;
let intersectionObserver;
let backendTotalCount = 0;
let currentSortField = 'timestamp';
let currentSortOrder = 'desc';

// Toggle collapsible sections
window.toggleSection = function (sectionId) {
    const content = document.getElementById(sectionId);
    const icon = document.getElementById(sectionId + 'Icon');

    if (content.style.display === 'none') {
        content.style.display = 'block';
        icon.textContent = '▼';
    } else {
        content.style.display = 'none';
        icon.textContent = '▶';
    }
};

// Show unique visitors popup
window.showUniqueVisitorsPopup = async function () {
    const modal = document.getElementById('uniqueVisitorsModal');
    const loading = document.getElementById('uniqueVisitorsLoading');
    const tbody = document.getElementById('uniqueVisitorsTableBody');

    // Show modal and loading state
    modal.style.display = 'block';
    loading.style.display = 'block';
    tbody.innerHTML = '';

    try {
        // Get current time filter
        const timeFilter = document.getElementById('timeFilter').value;
        const days = timeFilter === '1h' ? 0.04 :
            timeFilter === '24h' ? 1 :
                timeFilter === '7d' ? 7 :
                    timeFilter === '30d' ? 30 : 7;

        const response = await fetch(`/admin/analytics/unique-visitors?days=${days}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        // Populate table
        data.visitors.forEach(visitor => {
            const row = document.createElement('tr');
            const lastVisit = new Date(visitor.last_visit);
            const formattedLastVisit = lastVisit.toLocaleDateString() + ' ' + lastVisit.toLocaleTimeString();

            row.innerHTML = `
                <td>${visitor.ip_address}</td>
                <td>${visitor.total_views}</td>
                <td>${formattedLastVisit}</td>
            `;
            tbody.appendChild(row);
        });

    } catch (error) {
        console.error('Error loading unique visitors:', error);
        tbody.innerHTML = '<tr><td colspan="3" style="text-align: center; color: red;">Error loading visitor data</td></tr>';
    } finally {
        loading.style.display = 'none';
    }
};

// Close unique visitors popup
window.closeUniqueVisitorsPopup = function () {
    document.getElementById('uniqueVisitorsModal').style.display = 'none';
};

// Refresh analytics data
window.refreshAnalytics = function () {
    currentOffset = 0;
    allVisits = [];
    filteredVisits = [];
    hasMoreVisits = true;
    document.getElementById('analyticsTableBody').innerHTML = '';
    loadVisits();
};

// Clear filters
window.clearFilters = function () {
    document.getElementById('searchBox').value = '';
    document.getElementById('timeFilter').value = '7d';
    reloadVisitsWithFilters();
};

// Check if any filters are active
function hasActiveFilters() {
    const searchValue = document.getElementById('searchBox').value.trim();
    const timeFilter = document.getElementById('timeFilter').value;
    return searchValue !== '' || timeFilter !== '7d';
}

// Update clear filters button visibility
function updateClearFiltersButtonVisibility() {
    const clearBtn = document.getElementById('clearFiltersBtn');
    if (hasActiveFilters()) {
        clearBtn.style.display = 'block';
    } else {
        clearBtn.style.display = 'none';
    }
}

// Load visits with pagination
async function loadVisits(append = false) {
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
        const timeFilter = document.getElementById('timeFilter').value;

        if (searchValue) params.append('search', searchValue);
        if (timeFilter) {
            // Convert time filter to days
            const days = timeFilter === '1h' ? 0.04 :
                timeFilter === '24h' ? 1 :
                    timeFilter === '7d' ? 7 :
                        timeFilter === '30d' ? 30 : 7;
            params.append('days', days);
        }

        const response = await fetch(`/admin/analytics/recent-visits?${params}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (!append) {
            allVisits = [];
            filteredVisits = [];
            currentOffset = 0;
        }

        if (data.visits && data.visits.length > 0) {
            backendTotalCount = data.total_count || 0;

            if (append) {
                allVisits = allVisits.concat(data.visits);
            } else {
                allVisits = data.visits;
                currentOffset = 0; // Reset offset for fresh loads
            }

            currentOffset += data.visits.length;
            hasMoreVisits = data.has_more;

            // Since backend handles filtering, filtered visits = all loaded visits
            filteredVisits = allVisits;

            updateDisplay();
            updateStats();
            updateClearFiltersButtonVisibility();

            if (!hasMoreVisits) {
                document.getElementById('noMoreVisits').style.display = 'block';
            }
        } else {
            hasMoreVisits = false;
            document.getElementById('noMoreVisits').style.display = 'block';
            if (!append) {
                // Clear the display if this is a fresh load with no results
                allVisits = [];
                filteredVisits = [];
                updateDisplay();
                updateStats();
            }
        }

    } catch (error) {
        console.error('Error loading visits:', error);
        document.getElementById('errorMessage').textContent = `Error loading visits: ${error.message}`;
        document.getElementById('errorMessage').style.display = 'block';
    } finally {
        isLoading = false;
        document.getElementById('loadingIndicator').style.display = 'none';
    }
}

// Update the table display
function updateDisplay() {
    const tbody = document.getElementById('analyticsTableBody');
    tbody.innerHTML = '';

    if (filteredVisits.length === 0) {
        const row = document.createElement('tr');
        row.innerHTML = '<td colspan="11" style="text-align: center; padding: 20px;">No visits found</td>';
        tbody.appendChild(row);
        return;
    }

    filteredVisits.forEach(visit => {
        const row = document.createElement('tr');

        // Format timestamp
        const date = new Date(visit.timestamp);
        const formattedDate = date.toLocaleDateString() + ' ' + date.toLocaleTimeString();

        // Calculate age
        const age = getTimeAgo(date);

        // Truncate long user agents
        const userAgent = visit.user_agent ? (visit.user_agent.length > 40 ?
            visit.user_agent.substring(0, 40) + '...' : visit.user_agent) : '';

        // Truncate long referers
        const referer = visit.referer ? (visit.referer.length > 25 ?
            visit.referer.substring(0, 25) + '...' : visit.referer) : '';

        // Format mouse activity indicator
        const mouseActivity = visit.mouse_activity ? '✓' : '🤖';
        const mouseTitle = visit.mouse_activity ? 'Human activity detected' : 'Likely bot (no mouse activity)';

        // Format visitor type
        const visitorType = visit.visitor_type || 'unknown';
        const visitorTypeDisplay = visitorType.charAt(0).toUpperCase() + visitorType.slice(1);

        // Format reverse DNS
        const reverseDns = visit.reverse_dns ? (visit.reverse_dns.length > 30 ?
            visit.reverse_dns.substring(0, 30) + '...' : visit.reverse_dns) : '';

        // Format datacenter indicator
        const datacenterIndicator = visit.is_datacenter ? '🏢' : '';
        const datacenterTitle = visit.is_datacenter ? 'Datacenter/Cloud hosting' : 'Not a datacenter';

        // Format organization
        const organization = visit.organization ? (visit.organization.length > 25 ?
            visit.organization.substring(0, 25) + '...' : visit.organization) : '';

        row.innerHTML = `
            <td class="compact-td" title="${visit.timestamp}">${formattedDate}</td>
            <td class="compact-td" title="${age}">${age}</td>
            <td class="compact-td" title="${visit.page_path}">${visit.page_path}</td>
            <td class="compact-td" title="${visit.ip_address}">${visit.ip_address}</td>
            <td class="compact-td" title="${mouseTitle}" style="text-align: center;">${mouseActivity}</td>
            <td class="compact-td" title="Visitor Type: ${visitorType}" style="text-align: center;">${visitorTypeDisplay}</td>
            <td class="compact-td" title="${visit.reverse_dns || 'No reverse DNS'}">${reverseDns}</td>
            <td class="compact-td" title="${datacenterTitle}" style="text-align: center;">${datacenterIndicator}</td>
            <td class="compact-td" title="${visit.organization || 'Unknown organization'}">${organization}</td>
            <td class="compact-td" title="${visit.user_agent || ''}">${userAgent}</td>
            <td class="compact-td" title="${visit.referer || ''}">${referer}</td>
        `;

        tbody.appendChild(row);
    });
}

// Reload visits with current filters
function reloadVisitsWithFilters() {
    currentOffset = 0;
    allVisits = [];
    filteredVisits = [];
    hasMoreVisits = true;
    document.getElementById('analyticsTableBody').innerHTML = '';
    document.getElementById('noMoreVisits').style.display = 'none';
    document.getElementById('errorMessage').style.display = 'none';
    loadVisits();
}

// Get time ago string
function getTimeAgo(date) {
    const now = new Date();
    const diffMs = now - date;
    const diffMinutes = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMinutes / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMinutes < 1) return 'now';
    if (diffMinutes < 60) return `${diffMinutes}m`;
    if (diffHours < 24) return `${diffHours}h`;
    return `${diffDays}d`;
}

// Update stats
function updateStats() {
    document.getElementById('totalCount').textContent = `Total: ${backendTotalCount}`;
    document.getElementById('filteredVisits').textContent = `Loaded: ${allVisits.length}`;

    // Count unique IPs
    const uniqueIPs = new Set(allVisits.map(v => v.ip_address)).size;
    document.getElementById('uniqueVisitors').textContent = `Unique IPs: ${uniqueIPs}`;
}

// Setup intersection observer for infinite scroll
function setupIntersectionObserver() {
    const scrollTrigger = document.getElementById('scrollTrigger');
    if (!scrollTrigger) return;

    intersectionObserver = new IntersectionObserver((entries) => {
        if (entries[0].isIntersecting && hasMoreVisits && !isLoading) {
            loadVisits(true);
        }
    }, { threshold: 0.1 });

    intersectionObserver.observe(scrollTrigger);
}

// Setup sorting
function setupSorting() {
    document.querySelectorAll('.sortable').forEach(header => {
        header.addEventListener('click', () => {
            const field = header.getAttribute('data-sort');
            if (currentSortField === field) {
                currentSortOrder = currentSortOrder === 'asc' ? 'desc' : 'asc';
            } else {
                currentSortField = field;
                currentSortOrder = 'desc';
            }

            // Update sort indicators
            document.querySelectorAll('.sort-indicator').forEach(indicator => {
                indicator.textContent = '';
            });
            header.querySelector('.sort-indicator').textContent = currentSortOrder === 'asc' ? '↑' : '↓';

            reloadVisitsWithFilters();
        });
    });
}

// Debounce function
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

// Daily views chart functions
function drawDailyViewsChart(dailyViews) {
    const canvas = document.getElementById('dailyViewsChart');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (!dailyViews || dailyViews.length === 0) {
        // No data message
        ctx.fillStyle = '#666';
        ctx.font = '16px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('No daily view data available', canvas.width / 2, canvas.height / 2);
        ctx.fillText('Select a longer time period to see trends', canvas.width / 2, canvas.height / 2 + 25);
        return;
    }

    // Chart dimensions
    const padding = 60;
    const chartWidth = canvas.width - (padding * 2);
    const chartHeight = canvas.height - (padding * 2);
    const maxViews = Math.max(...dailyViews.map(d => d.views), 1);
    const barWidth = chartWidth / dailyViews.length;

    // Draw background grid
    ctx.strokeStyle = '#f0f0f0';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 5; i++) {
        const y = padding + (chartHeight * i / 5);
        ctx.beginPath();
        ctx.moveTo(padding, y);
        ctx.lineTo(canvas.width - padding, y);
        ctx.stroke();
    }

    // Draw bars
    dailyViews.forEach((day, index) => {
        const barHeight = (day.views / maxViews) * chartHeight;
        const x = padding + (index * barWidth);
        const y = canvas.height - padding - barHeight;

        // Bar background
        ctx.fillStyle = '#e3f2fd';
        ctx.fillRect(x + 2, canvas.height - padding - chartHeight, barWidth - 4, chartHeight);

        // Actual bar
        ctx.fillStyle = '#007acc';
        ctx.fillRect(x + 2, y, barWidth - 4, barHeight);

        // Bar border
        ctx.strokeStyle = '#005a9e';
        ctx.lineWidth = 1;
        ctx.strokeRect(x + 2, y, barWidth - 4, barHeight);

        // Date labels (rotate for better fit)
        ctx.save();
        ctx.translate(x + barWidth / 2, canvas.height - padding + 15);
        ctx.rotate(-Math.PI / 4);
        ctx.fillStyle = '#333';
        ctx.font = '11px Arial';
        ctx.textAlign = 'center';
        ctx.fillText(formatDateLabel(day.date), 0, 0);
        ctx.restore();

        // View count on top of bar (limit width to 1em)
        if (day.views > 0) {
            ctx.fillStyle = '#333';
            ctx.font = 'bold 12px Arial';
            ctx.textAlign = 'center';
            // Ensure text doesn't exceed 1em width by truncating if needed
            const text = day.views.toString();
            const textWidth = ctx.measureText(text).width;
            const maxWidth = 12; // 1em in pixels (approximation)
            if (textWidth > maxWidth) {
                // Truncate the text and add ellipsis
                const truncated = text.length > 3 ? text.substring(0, 2) + '…' : text;
                ctx.fillText(truncated, x + barWidth / 2, y - 5);
            } else {
                ctx.fillText(text, x + barWidth / 2, y - 5);
            }
        }
    });

    // Y-axis labels
    ctx.fillStyle = '#666';
    ctx.font = '11px Arial';
    ctx.textAlign = 'right';
    for (let i = 0; i <= 5; i++) {
        const value = Math.round(maxViews * (5 - i) / 5);
        const y = padding + (chartHeight * i / 5) + 4;
        ctx.fillText(value, padding - 10, y);
    }

    // Chart title
    ctx.fillStyle = '#333';
    ctx.font = 'bold 14px Arial';
    ctx.textAlign = 'center';
    ctx.fillText('Daily Page Views', canvas.width / 2, 25);

    // Y-axis title
    ctx.save();
    ctx.translate(20, canvas.height / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.fillStyle = '#666';
    ctx.font = '12px Arial';
    ctx.textAlign = 'center';
    ctx.fillText('Views', 0, 0);
    ctx.restore();
}

function formatDateLabel(dateStr) {
    const date = new Date(dateStr);
    return (date.getMonth() + 1) + '/' + date.getDate();
}

// Initialize analytics admin page
function initializeAnalyticsAdmin(dailyViewsData) {
    // Setup intersection observer and sorting
    setupIntersectionObserver();
    setupSorting();

    // Setup filter event listeners
    document.getElementById('searchBox').addEventListener('input',
        debounce(reloadVisitsWithFilters, 500));
    document.getElementById('timeFilter').addEventListener('change', reloadVisitsWithFilters);

    // Draw the daily views chart
    if (dailyViewsData) {
        drawDailyViewsChart(dailyViewsData);
    }

    // Initial load of visits
    loadVisits();
}

// Export for use in template
window.initializeAnalyticsAdmin = initializeAnalyticsAdmin;