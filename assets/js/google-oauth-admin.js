// google-oauth-admin.js - Google OAuth Administration Interface

class GoogleOAuthAdmin {
    constructor() {
        try {
            this.init();
        } catch (error) {
            console.error('Error initializing GoogleOAuthAdmin:', error);
            alert('Error: Failed to initialize Google OAuth admin. Please refresh the page.');
        }
    }

    init() {
        // Check for required elements before binding events
        const requiredElements = [
            'google-status-display',
            'google-status-text', 
            'google-connection-status',
            'google-connection-text',
            'result-messages'
        ];
        
        const missingElements = [];
        requiredElements.forEach(elementId => {
            if (!document.getElementById(elementId)) {
                missingElements.push(elementId);
            }
        });
        
        if (missingElements.length > 0) {
            console.error('Missing required elements:', missingElements);
            alert('Error: Required page elements not found. Please refresh the page.');
            return;
        }
        
        this.bindEvents();
        this.loadGoogleStatus();
    }

    bindEvents() {
        // Google Configuration Form
        const googleForm = document.getElementById('google-config-form');
        if (googleForm) {
            googleForm.addEventListener('submit', (e) => this.saveGoogleConfig(e));
        }

        // Google Action Buttons
        const testBtn = document.getElementById('test-google-connection');
        if (testBtn) testBtn.addEventListener('click', () => this.testGoogleConnection());

        const clearBtn = document.getElementById('clear-google-config');
        if (clearBtn) clearBtn.addEventListener('click', () => this.clearGoogleConfig());

        const authorizeBtn = document.getElementById('initiate-google-oauth');
        if (authorizeBtn) authorizeBtn.addEventListener('click', () => this.initiateGoogleAuth());

        const revokeBtn = document.getElementById('revoke-google-oauth');
        if (revokeBtn) revokeBtn.addEventListener('click', () => this.revokeGoogleAuth());

        const testApiBtn = document.getElementById('test-google-api');
        if (testApiBtn) testApiBtn.addEventListener('click', () => this.testGoogleAPI());

        const testProfileBtn = document.getElementById('test-profile-access');
        if (testProfileBtn) testProfileBtn.addEventListener('click', () => this.testProfileAccess());
    }

    async loadGoogleStatus() {
        try {
            const response = await fetch('/admin/google/oauth/status');
            if (response.ok) {
                const data = await response.json();
                this.updateGoogleStatus(data);
            } else {
                this.showMessage('Failed to load Google OAuth status', 'error');
            }
        } catch (error) {
            console.error('Error loading Google status:', error);
            this.showMessage('Error loading Google OAuth status', 'error');
        }
    }

    updateGoogleStatus(data) {
        const statusDisplay = document.getElementById('google-status-display');
        const statusText = document.getElementById('google-status-text');
        const connectionStatus = document.getElementById('google-connection-status');
        const connectionText = document.getElementById('google-connection-text');

        if (data.configured) {
            statusDisplay.className = 'status-configured';
            statusText.textContent = 'Google OAuth configured and ready';
            
            // Populate form with existing config
            document.getElementById('google-app-name').value = data.app_name || '';
            document.getElementById('google-client-id').value = data.client_id || '';
            document.getElementById('google-redirect-uri').value = data.redirect_uri || '';
        } else {
            statusDisplay.className = 'status-not-configured';
            statusText.textContent = 'Google OAuth not configured';
        }

        if (data.connected) {
            connectionStatus.className = 'status-configured';
            connectionText.textContent = 'Connected to Google';
            
            const details = document.getElementById('google-connection-details');
            details.style.display = 'block';
            document.getElementById('google-account-email').textContent = data.account_email || 'Unknown';
            document.getElementById('google-last-sync').textContent = data.last_sync || 'Never';
            document.getElementById('google-token-expiry').textContent = data.token_expiry || 'Unknown';
        } else {
            connectionStatus.className = 'status-not-configured';
            connectionText.textContent = 'Not connected to Google';
            document.getElementById('google-connection-details').style.display = 'none';
        }
    }

    async saveGoogleConfig(e) {
        e.preventDefault();
        
        const formData = new FormData(e.target);
        const config = Object.fromEntries(formData);

        try {
            const response = await fetch('/admin/google/oauth/config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(config)
            });

            if (response.ok) {
                const result = await response.json();
                this.showMessage('Google OAuth configuration saved successfully', 'success');
                this.loadGoogleStatus();
            } else {
                const error = await response.json();
                this.showMessage(`Failed to save Google configuration: ${error.detail}`, 'error');
            }
        } catch (error) {
            console.error('Error saving Google config:', error);
            this.showMessage('Error saving Google OAuth configuration', 'error');
        }
    }

    async testGoogleConnection() {
        const resultsDiv = document.getElementById('google-test-results');
        resultsDiv.style.display = 'block';
        resultsDiv.innerHTML = '<div class="test-results">Testing Google connection...</div>';

        try {
            const response = await fetch('/admin/google/oauth/test');
            const result = await response.json();

            if (response.ok) {
                resultsDiv.innerHTML = `<div class="test-success">✅ Google connection test passed: ${result.message}</div>`;
            } else {
                resultsDiv.innerHTML = `<div class="test-error">❌ Google connection test failed: ${result.detail}</div>`;
            }
        } catch (error) {
            console.error('Error testing Google connection:', error);
            resultsDiv.innerHTML = '<div class="test-error">❌ Google connection test failed: Network error</div>';
        }
    }

    async clearGoogleConfig() {
        if (!confirm('Are you sure you want to clear the Google OAuth configuration?')) {
            return;
        }

        try {
            const response = await fetch('/admin/google/oauth/config', {
                method: 'DELETE'
            });

            if (response.ok) {
                this.showMessage('Google OAuth configuration cleared', 'success');
                this.loadGoogleStatus();
                document.getElementById('google-config-form').reset();
            } else {
                const error = await response.json();
                this.showMessage(`Failed to clear Google configuration: ${error.detail}`, 'error');
            }
        } catch (error) {
            console.error('Error clearing Google config:', error);
            this.showMessage('Error clearing Google OAuth configuration', 'error');
        }
    }

    async initiateGoogleAuth() {
        try {
            const response = await fetch('/admin/google/oauth/authorize');
            if (response.ok) {
                const data = await response.json();
                window.location.href = data.auth_url;
            } else {
                const error = await response.json();
                this.showMessage(`Failed to initiate Google authorization: ${error.detail}`, 'error');
            }
        } catch (error) {
            console.error('Error initiating Google auth:', error);
            this.showMessage('Error initiating Google authorization', 'error');
        }
    }

    async revokeGoogleAuth() {
        if (!confirm('Are you sure you want to revoke Google access?')) {
            return;
        }

        try {
            const response = await fetch('/admin/google/oauth/revoke', {
                method: 'POST'
            });

            if (response.ok) {
                this.showMessage('Google access revoked successfully', 'success');
                this.loadGoogleStatus();
            } else {
                const error = await response.json();
                this.showMessage(`Failed to revoke Google access: ${error.detail}`, 'error');
            }
        } catch (error) {
            console.error('Error revoking Google auth:', error);
            this.showMessage('Error revoking Google access', 'error');
        }
    }

    async testGoogleAPI() {
        const resultsDiv = document.getElementById('google-test-results');
        resultsDiv.style.display = 'block';
        resultsDiv.innerHTML = '<div class="test-results">Testing Google API access...</div>';

        try {
            const response = await fetch('/admin/google/oauth/profile');
            const result = await response.json();

            if (response.ok) {
                resultsDiv.innerHTML = `<div class="test-success">✅ Google Profile API test passed: ${result.name} (${result.email})</div>`;
            } else {
                resultsDiv.innerHTML = `<div class="test-error">❌ Google Profile API test failed: ${result.detail}</div>`;
            }
        } catch (error) {
            console.error('Error testing Google API:', error);
            resultsDiv.innerHTML = '<div class="test-error">❌ Google Profile API test failed: Network error</div>';
        }
    }

    async testProfileAccess() {
        const resultsDiv = document.getElementById('google-test-results');
        if (!resultsDiv) {
            console.error('google-test-results element not found');
            alert('Error: Test results area not found on page');
            return;
        }
        
        resultsDiv.style.display = 'block';
        resultsDiv.innerHTML = '<div class="test-results">Testing Google Profile Access...</div>';

        try {
            const response = await fetch('/admin/google/oauth/profile');
            const result = await response.json();

            if (response.ok && result.status === 'success') {
                const profile = result.profile;
                const debug = result.debug_info;
                
                // Extract key profile information
                const primaryName = profile.names?.[0]?.displayName || 'N/A';
                const primaryEmail = profile.email_addresses?.[0]?.value || 'N/A';
                const profilePhoto = profile.photos?.[0]?.url || null;
                const resourceName = profile.resource_name || 'N/A';
                
                // Build comprehensive profile display
                let profileHtml = `
                    <div class="test-success">
                        ✅ Profile Access test passed<br>
                        <div style="margin-top: 10px;">
                            <strong>Name:</strong> ${primaryName}<br>
                            <strong>Email:</strong> ${primaryEmail}<br>
                            <strong>Resource ID:</strong> ${resourceName}<br>
                `;
                
                if (profilePhoto) {
                    profileHtml += `<strong>Profile Photo:</strong> <img src="${profilePhoto}" alt="Profile" style="width: 50px; height: 50px; border-radius: 25px; margin-left: 10px;"><br>`;
                }
                
                // Add counts of available data
                profileHtml += `
                            <br><strong>Available Data:</strong><br>
                            • Names: ${debug.total_names}<br>
                            • Emails: ${debug.total_emails}<br>
                            • Photos: ${debug.total_photos}<br>
                            • Phone Numbers: ${debug.total_phone_numbers}<br>
                            • Addresses: ${debug.total_addresses}<br>
                        </div>
                        <details style="margin-top: 10px;">
                            <summary><strong>Full Profile Data (Click to expand)</strong></summary>
                            <pre style="background: #f5f5f5; padding: 10px; border-radius: 4px; max-height: 300px; overflow-y: auto; font-size: 12px;">${JSON.stringify(profile, null, 2)}</pre>
                        </details>
                    </div>`;
                
                resultsDiv.innerHTML = profileHtml;
            } else {
                resultsDiv.innerHTML = `<div class="test-error">❌ Profile Access test failed: ${result.message || result.detail}</div>`;
            }
        } catch (error) {
            console.error('Error testing profile access:', error);
            resultsDiv.innerHTML = '<div class="test-error">❌ Profile Access test failed: Network error</div>';
        }
    }

    showMessage(message, type) {
        const container = document.getElementById('result-messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message-${type}`;
        messageDiv.textContent = message;
        
        container.appendChild(messageDiv);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (messageDiv.parentNode) {
                messageDiv.parentNode.removeChild(messageDiv);
            }
        }, 5000);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new GoogleOAuthAdmin();
});
