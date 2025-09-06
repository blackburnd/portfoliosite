// linkedin-oauth-admin.js - LinkedIn OAuth Administration Interface

class LinkedInOAuthAdmin {
    constructor() {
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadLinkedInStatus();
        this.loadLinkedInConfig();
    }

    bindEvents() {
        // LinkedIn Configuration Form
        const linkedinForm = document.getElementById('linkedin-config-form');
        if (linkedinForm) {
            linkedinForm.addEventListener('submit', (e) => this.saveLinkedInConfig(e));
        }

        // LinkedIn Action Buttons
        const testBtn = document.getElementById('test-linkedin-connection');
        if (testBtn) testBtn.addEventListener('click', () => this.testLinkedInConnection());

        const clearBtn = document.getElementById('clear-linkedin-config');
        if (clearBtn) clearBtn.addEventListener('click', () => this.clearLinkedInConfig());

        const authorizeBtn = document.getElementById('initiate-linkedin-oauth');
        if (authorizeBtn) authorizeBtn.addEventListener('click', () => this.initiateLinkedInAuth());

        const revokeBtn = document.getElementById('revoke-linkedin-oauth');
        if (revokeBtn) revokeBtn.addEventListener('click', () => this.revokeLinkedInAuth());

        const testApiBtn = document.getElementById('test-linkedin-api');
        if (testApiBtn) testApiBtn.addEventListener('click', () => this.testLinkedInAPI());

        const testProfileBtn = document.getElementById('test-profile-access');
        if (testProfileBtn) testProfileBtn.addEventListener('click', () => this.testProfileAccess());

        const testEmailBtn = document.getElementById('test-email-access');
        if (testEmailBtn) testEmailBtn.addEventListener('click', () => this.testEmailAccess());

        const testPositionsBtn = document.getElementById('test-positions-access');
        if (testPositionsBtn) testPositionsBtn.addEventListener('click', () => this.testPositionsAccess());

        const syncBtn = document.getElementById('sync-linkedin-data');
        if (syncBtn) syncBtn.addEventListener('click', () => this.syncLinkedInData());
    }

    async loadLinkedInStatus() {
        try {
            const response = await fetch('/admin/linkedin/oauth/status');
            if (response.ok) {
                const data = await response.json();
                this.updateLinkedInStatus(data);
            } else {
                this.showMessage('Failed to load LinkedIn OAuth status', 'error');
            }
        } catch (error) {
            console.error('Error loading LinkedIn status:', error);
            this.showMessage('Error loading LinkedIn OAuth status', 'error');
        }
    }

    async loadLinkedInConfig() {
        try {
            const response = await fetch('/admin/linkedin/config');
            if (response.ok) {
                const data = await response.json();
                this.updateLinkedInConfigForm(data);
            } else {
                this.showMessage('Failed to load LinkedIn OAuth configuration', 'error');
            }
        } catch (error) {
            console.error('Error loading LinkedIn config:', error);
            this.showMessage('Error loading LinkedIn OAuth configuration', 'error');
        }
    }

    updateLinkedInStatus(data) {
        const statusDisplay = document.getElementById('linkedin-status-display');
        const statusText = document.getElementById('linkedin-status-text');
        const connectionStatus = document.getElementById('linkedin-connection-status');
        const connectionText = document.getElementById('linkedin-connection-text');

        if (data.configured) {
            statusDisplay.className = 'status-configured';
            statusText.textContent = 'LinkedIn OAuth configured and ready';
            
            // Populate form with existing config
            document.getElementById('linkedin-app-name').value = data.app_name || '';
            document.getElementById('linkedin-client-id').value = data.client_id || '';
            document.getElementById('linkedin-client-secret').value = data.client_secret || '';
            document.getElementById('linkedin-redirect-uri').value = data.redirect_uri || '';
        } else {
            statusDisplay.className = 'status-not-configured';
            statusText.textContent = 'LinkedIn OAuth not configured';
        }

        if (data.connected) {
            connectionStatus.className = 'status-configured';
            connectionText.textContent = 'Connected to LinkedIn';
            
            const details = document.getElementById('linkedin-connection-details');
            details.style.display = 'block';
            document.getElementById('linkedin-account-email').textContent = data.account_email || 'Unknown';
            document.getElementById('linkedin-last-sync').textContent = data.last_sync || 'Never';
            document.getElementById('linkedin-token-expiry').textContent = data.token_expiry || 'Unknown';
        } else {
            connectionStatus.className = 'status-not-configured';
            connectionText.textContent = 'Not connected to LinkedIn';
            document.getElementById('linkedin-connection-details').style.display = 'none';
        }
    }

    updateLinkedInConfigForm(data) {
        // Populate LinkedIn OAuth configuration form with data
        document.getElementById('linkedin-app-name').value = data.app_name || '';
        document.getElementById('linkedin-client-id').value = data.client_id || '';
        document.getElementById('linkedin-client-secret').value = data.client_secret || '';
        document.getElementById('linkedin-redirect-uri').value = data.redirect_uri || '';
        document.getElementById('linkedin-scopes').value = data.scopes || '';
    }

    async saveLinkedInConfig(e) {
        e.preventDefault();
        
        const formData = new FormData(e.target);
        const config = Object.fromEntries(formData);

        try {
            const response = await fetch('/admin/linkedin/oauth/config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(config)
            });

            if (response.ok) {
                const result = await response.json();
                this.showMessage('LinkedIn OAuth configuration saved successfully', 'success');
                this.loadLinkedInStatus();
            } else {
                const error = await response.json();
                this.showMessage(`Failed to save LinkedIn configuration: ${error.detail}`, 'error');
            }
        } catch (error) {
            console.error('Error saving LinkedIn config:', error);
            this.showMessage('Error saving LinkedIn OAuth configuration', 'error');
        }
    }

    async testLinkedInConnection() {
        const resultsDiv = document.getElementById('linkedin-test-results');
        resultsDiv.style.display = 'block';
        resultsDiv.innerHTML = '<div class="test-results">Testing LinkedIn connection...</div>';

        try {
            const response = await fetch('/admin/linkedin/oauth/test');
            const result = await response.json();

            if (response.ok) {
                resultsDiv.innerHTML = `<div class="test-success">✅ LinkedIn connection test passed: ${result.message}</div>`;
            } else {
                resultsDiv.innerHTML = `<div class="test-error">❌ LinkedIn connection test failed: ${result.detail}</div>`;
            }
        } catch (error) {
            console.error('Error testing LinkedIn connection:', error);
            resultsDiv.innerHTML = '<div class="test-error">❌ LinkedIn connection test failed: Network error</div>';
        }
    }

    async clearLinkedInConfig() {
        if (!confirm('Are you sure you want to clear the LinkedIn OAuth configuration?')) {
            return;
        }

        try {
            const response = await fetch('/admin/linkedin/oauth/config', {
                method: 'DELETE'
            });

            if (response.ok) {
                this.showMessage('LinkedIn OAuth configuration cleared', 'success');
                this.loadLinkedInStatus();
                document.getElementById('linkedin-config-form').reset();
            } else {
                const error = await response.json();
                this.showMessage(`Failed to clear LinkedIn configuration: ${error.detail}`, 'error');
            }
        } catch (error) {
            console.error('Error clearing LinkedIn config:', error);
            this.showMessage('Error clearing LinkedIn OAuth configuration', 'error');
        }
    }

    async initiateLinkedInAuth() {
        try {
            const response = await fetch('/admin/linkedin/oauth/authorize');
            if (response.ok) {
                const data = await response.json();
                window.location.href = data.auth_url;
            } else {
                const error = await response.json();
                this.showMessage(`Failed to initiate LinkedIn authorization: ${error.detail}`, 'error');
            }
        } catch (error) {
            console.error('Error initiating LinkedIn auth:', error);
            this.showMessage('Error initiating LinkedIn authorization', 'error');
        }
    }

    async revokeLinkedInAuth() {
        if (!confirm('Are you sure you want to revoke LinkedIn access?')) {
            return;
        }

        try {
            const response = await fetch('/admin/linkedin/oauth/revoke', {
                method: 'POST'
            });

            if (response.ok) {
                this.showMessage('LinkedIn access revoked successfully', 'success');
                this.loadLinkedInStatus();
            } else {
                const error = await response.json();
                this.showMessage(`Failed to revoke LinkedIn access: ${error.detail}`, 'error');
            }
        } catch (error) {
            console.error('Error revoking LinkedIn auth:', error);
            this.showMessage('Error revoking LinkedIn access', 'error');
        }
    }

    async testLinkedInAPI() {
        const resultsDiv = document.getElementById('linkedin-test-results');
        resultsDiv.style.display = 'block';
        resultsDiv.innerHTML = '<div class="test-results">Testing LinkedIn API access...</div>';

        try {
            const response = await fetch('/admin/linkedin/oauth/test-api');
            const result = await response.json();

            if (response.ok) {
                resultsDiv.innerHTML = `<div class="test-success">✅ LinkedIn API test passed: ${result.message}</div>`;
            } else {
                resultsDiv.innerHTML = `<div class="test-error">❌ LinkedIn API test failed: ${result.detail}</div>`;
            }
        } catch (error) {
            console.error('Error testing LinkedIn API:', error);
            resultsDiv.innerHTML = '<div class="test-error">❌ LinkedIn API test failed: Network error</div>';
        }
    }

    async syncLinkedInData() {
        try {
            const response = await fetch('/admin/linkedin/sync', {
                method: 'POST'
            });

            if (response.ok) {
                const result = await response.json();
                this.showMessage(`LinkedIn data sync completed: ${result.message}`, 'success');
                this.loadLinkedInStatus();
            } else {
                const error = await response.json();
                this.showMessage(`LinkedIn sync failed: ${error.detail}`, 'error');
            }
        } catch (error) {
            console.error('Error syncing LinkedIn data:', error);
            this.showMessage('Error syncing LinkedIn data', 'error');
        }
    }

    async testProfileAccess() {
        const resultsDiv = document.getElementById('linkedin-test-results');
        resultsDiv.style.display = 'block';
        resultsDiv.innerHTML = '<div class="test-results">Testing LinkedIn Profile Access...</div>';

        try {
            const response = await fetch('/admin/linkedin/oauth/test-profile');
            const result = await response.json();

            if (response.ok) {
                const data = result.data;
                resultsDiv.innerHTML = `
                    <div class="test-success">
                        ✅ Profile Access test passed<br>
                        <strong>Name:</strong> ${data.name}<br>
                        <strong>Headline:</strong> ${data.headline}<br>
                        <strong>Profile ID:</strong> ${data.profile_id}
                    </div>`;
            } else {
                resultsDiv.innerHTML = `<div class="test-error">❌ Profile Access test failed: ${result.detail}</div>`;
            }
        } catch (error) {
            console.error('Error testing profile access:', error);
            resultsDiv.innerHTML = '<div class="test-error">❌ Profile Access test failed: Network error</div>';
        }
    }

    async testEmailAccess() {
        const resultsDiv = document.getElementById('linkedin-test-results');
        resultsDiv.style.display = 'block';
        resultsDiv.innerHTML = '<div class="test-results">Testing LinkedIn Email Access...</div>';

        try {
            const response = await fetch('/admin/linkedin/oauth/test-email');
            const result = await response.json();

            if (response.ok) {
                const data = result.data;
                resultsDiv.innerHTML = `
                    <div class="test-success">
                        ✅ Email Access test passed<br>
                        <strong>Email:</strong> ${data.email}
                    </div>`;
            } else {
                resultsDiv.innerHTML = `<div class="test-error">❌ Email Access test failed: ${result.detail}</div>`;
            }
        } catch (error) {
            console.error('Error testing email access:', error);
            resultsDiv.innerHTML = '<div class="test-error">❌ Email Access test failed: Network error</div>';
        }
    }

    async testPositionsAccess() {
        const resultsDiv = document.getElementById('linkedin-test-results');
        resultsDiv.style.display = 'block';
        resultsDiv.innerHTML = '<div class="test-results">Testing LinkedIn Position Data Access...</div>';

        try {
            const response = await fetch('/admin/linkedin/oauth/test-positions');
            const result = await response.json();

            if (response.ok) {
                const data = result.data;
                resultsDiv.innerHTML = `
                    <div class="test-success">
                        ✅ Position Data Access test passed<br>
                        <strong>Positions Count:</strong> ${data.positions_count}<br>
                        <strong>Data Available:</strong> ${data.positions_available ? 'Yes' : 'No'}
                    </div>`;
            } else {
                resultsDiv.innerHTML = `<div class="test-error">❌ Position Data Access test failed: ${result.detail}</div>`;
            }
        } catch (error) {
            console.error('Error testing positions access:', error);
            resultsDiv.innerHTML = '<div class="test-error">❌ Position Data Access test failed: Network error</div>';
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
    new LinkedInOAuthAdmin();
});
