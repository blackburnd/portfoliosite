// google-oauth-admin.js - Google OAuth Administration Interface

class GoogleOAuthAdmin {
    constructor() {
        this.init();
    }

    init() {
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
            document.getElementById('google-client-secret').value = data.client_secret || '';
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

    async testProfileAccess() {
        const statusSpan = document.getElementById('profile-test-status');
        const resultsDiv = document.getElementById('profile-test-results');
        
        // Show loading state
        statusSpan.textContent = 'Testing...';
        statusSpan.className = 'test-status testing';
        resultsDiv.style.display = 'block';
        resultsDiv.innerHTML = '<div class="test-results">Retrieving Google profile information...</div>';

        try {
            const response = await fetch('/admin/google/oauth/profile');
            const result = await response.json();

            if (response.ok && result.status === 'success') {
                statusSpan.textContent = '✅ Success';
                statusSpan.className = 'test-status success';
                
                const profile = result.profile;
                const debugInfo = result.debug_info;
                const sessionInfo = result.session_info;
                
                let profileHtml = `
                    <div class="test-success">
                        <h4>✅ Profile Access Successful</h4>
                        <div class="profile-data">
                            <div class="profile-section">
                                <h5>Profile Information</h5>
                                <div class="data-item"><strong>Name:</strong> ${profile.name || 'N/A'}</div>
                                <div class="data-item"><strong>Email:</strong> ${profile.email || 'N/A'}</div>
                                <div class="data-item"><strong>Google ID:</strong> ${profile.id || 'N/A'}</div>
                                <div class="data-item"><strong>Verified Email:</strong> ${profile.verified_email || 'N/A'}</div>
                                <div class="data-item"><strong>Locale:</strong> ${profile.locale || 'N/A'}</div>
                                <div class="data-item"><strong>Profile Picture:</strong> ${profile.picture ? 'Available' : 'Not available'}</div>
                            </div>
                            
                            <div class="profile-section">
                                <h5>Debug Information</h5>
                                <div class="data-item"><strong>API Endpoint:</strong> ${debugInfo.api_endpoint}</div>
                                <div class="data-item"><strong>User Verified Email:</strong> ${debugInfo.user_verified_email}</div>
                                <div class="data-item"><strong>Profile Picture Available:</strong> ${debugInfo.profile_picture_available}</div>
                                <div class="data-item"><strong>Google User ID:</strong> ${debugInfo.google_user_id}</div>
                            </div>
                            
                            <div class="profile-section">
                                <h5>Session Information</h5>
                                <div class="data-item"><strong>Token Length:</strong> ${sessionInfo.token_length} characters</div>
                                <div class="data-item"><strong>Session Email:</strong> ${sessionInfo.session_user_email || 'N/A'}</div>
                                <div class="data-item"><strong>Session Expires:</strong> ${sessionInfo.session_expires_at || 'N/A'}</div>
                            </div>
                        </div>
                `;
                
                if (profile.picture) {
                    profileHtml += `
                        <div class="profile-section">
                            <h5>Profile Picture</h5>
                            <img src="${profile.picture}" alt="Profile Picture" style="max-width: 100px; border-radius: 50px;">
                        </div>
                    `;
                }
                
                profileHtml += '</div>';
                resultsDiv.innerHTML = profileHtml;
                
            } else if (response.status === 401) {
                statusSpan.textContent = '⚠️ Auth Required';
                statusSpan.className = 'test-status warning';
                resultsDiv.innerHTML = `
                    <div class="test-warning">
                        <h4>⚠️ Authorization Required</h4>
                        <p>${result.message}</p>
                        <p>Please click "Authorize Google Access" button to grant permission first.</p>
                    </div>
                `;
                
            } else {
                statusSpan.textContent = '❌ Failed';
                statusSpan.className = 'test-status error';
                resultsDiv.innerHTML = `
                    <div class="test-error">
                        <h4>❌ Profile Access Failed</h4>
                        <p><strong>Error:</strong> ${result.message}</p>
                        ${result.details ? `<p><strong>Details:</strong> ${result.details}</p>` : ''}
                    </div>
                `;
            }
            
        } catch (error) {
            console.error('Error testing profile access:', error);
            statusSpan.textContent = '❌ Error';
            statusSpan.className = 'test-status error';
            resultsDiv.innerHTML = `
                <div class="test-error">
                    <h4>❌ Network Error</h4>
                    <p>Failed to contact the server: ${error.message}</p>
                </div>
            `;
        }
    }

    async testGoogleAPI() {
        const resultsDiv = document.getElementById('google-test-results');
        resultsDiv.style.display = 'block';
        resultsDiv.innerHTML = '<div class="test-results">Testing Google API access...</div>';

        try {
            const response = await fetch('/admin/google/oauth/test-api');
            const result = await response.json();

            if (response.ok) {
                resultsDiv.innerHTML = `<div class="test-success">✅ Google API test passed: ${result.message}</div>`;
            } else {
                resultsDiv.innerHTML = `<div class="test-error">❌ Google API test failed: ${result.detail}</div>`;
            }
        } catch (error) {
            console.error('Error testing Google API:', error);
            resultsDiv.innerHTML = '<div class="test-error">❌ Google API test failed: Network error</div>';
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
