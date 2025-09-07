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
        
        // Initialize permission status on page load
        this.resetPermissionStatus();
    }

    formatTimestamp() {
        const now = new Date();
        return now.toLocaleString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
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
        const connectionDetails = document.getElementById('google-connection-details');

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

        // Update connection status
        if (data.connected && data.account_email) {
            connectionStatus.className = 'status-configured';
            connectionText.textContent = 'Connected to Google';
            connectionDetails.style.display = 'block';
            
            document.getElementById('google-account-email').textContent = data.account_email;
            document.getElementById('google-last-sync').textContent = data.last_sync || 'Current session';
            document.getElementById('google-token-expiry').textContent = data.token_expiry || 'Unknown';
            
            // Automatically check scopes when connected
            this.checkGrantedScopes();
        } else {
            connectionStatus.className = 'status-not-configured';
            connectionText.textContent = 'Not connected to Google';
            connectionDetails.style.display = 'none';
            
            // Reset permission status indicators and show authorize button
            this.resetPermissionStatus();
            this.updateAuthorizationButtonVisibility(false);
        }
    }

    updateAuthorizationButtonVisibility(allPermissionsGranted) {
        const authorizeBtn = document.getElementById('initiate-google-oauth');
        if (authorizeBtn) {
            if (allPermissionsGranted) {
                authorizeBtn.style.display = 'none';
                authorizeBtn.setAttribute('title', 'All required permissions already granted');
            } else {
                authorizeBtn.style.display = 'inline-block';
                authorizeBtn.setAttribute('title', 'Click to grant Google OAuth permissions');
            }
        }
    }

    async checkGrantedScopes() {
        try {
            const response = await fetch('/admin/google/oauth/scopes');
            const result = await response.json();

            if (response.ok && result.status === 'success') {
                this.updatePermissionStatusFromScopes(result.scopes);
            } else {
                // If we can't get scopes, reset to unknown
                this.resetPermissionStatus();
            }
        } catch (error) {
            console.error('Error checking granted scopes:', error);
            this.resetPermissionStatus();
        }
    }

    updatePermissionStatusFromScopes(scopes) {
        // Update permission status based on actual granted scopes from Google
        const scopeElements = {
            'openid-status': scopes.openid,
            'email-status': scopes.email,
            'profile-status': scopes.profile,
            'gmail-send-status': scopes['https://www.googleapis.com/auth/gmail.send']
        };

        let allPermissionsGranted = true;
        const currentTime = this.formatTimestamp();

        Object.entries(scopeElements).forEach(([elementId, granted]) => {
            const element = document.getElementById(elementId);
            const scopeName = elementId.replace('-status', '');
            const revokeButton = document.getElementById(`revoke-${scopeName}`);
            
            if (element) {
                if (granted) {
                    element.innerHTML = `
                        <span class="status-granted">
                            ✅ Granted
                            <span class="permission-timestamp">Last checked: ${currentTime}</span>
                        </span>`;
                    // Show revoke button for granted scopes
                    if (revokeButton) {
                        revokeButton.style.display = 'inline-block';
                    }
                } else {
                    element.innerHTML = `
                        <span class="status-denied">
                            ❌ Denied
                            <span class="permission-timestamp">Last checked: ${currentTime}</span>
                        </span>`;
                    allPermissionsGranted = false;
                    // Hide revoke button for denied scopes
                    if (revokeButton) {
                        revokeButton.style.display = 'none';
                    }
                }
            }
        });

        // Update authorization button visibility
        this.updateAuthorizationButtonVisibility(allPermissionsGranted);
    }

    resetPermissionStatus() {
        // Reset all permission status indicators to unknown
        const permissionElements = ['openid-status', 'email-status', 'profile-status', 'gmail-send-status'];
        permissionElements.forEach(elementId => {
            const element = document.getElementById(elementId);
            const scopeName = elementId.replace('-status', '');
            const revokeButton = document.getElementById(`revoke-${scopeName}`);
            
            if (element) {
                element.innerHTML = '<span class="status-unknown">⚪ Unknown</span>';
            }
            // Hide revoke buttons when status is unknown
            if (revokeButton) {
                revokeButton.style.display = 'none';
            }
        });
        
        // Show authorize button when permissions are unknown
        this.updateAuthorizationButtonVisibility(false);
    }

    updatePermissionStatus(profileData) {
        // Update permission status based on successful profile data retrieval
        const permissions = {
            'openid-status': profileData.id ? 'granted' : 'denied',
            'email-status': profileData.email ? 'granted' : 'denied', 
            'profile-status': (profileData.name || profileData.picture) ? 'granted' : 'denied'
        };

        const currentTime = this.formatTimestamp();

        Object.entries(permissions).forEach(([elementId, status]) => {
            const element = document.getElementById(elementId);
            if (element) {
                if (status === 'granted') {
                    element.innerHTML = `
                        <span class="status-granted">
                            ✅ Granted
                            <span class="permission-timestamp">Last checked: ${currentTime}</span>
                        </span>`;
                } else {
                    element.innerHTML = `
                        <span class="status-denied">
                            ❌ Denied
                            <span class="permission-timestamp">Last checked: ${currentTime}</span>
                        </span>`;
                }
            }
        });
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
                
                // Show permission details before redirecting
                const permissionDetails = Object.entries(data.scope_descriptions)
                    .map(([scope, description]) => `• ${scope}: ${description}`)
                    .join('\n');
                
                const confirmMessage = `You will be asked to grant the following permissions:\n\n${permissionDetails}\n\nContinue to Google authorization?`;
                
                if (confirm(confirmMessage)) {
                    window.location.href = data.auth_url;
                }
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
        const revokeMessage = `Are you sure you want to revoke Google OAuth access?\n\nThis will:\n• Remove your Google authentication token\n• Clear your current Google session\n• Require re-authorization to access Google data\n\nNote: Your admin access to this site will remain intact.`;
        
        if (!confirm(revokeMessage)) {
            return;
        }

        try {
            const response = await fetch('/admin/google/oauth/revoke', {
                method: 'POST'
            });

            if (response.ok) {
                this.showMessage('Google access revoked successfully. Admin access remains active.', 'success');
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

    async revokeScope(scopeName) {
        // Map short scope names to full scope URLs
        const scopeMapping = {
            'openid': 'openid',
            'email': 'email', 
            'profile': 'profile',
            'gmail.send': 'https://www.googleapis.com/auth/gmail.send'
        };

        const fullScopeName = scopeMapping[scopeName] || scopeName;
        const revokeMessage = `Are you sure you want to revoke the "${scopeName}" scope?\n\nThis will remove access to this specific permission while keeping other Google OAuth permissions intact.`;
        
        if (!confirm(revokeMessage)) {
            return;
        }

        try {
            const response = await fetch('/admin/google/oauth/revoke-scope', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ scope: fullScopeName })
            });

            if (response.ok) {
                this.showMessage(`Successfully revoked "${scopeName}" scope.`, 'success');
                // Refresh the scope status to reflect the change
                await this.checkGrantedScopes();
            } else {
                const error = await response.json();
                this.showMessage(`Failed to revoke "${scopeName}" scope: ${error.detail}`, 'error');
            }
        } catch (error) {
            console.error('Error revoking scope:', error);
            this.showMessage(`Error revoking "${scopeName}" scope`, 'error');
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
            return;
        }
        
        resultsDiv.style.display = 'block';
        resultsDiv.innerHTML = '<div class="test-results">Testing Google Profile Access...</div>';

        try {
            const response = await fetch('/admin/google/oauth/profile');
            const result = await response.json();

            if (response.ok && result.status === 'success') {
                const data = result.data;
                
                // Update permission status indicators based on returned data
                this.updatePermissionStatus(data);
                
                // Also check actual granted scopes from Google
                this.checkGrantedScopes();
                
                resultsDiv.innerHTML = `
                    <div class="test-success">
                        ✅ Profile Access test passed - Required permissions working properly<br>
                        <strong>ID:</strong> ${data.id || 'N/A'}<br>
                        <strong>Name:</strong> ${data.name || 'N/A'}<br>
                        <strong>Email:</strong> ${data.email || 'N/A'}<br>
                        <strong>Picture:</strong> ${data.picture ? '<br><img src="' + data.picture + '" style="max-width: 100px; border-radius: 50%;">' : 'N/A'}<br>
                        <strong>Verified Email:</strong> ${data.verified_email || 'N/A'}<br>
                        <strong>Locale:</strong> ${data.locale || 'N/A'}
                    </div>`;
            } else {
                // Reset permission status on failure and check actual scopes
                this.resetPermissionStatus();
                this.checkGrantedScopes();
                resultsDiv.innerHTML = `<div class="test-error">❌ Profile Access test failed: ${result.message || result.detail}</div>`;
            }
        } catch (error) {
            console.error('Error testing profile access:', error);
            this.resetPermissionStatus();
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
