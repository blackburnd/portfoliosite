/**
 * LinkedIn Admin Interface JavaScript
 * Handles configuration, OAuth connection, and sync operations
 */

class LinkedInAdmin {
    constructor() {
        // Global state
        this.linkedinConfigured = false;
        this.oauthConnected = false;
        
        // DOM elements cache
        this.elements = {};
        
        // Initialize when DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.init());
        } else {
            this.init();
        }
    }
    
    init() {
        this.cacheElements();
        this.bindEvents();
        this.loadInitialData();
    }
    
    cacheElements() {
        // Status and sync elements
        this.elements.statusContent = document.getElementById('status-content');
        this.elements.syncProfile = document.getElementById('syncProfile');
        this.elements.syncExperience = document.getElementById('syncExperience');
        this.elements.syncFull = document.getElementById('syncFull');
        this.elements.syncStatus = document.getElementById('sync-status');
        
        // Configuration elements
        this.elements.configForm = document.getElementById('linkedin-config-form');
        this.elements.testConfigBtn = document.getElementById('test-config-btn');
        this.elements.configStatusDiv = document.getElementById('config-status');
        this.elements.configDetailsDiv = document.getElementById('config-details');
        
        // OAuth elements
        this.elements.connectLinkedinBtn = document.getElementById('connect-linkedin-btn');
        this.elements.disconnectLinkedinBtn = document.getElementById('disconnect-linkedin-btn');
        this.elements.notConnectedDiv = document.getElementById('not-connected');
        this.elements.connectedDiv = document.getElementById('connected');
        this.elements.connectionDetailsDiv = document.getElementById('connection-details');
        
        // Result elements
        this.elements.resultSuccess = document.getElementById('result-success');
        this.elements.resultError = document.getElementById('result-error');
        this.elements.resultInfo = document.getElementById('result-info');
        this.elements.successContent = document.getElementById('success-content');
        this.elements.errorContent = document.getElementById('error-content');
        this.elements.infoContent = document.getElementById('info-content');
    }
    
    bindEvents() {
        // Sync button events
        if (this.elements.syncProfile) {
            this.elements.syncProfile.addEventListener('click', () => this.performSync('profile'));
        }
        if (this.elements.syncExperience) {
            this.elements.syncExperience.addEventListener('click', () => this.performSync('experience'));
        }
        if (this.elements.syncFull) {
            this.elements.syncFull.addEventListener('click', () => this.performSync('full'));
        }
        
        // Configuration events
        if (this.elements.configForm) {
            this.elements.configForm.addEventListener('submit', (e) => this.saveLinkedInConfig(e));
        }
        if (this.elements.testConfigBtn) {
            this.elements.testConfigBtn.addEventListener('click', () => this.testConfiguration());
        }
        
        // OAuth events
        if (this.elements.connectLinkedinBtn) {
            this.elements.connectLinkedinBtn.addEventListener('click', () => this.connectLinkedIn());
        }
        if (this.elements.disconnectLinkedinBtn) {
            this.elements.disconnectLinkedinBtn.addEventListener('click', () => this.disconnectLinkedIn());
        }
    }
    
    loadInitialData() {
        this.loadConfigurationStatus();
        this.loadLinkedInConfig();
    }
    
    async loadLinkedInConfig() {
        try {
            const response = await fetch('/admin/linkedin/config', {
                headers: { 'Accept': 'application/json' }
            });
            
            if (response.ok) {
                const config = await response.json();
                
                // Populate form fields
                this.populateConfigForm(config);
                this.updateConfigStatus(config);
                
                // Enable connect button if configuration is complete
                const isConfigured = config.client_id && config.client_secret;
                if (this.elements.connectLinkedinBtn) {
                    this.elements.connectLinkedinBtn.disabled = !isConfigured;
                }
                
            } else {
                if (this.elements.configDetailsDiv) {
                    this.elements.configDetailsDiv.innerHTML = 
                        '<p style="color: #666;">No configuration found. Please enter your LinkedIn app settings above.</p>';
                }
            }
        } catch (error) {
            console.error('Error loading LinkedIn config:', error);
            if (this.elements.configDetailsDiv) {
                this.elements.configDetailsDiv.innerHTML = '<p style="color: red;">Error loading configuration</p>';
            }
        }
    }
    
    populateConfigForm(config) {
        const fields = [
            { id: 'app_name', value: config.app_name || 'blackburnsystems profile site' },
            { id: 'client_id', value: config.client_id || '' },
            { id: 'client_secret', value: config.client_secret || '' },
            { id: 'redirect_uri', value: config.redirect_uri || 'https://www.blackburnsystems.com/admin/linkedin/callback' },
            { id: 'scopes', value: config.scopes || 'r_liteprofile,r_emailaddress' }
        ];
        
        fields.forEach(field => {
            const element = document.getElementById(field.id);
            if (element) {
                element.value = field.value;
            }
        });
    }
    
    async saveLinkedInConfig(event) {
        event.preventDefault();
        
        const formData = new FormData(this.elements.configForm);
        const config = {
            app_name: formData.get('app_name'),
            client_id: formData.get('client_id'),
            client_secret: formData.get('client_secret'),
            redirect_uri: formData.get('redirect_uri'),
            scopes: formData.get('scopes')
        };
        
        try {
            const response = await fetch('/admin/linkedin/config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(config)
            });
            
            if (response.ok) {
                this.updateConfigStatus(config);
                this.showMessage('Configuration saved successfully!', 'success');
                
                // Enable connect button
                if (this.elements.connectLinkedinBtn) {
                    this.elements.connectLinkedinBtn.disabled = false;
                }
                const noteElement = document.querySelector('#not-connected .note');
                if (noteElement) {
                    noteElement.style.display = 'none';
                }
            } else {
                const error = await response.json();
                this.showMessage(`Error saving configuration: ${error.detail}`, 'error');
            }
        } catch (error) {
            console.error('Error saving configuration:', error);
            this.showMessage('Error saving configuration', 'error');
        }
    }
    
    async testConfiguration() {
        try {
            this.elements.testConfigBtn.disabled = true;
            this.elements.testConfigBtn.textContent = 'Testing...';
            
            const response = await fetch('/admin/linkedin/test-config', {
                method: 'POST',
                headers: { 'Accept': 'application/json' }
            });
            
            const result = await response.json();
            
            if (response.ok && result.valid) {
                this.showMessage('Configuration test successful!', 'success');
            } else {
                this.showMessage(`Configuration test failed: ${result.error || 'Unknown error'}`, 'error');
            }
        } catch (error) {
            console.error('Error testing configuration:', error);
            this.showMessage('Error testing configuration', 'error');
        } finally {
            this.elements.testConfigBtn.disabled = false;
            this.elements.testConfigBtn.textContent = 'Test Connection';
        }
    }
    
    updateConfigStatus(config) {
        const hasClientId = config.client_id && config.client_id.length > 0;
        const hasClientSecret = config.client_secret && config.client_secret.length > 0;
        const hasRedirectUri = config.redirect_uri && config.redirect_uri.length > 0;
        
        const statusItems = [
            { label: 'App Name', value: config.app_name || 'Not set', type: 'info' },
            { label: 'Client ID', value: hasClientId ? '✅ Configured' : '❌ Missing', type: hasClientId ? 'configured' : 'missing' },
            { label: 'Client Secret', value: hasClientSecret ? '✅ Configured' : '❌ Missing', type: hasClientSecret ? 'configured' : 'missing' },
            { label: 'Redirect URI', value: hasRedirectUri ? '✅ Configured' : '❌ Missing', type: hasRedirectUri ? 'configured' : 'missing' },
            { label: 'Scopes', value: config.scopes || 'Default', type: 'info' }
        ];
        
        let statusHtml = '<div class="config-items">';
        statusItems.forEach(item => {
            statusHtml += `<div class="config-item">
                <span class="config-label">${item.label}:</span>
                <span class="config-value ${item.type}">${item.value}</span>
            </div>`;
        });
        statusHtml += '</div>';
        
        if (this.elements.configDetailsDiv) {
            this.elements.configDetailsDiv.innerHTML = statusHtml;
        }
    }
    
    async connectLinkedIn() {
        try {
            const response = await fetch('/admin/linkedin/oauth/start', {
                method: 'POST',
                headers: { 'Accept': 'application/json' }
            });
            
            if (response.ok) {
                const result = await response.json();
                // Redirect to LinkedIn OAuth
                window.location.href = result.authorization_url;
            } else {
                const error = await response.json();
                this.showMessage(`Error starting OAuth: ${error.detail}`, 'error');
            }
        } catch (error) {
            console.error('Error connecting LinkedIn:', error);
            this.showMessage('Error connecting to LinkedIn', 'error');
        }
    }
    
    async disconnectLinkedIn() {
        if (!confirm('Are you sure you want to disconnect your LinkedIn account?')) {
            return;
        }
        
        try {
            const response = await fetch('/admin/linkedin/oauth/disconnect', {
                method: 'POST',
                headers: { 'Accept': 'application/json' }
            });
            
            if (response.ok) {
                this.showMessage('LinkedIn account disconnected successfully', 'success');
                // Refresh the page to update the UI
                setTimeout(() => location.reload(), 1000);
            } else {
                const error = await response.json();
                this.showMessage(`Error disconnecting: ${error.detail}`, 'error');
            }
        } catch (error) {
            console.error('Error disconnecting LinkedIn:', error);
            this.showMessage('Error disconnecting LinkedIn account', 'error');
        }
    }
    
    async loadConfigurationStatus() {
        try {
            const response = await fetch('/linkedin/status', {
                headers: {
                    'Accept': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            this.displayConfigurationStatus(data.linkedin_sync);
            
        } catch (error) {
            console.error('Error loading configuration status:', error);
            if (this.elements.statusContent) {
                this.elements.statusContent.innerHTML = `
                    <div style="color: red;">
                        ❌ Error loading configuration: ${error.message}
                    </div>
                `;
            }
        }
    }
    
    displayConfigurationStatus(config) {
        // Check OAuth status
        const oauth = config.oauth || {};
        this.oauthConnected = oauth.connected && oauth.token_valid;
        this.linkedinConfigured = this.oauthConnected || config.legacy_configured;
        
        // Update OAuth connection display
        if (this.oauthConnected) {
            // Show connected state
            if (this.elements.notConnectedDiv) this.elements.notConnectedDiv.style.display = 'none';
            if (this.elements.connectedDiv) this.elements.connectedDiv.style.display = 'block';
            
            // Update connection details
            if (this.elements.connectionDetailsDiv) {
                this.elements.connectionDetailsDiv.innerHTML = `
                    <div><strong>Profile ID:</strong> ${oauth.linkedin_profile_id || 'Not available'}</div>
                    <div><strong>Token Expires:</strong> ${oauth.expires_at ? new Date(oauth.expires_at).toLocaleString() : 'Unknown'}</div>
                    <div><strong>Status:</strong> ${oauth.token_valid ? 'Active' : 'Expired'}</div>
                `;
            }
        } else {
            // Show not connected state
            if (this.elements.notConnectedDiv) this.elements.notConnectedDiv.style.display = 'block';
            if (this.elements.connectedDiv) this.elements.connectedDiv.style.display = 'none';
        }
        
        // Update main status display
        this.updateMainStatus(config);
        
        // Enable/disable sync buttons
        this.updateSyncButtons(config);
    }
    
    updateMainStatus(config) {
        if (!this.elements.statusContent) return;
        
        if (this.oauthConnected) {
            this.elements.statusContent.innerHTML = `
                <div class="status-item">
                    <span class="status-label">Status:</span>
                    <span class="status-value">
                        <span class="status-indicator configured"></span>
                        LinkedIn Account Connected via OAuth 2.0
                    </span>
                </div>
                <div class="status-item">
                    <span class="status-label">Portfolio ID:</span>
                    <span class="status-value">${config.portfolio_id}</span>
                </div>
            `;
        } else {
            const authMethod = config.legacy_configured ? 'Environment Variables (Deprecated)' : 'Not Configured';
            const authIndicator = config.legacy_configured ? 
                '<span class="status-indicator deprecated"></span>' : 
                '<span class="status-indicator not-configured"></span>';
            
            this.elements.statusContent.innerHTML = `
                <div class="status-item">
                    <span class="status-label">Status:</span>
                    <span class="status-value">
                        <span class="status-indicator not-configured"></span>
                        LinkedIn Account Not Connected
                    </span>
                </div>
                <div class="status-item">
                    <span class="status-label">Authentication:</span>
                    <span class="status-value">${authIndicator}${authMethod}</span>
                </div>
                <div class="status-item">
                    <span class="status-label">Portfolio ID:</span>
                    <span class="status-value">${config.portfolio_id}</span>
                </div>
            `;
        }
    }
    
    updateSyncButtons(config) {
        const buttons = [this.elements.syncProfile, this.elements.syncExperience, this.elements.syncFull];
        
        if (this.oauthConnected) {
            buttons.forEach(btn => {
                if (btn) btn.disabled = false;
            });
            if (this.elements.syncStatus) {
                this.elements.syncStatus.textContent = 'Ready to sync with LinkedIn';
            }
        } else if (config.legacy_configured) {
            buttons.forEach(btn => {
                if (btn) btn.disabled = false;
            });
            if (this.elements.syncStatus) {
                this.elements.syncStatus.textContent = 'Ready to sync (using legacy configuration)';
            }
        } else {
            buttons.forEach(btn => {
                if (btn) btn.disabled = true;
            });
            if (this.elements.syncStatus) {
                this.elements.syncStatus.textContent = 'Connect LinkedIn account to enable sync';
            }
        }
    }
    
    async performSync(syncType) {
        const button = document.getElementById(`sync${syncType.charAt(0).toUpperCase() + syncType.slice(1)}`);
        if (!button) return;
        
        const originalText = button.textContent;
        button.disabled = true;
        button.innerHTML = `<span class="loading"></span> Syncing...`;
        
        if (this.elements.syncStatus) {
            this.elements.syncStatus.textContent = `Syncing ${syncType}...`;
        }
        
        this.hideAllResults();
        
        try {
            const response = await fetch(`/linkedin/sync/${syncType}`, {
                method: 'POST',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            });
            
            const result = await response.json();
            
            if (response.ok) {
                let successMessage = `${syncType.charAt(0).toUpperCase() + syncType.slice(1)} sync completed successfully!`;
                if (result.message) {
                    successMessage += `<br><br><strong>Details:</strong><br>${result.message}`;
                }
                this.showMessage(successMessage, 'success');
                if (this.elements.syncStatus) {
                    this.elements.syncStatus.textContent = 'Sync completed successfully';
                }
            } else {
                const errorMessage = result.detail || result.message || 'Unknown error occurred';
                this.showMessage(`Sync failed: ${errorMessage}`, 'error');
                if (this.elements.syncStatus) {
                    this.elements.syncStatus.textContent = 'Sync failed';
                }
            }
            
        } catch (error) {
            console.error('Sync error:', error);
            this.showMessage(`Sync failed: ${error.message}`, 'error');
            if (this.elements.syncStatus) {
                this.elements.syncStatus.textContent = 'Sync failed';
            }
        } finally {
            button.disabled = false;
            button.innerHTML = originalText;
            
            // Reset status after a delay
            setTimeout(() => {
                if (this.elements.syncStatus) {
                    if (this.oauthConnected) {
                        this.elements.syncStatus.textContent = 'Ready to sync with LinkedIn';
                    } else {
                        this.elements.syncStatus.textContent = 'Connect LinkedIn account to enable sync';
                    }
                }
            }, 3000);
        }
    }
    
    showMessage(message, type = 'info') {
        this.hideAllResults();
        
        if (type === 'success' && this.elements.resultSuccess) {
            this.elements.successContent.innerHTML = message;
            this.elements.resultSuccess.style.display = 'block';
        } else if (type === 'error' && this.elements.resultError) {
            this.elements.errorContent.innerHTML = message;
            this.elements.resultError.style.display = 'block';
        } else if (this.elements.resultInfo) {
            this.elements.infoContent.innerHTML = message;
            this.elements.resultInfo.style.display = 'block';
        }
        
        // Auto-hide after 5 seconds
        setTimeout(() => this.hideAllResults(), 5000);
    }
    
    hideAllResults() {
        if (this.elements.resultSuccess) this.elements.resultSuccess.style.display = 'none';
        if (this.elements.resultError) this.elements.resultError.style.display = 'none';
        if (this.elements.resultInfo) this.elements.resultInfo.style.display = 'none';
    }
}

// Initialize the LinkedIn Admin interface
new LinkedInAdmin();
