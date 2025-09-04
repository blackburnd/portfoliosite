// oauth-admin.js - OAuth Administration Interface JavaScript
// Handles Google and LinkedIn OAuth configuration management

class OAuthAdmin {
    constructor() {
        this.initializeEventListeners();
        this.loadInitialStatus();
    }

    initializeEventListeners() {
        // Google OAuth form handlers
        const googleForm = document.getElementById('google-oauth-form');
        if (googleForm) {
            googleForm.addEventListener('submit', (e) => this.handleGoogleOAuthSubmit(e));
        }

        const googleTestBtn = document.getElementById('google-test-btn');
        if (googleTestBtn) {
            googleTestBtn.addEventListener('click', () => this.testGoogleOAuth());
        }

        const googleDisconnectBtn = document.getElementById('google-disconnect-btn');
        if (googleDisconnectBtn) {
            googleDisconnectBtn.addEventListener('click', () => this.disconnectGoogleOAuth());
        }

        // LinkedIn OAuth form handlers
        const linkedinForm = document.getElementById('linkedin-oauth-form');
        if (linkedinForm) {
            linkedinForm.addEventListener('submit', (e) => this.handleLinkedInOAuthSubmit(e));
        }

        const linkedinConnectBtn = document.getElementById('linkedin-connect-btn');
        if (linkedinConnectBtn) {
            linkedinConnectBtn.addEventListener('click', () => this.connectLinkedInOAuth());
        }

        const linkedinTestBtn = document.getElementById('linkedin-test-btn');
        if (linkedinTestBtn) {
            linkedinTestBtn.addEventListener('click', () => this.testLinkedInOAuth());
        }

        const linkedinDisconnectBtn = document.getElementById('linkedin-disconnect-btn');
        if (linkedinDisconnectBtn) {
            linkedinDisconnectBtn.addEventListener('click', () => this.disconnectLinkedInOAuth());
        }

        // Refresh status buttons
        const refreshStatusBtn = document.getElementById('refresh-status-btn');
        if (refreshStatusBtn) {
            refreshStatusBtn.addEventListener('click', () => this.loadInitialStatus());
        }
    }

    async loadInitialStatus() {
        await Promise.all([
            this.loadGoogleStatus(),
            this.loadLinkedInStatus()
        ]);
    }

    async loadGoogleStatus() {
        try {
            const response = await fetch('/admin/oauth/google/status');
            const data = await response.json();
            
            this.updateGoogleStatus(data);
        } catch (error) {
            console.error('Error loading Google OAuth status:', error);
            this.showMessage('Error loading Google OAuth status', 'error');
        }
    }

    async loadLinkedInStatus() {
        try {
            const response = await fetch('/admin/oauth/linkedin/status');
            const data = await response.json();
            
            this.updateLinkedInStatus(data);
        } catch (error) {
            console.error('Error loading LinkedIn OAuth status:', error);
            this.showMessage('Error loading LinkedIn OAuth status', 'error');
        }
    }

    updateGoogleStatus(data) {
        const statusDiv = document.getElementById('google-status');
        const formDiv = document.getElementById('google-form');
        const actionsDiv = document.getElementById('google-actions');

        if (data.configured && data.connected) {
            statusDiv.className = 'status-configured';
            statusDiv.textContent = 'Google OAuth is configured and connected';
            formDiv.classList.add('hidden');
            actionsDiv.classList.remove('hidden');
        } else if (data.configured) {
            statusDiv.className = 'status-not-configured';
            statusDiv.textContent = 'Google OAuth is configured but not connected';
            formDiv.classList.add('hidden');
            actionsDiv.classList.remove('hidden');
        } else {
            statusDiv.className = 'status-not-configured';
            statusDiv.textContent = data.message || 'Google OAuth is not configured';
            formDiv.classList.remove('hidden');
            actionsDiv.classList.add('hidden');
        }
    }

    updateLinkedInStatus(data) {
        const statusDiv = document.getElementById('linkedin-status');
        const formDiv = document.getElementById('linkedin-form');
        const actionsDiv = document.getElementById('linkedin-actions');

        if (data.app_configured && data.connected) {
            statusDiv.className = 'status-configured';
            statusDiv.textContent = 'LinkedIn OAuth is configured and connected';
            formDiv.classList.add('hidden');
            actionsDiv.classList.remove('hidden');
        } else if (data.app_configured) {
            statusDiv.className = 'status-not-configured';
            statusDiv.textContent = 'LinkedIn OAuth app is configured but not connected';
            formDiv.classList.add('hidden');
            actionsDiv.classList.remove('hidden');
        } else {
            statusDiv.className = 'status-not-configured';
            statusDiv.textContent = 'LinkedIn OAuth app is not configured';
            formDiv.classList.remove('hidden');
            actionsDiv.classList.add('hidden');
        }

        // Update form fields if configuration exists
        if (data.config) {
            const clientIdField = document.getElementById('linkedin-client-id');
            const redirectUriField = document.getElementById('linkedin-redirect-uri');
            
            if (clientIdField) clientIdField.value = data.config.client_id || '';
            if (redirectUriField) redirectUriField.value = data.config.redirect_uri || '';
        }
    }

    async handleGoogleOAuthSubmit(event) {
        event.preventDefault();
        
        const formData = new FormData(event.target);
        const data = {
            client_id: formData.get('client_id'),
            client_secret: formData.get('client_secret'),
            redirect_uri: formData.get('redirect_uri')
        };

        try {
            const response = await fetch('/admin/oauth/google/configure', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();
            
            if (response.ok && result.status === 'success') {
                this.showMessage('Google OAuth configured successfully', 'success');
                this.loadGoogleStatus();
            } else {
                this.showMessage(result.message || 'Failed to configure Google OAuth', 'error');
            }
        } catch (error) {
            console.error('Error configuring Google OAuth:', error);
            this.showMessage('Error configuring Google OAuth', 'error');
        }
    }

    async handleLinkedInOAuthSubmit(event) {
        event.preventDefault();
        
        const formData = new FormData(event.target);
        const data = {
            client_id: formData.get('client_id'),
            client_secret: formData.get('client_secret'),
            redirect_uri: formData.get('redirect_uri')
        };

        try {
            const response = await fetch('/admin/oauth/linkedin/configure', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();
            
            if (response.ok && result.status === 'success') {
                this.showMessage('LinkedIn OAuth configured successfully', 'success');
                this.loadLinkedInStatus();
            } else {
                this.showMessage(result.message || 'Failed to configure LinkedIn OAuth', 'error');
            }
        } catch (error) {
            console.error('Error configuring LinkedIn OAuth:', error);
            this.showMessage('Error configuring LinkedIn OAuth', 'error');
        }
    }

    async connectLinkedInOAuth() {
        try {
            // Get selected scopes
            const scopeCheckboxes = document.querySelectorAll('input[name="linkedin-scopes"]:checked');
            const selectedScopes = Array.from(scopeCheckboxes).map(cb => cb.value);

            const response = await fetch('/admin/oauth/linkedin/connect', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    scopes: selectedScopes
                })
            });

            const result = await response.json();
            
            if (response.ok && result.status === 'success') {
                // Redirect to LinkedIn authorization
                window.location.href = result.auth_url;
            } else {
                this.showMessage(result.message || 'Failed to initiate LinkedIn OAuth', 'error');
            }
        } catch (error) {
            console.error('Error connecting LinkedIn OAuth:', error);
            this.showMessage('Error connecting LinkedIn OAuth', 'error');
        }
    }

    async testGoogleOAuth() {
        try {
            const response = await fetch('/admin/oauth/google/test', {
                method: 'POST'
            });

            const result = await response.json();
            
            if (response.ok && result.status === 'success') {
                this.showMessage('Google OAuth test successful', 'success');
                this.displayTestResults('google', result);
            } else {
                this.showMessage(result.message || 'Google OAuth test failed', 'error');
            }
        } catch (error) {
            console.error('Error testing Google OAuth:', error);
            this.showMessage('Error testing Google OAuth', 'error');
        }
    }

    async testLinkedInOAuth() {
        try {
            const response = await fetch('/admin/oauth/linkedin/test', {
                method: 'POST'
            });

            const result = await response.json();
            
            if (response.ok && result.status === 'success') {
                this.showMessage('LinkedIn OAuth test successful', 'success');
                this.displayTestResults('linkedin', result);
            } else {
                this.showMessage(result.message || 'LinkedIn OAuth test failed', 'error');
            }
        } catch (error) {
            console.error('Error testing LinkedIn OAuth:', error);
            this.showMessage('Error testing LinkedIn OAuth', 'error');
        }
    }

    async disconnectGoogleOAuth() {
        if (!confirm('Are you sure you want to disconnect Google OAuth? This will remove all stored tokens.')) {
            return;
        }

        try {
            const response = await fetch('/admin/oauth/google/disconnect', {
                method: 'POST'
            });

            const result = await response.json();
            
            if (response.ok && result.status === 'success') {
                this.showMessage('Google OAuth disconnected successfully', 'success');
                this.loadGoogleStatus();
            } else {
                this.showMessage(result.message || 'Failed to disconnect Google OAuth', 'error');
            }
        } catch (error) {
            console.error('Error disconnecting Google OAuth:', error);
            this.showMessage('Error disconnecting Google OAuth', 'error');
        }
    }

    async disconnectLinkedInOAuth() {
        if (!confirm('Are you sure you want to disconnect LinkedIn OAuth? This will remove all stored tokens.')) {
            return;
        }

        try {
            const response = await fetch('/admin/oauth/linkedin/disconnect', {
                method: 'POST'
            });

            const result = await response.json();
            
            if (response.ok && result.status === 'success') {
                this.showMessage('LinkedIn OAuth disconnected successfully', 'success');
                this.loadLinkedInStatus();
            } else {
                this.showMessage(result.message || 'Failed to disconnect LinkedIn OAuth', 'error');
            }
        } catch (error) {
            console.error('Error disconnecting LinkedIn OAuth:', error);
            this.showMessage('Error disconnecting LinkedIn OAuth', 'error');
        }
    }

    displayTestResults(provider, result) {
        const resultsDiv = document.getElementById(`${provider}-test-results`);
        if (resultsDiv) {
            resultsDiv.innerHTML = `
                <div class="test-success">
                    <h4>Test Successful</h4>
                    ${result.profile ? `
                        <p><strong>Profile:</strong> ${result.profile.name}</p>
                        <p><strong>ID:</strong> ${result.profile.id}</p>
                        ${result.profile.profile_url ? `<p><strong>URL:</strong> <a href="${result.profile.profile_url}" target="_blank">${result.profile.profile_url}</a></p>` : ''}
                    ` : ''}
                </div>
            `;
            resultsDiv.classList.remove('hidden');
        }
    }

    showMessage(message, type = 'info') {
        // Remove any existing messages
        const existingMessages = document.querySelectorAll('.result-messages .message');
        existingMessages.forEach(msg => msg.remove());

        // Create new message
        const messageDiv = document.createElement('div');
        messageDiv.className = `message-${type}`;
        messageDiv.textContent = message;

        // Add to messages container
        let messagesContainer = document.querySelector('.result-messages');
        if (!messagesContainer) {
            messagesContainer = document.createElement('div');
            messagesContainer.className = 'result-messages';
            document.body.appendChild(messagesContainer);
        }
        
        messagesContainer.appendChild(messageDiv);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            messageDiv.remove();
        }, 5000);
    }
}

// Initialize OAuth admin when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new OAuthAdmin();
});
