// google-oauth-admin.js - Google OAuth Administration Interface

class GoogleOAuthAdmin {
    constructor() {
        try {
            this.init();
            // Listen for messages from OAuth popup
            window.addEventListener('message', (event) => {
                if (event.origin !== window.location.origin) return;
                
                if (event.data.type === 'OAUTH_SUCCESS') {
                    this.showMessage('Google authorization successful! Updating status...', 'success');
                    setTimeout(() => {
                        this.loadGoogleStatus();
                    }, 1000);
                } else if (event.data.type === 'OAUTH_CANCELLED') {
                    this.showMessage('Google authorization was cancelled.', 'warning');
                }
            });
        } catch (error) {
            console.error('Error initializing GoogleOAuthAdmin:', error);
        }
    }

    init() {
        // Check for required elements before binding events
        const requiredElements = [
            'google-status-display',
            'google-status-text', 
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
        const clearBtn = document.getElementById('clear-google-config');
        if (clearBtn) clearBtn.addEventListener('click', () => this.clearGoogleConfig());

        const authorizeBtn = document.getElementById('initiate-google-oauth');
        if (authorizeBtn) authorizeBtn.addEventListener('click', () => this.initiateGoogleAuth());

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

        if (data.configured) {
            statusDisplay.className = 'status-configured';
            statusText.textContent = 'Google OAuth configured and ready';
            
            // Populate form with existing config
            document.getElementById('google-client-id').value = data.client_id || '';
            document.getElementById('google-client-secret').value = data.client_secret || '';
            document.getElementById('google-redirect-uri').value = data.redirect_uri || '';
        } else {
            statusDisplay.className = 'status-not-configured';
            statusText.textContent = 'Google OAuth not configured';
        }

        // Check scopes if connected
        if (data.connected && data.account_email) {
            // Automatically check scopes when connected
            this.checkGrantedScopes();
        } else {
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
        
        // Reset scope data fields to defaults
        this.resetScopeDataFields();
        
        // Show authorize button when permissions are unknown
        this.updateAuthorizationButtonVisibility(false);
    }

    resetScopeDataFields() {
        // Reset to default placeholder values
        const openidData = document.getElementById('openid-data');
        if (openidData) openidData.innerHTML = 'User ID, basic profile';

        const emailData = document.getElementById('email-data');
        if (emailData) emailData.innerHTML = 'Primary email address';

        const profileData = document.getElementById('profile-data');
        if (profileData) profileData.innerHTML = 'Name, profile picture, locale';

        const gmailData = document.getElementById('gmail-send-data');
        if (gmailData) gmailData.innerHTML = 'Ability to send emails through Gmail API';
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
                this.openOAuthPopup(data.auth_url);
            } else {
                const error = await response.json();
                this.showMessage(`Failed to initiate Google authorization: ${error.detail}`, 'error');
            }
        } catch (error) {
            console.error('Error initiating Google auth:', error);
            this.showMessage('Error initiating Google authorization', 'error');
        }
    }

    openOAuthPopup(authUrl) {
        // Calculate popup dimensions and position
        const width = 500;
        const height = 600;
        const left = (window.screen.width / 2) - (width / 2);
        const top = (window.screen.height / 2) - (height / 2);
        
        // Open popup window
        const popup = window.open(
            authUrl,
            'googleOAuth',
            `width=${width},height=${height},left=${left},top=${top},scrollbars=yes,resizable=yes,status=yes,location=yes`
        );
        
        if (!popup) {
            this.showMessage('Popup blocked! Please allow popups for this site and try again.', 'error');
            return;
        }
        
        // Monitor popup for completion
        this.monitorOAuthPopup(popup);
    }

    monitorOAuthPopup(popup) {
        const checkClosed = setInterval(() => {
            if (popup.closed) {
                clearInterval(checkClosed);
                // Popup was closed, but we'll rely on postMessage for success notification
                // Only show this message if we haven't received a postMessage
                setTimeout(() => {
                    // Check if status has been updated, if not show generic message
                    this.loadGoogleStatus();
                }, 1000);
                return;
            }
            
            try {
                // Check if popup has navigated back to our domain (indicates completion)
                const popupUrl = popup.location.href;
                if (popupUrl.includes(window.location.origin)) {
                    // We're back on our domain, the callback should handle the rest
                    // Keep monitoring as the popup should close itself
                }
            } catch (e) {
                // Cross-origin error is expected while on Google's domain
                // Continue monitoring
            }
        }, 1000);
        
        // Set a timeout to stop monitoring after 10 minutes
        setTimeout(() => {
            if (!popup.closed) {
                clearInterval(checkClosed);
                popup.close();
                this.showMessage('OAuth process timed out. Please try again.', 'warning');
            }
        }, 600000); // 10 minutes
    }

    async revokeGoogleAuth() {
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

    async testProfileAccess() {
        try {
            const response = await fetch('/admin/google/oauth/profile');
            const result = await response.json();

            if (response.ok && result.status === 'success') {
                const data = result.data;
                
                // Update permission status indicators based on returned data
                this.updatePermissionStatus(data);
                
                // Also check actual granted scopes from Google
                this.checkGrantedScopes();
                
                // Populate the scope data fields with actual values
                this.updateScopeDataFields(data);
                
                this.showMessage('✅ Google data fetched successfully!', 'success');
            } else {
                // Reset permission status on failure and check actual scopes
                this.resetPermissionStatus();
                this.checkGrantedScopes();
                this.showMessage(`❌ Failed to fetch Google data: ${result.message || result.detail}`, 'error');
            }
        } catch (error) {
            console.error('Error testing profile access:', error);
            this.resetPermissionStatus();
            this.showMessage('❌ Failed to fetch Google data: Network error', 'error');
        }
    }

    updateScopeDataFields(data) {
        // Update OpenID data
        const openidData = document.getElementById('openid-data');
        if (openidData && data.id) {
            openidData.innerHTML = `User ID: ${data.id}`;
        }

        // Update Email data
        const emailData = document.getElementById('email-data');
        if (emailData && data.email) {
            const verifiedText = data.verified_email ? ' (Verified)' : ' (Unverified)';
            emailData.innerHTML = `${data.email}${verifiedText}`;
        }

        // Update Profile data
        const profileData = document.getElementById('profile-data');
        if (profileData) {
            let profileHtml = '';
            if (data.name) {
                profileHtml += `Name: ${data.name}`;
            }
            if (data.picture) {
                profileHtml += `<br><img src="${data.picture}" style="max-width: 40px; height: 40px; border-radius: 50%; margin-top: 5px; object-fit: cover;" alt="Profile Picture">`;
            }
            if (data.locale) {
                profileHtml += `<br>Locale: ${data.locale}`;
            }
            if (profileHtml) {
                profileData.innerHTML = profileHtml;
            }
        }

        // Gmail send data remains static since we don't fetch Gmail-specific data
        const gmailData = document.getElementById('gmail-send-data');
        if (gmailData) {
            gmailData.innerHTML = 'Gmail API access enabled for sending emails';
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
    window.googleOAuthAdmin = new GoogleOAuthAdmin();
});
