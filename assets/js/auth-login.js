/**
 * Google OAuth Login with Popup Window
 * Centered popup positioning and OAuth flow management
 */

let authPopup = null;

/**
 * Calculate centered popup position
 */
function getPopupPosition(width = 500, height = 600) {
    const screenLeft = window.screenLeft !== undefined ? window.screenLeft : window.screenX;
    const screenTop = window.screenTop !== undefined ? window.screenTop : window.screenY;
    
    const windowWidth = window.innerWidth ? window.innerWidth : document.documentElement.clientWidth ? document.documentElement.clientWidth : screen.width;
    const windowHeight = window.innerHeight ? window.innerHeight : document.documentElement.clientHeight ? document.documentElement.clientHeight : screen.height;
    
    const left = ((windowWidth / 2) - (width / 2)) + screenLeft;
    const top = ((windowHeight / 2) - (height / 2)) + screenTop;
    
    return {
        left: Math.max(0, Math.floor(left)),
        top: Math.max(0, Math.floor(top)),
        width: width,
        height: height
    };
}

/**
 * Initiate Google OAuth login via popup
 */
async function initiateLogin() {
    try {
        console.log('Initiating Google OAuth login...');
        
        // Close any existing popup
        if (authPopup && !authPopup.closed) {
            authPopup.close();
        }
        
        // Get auth URL from server
        const response = await fetch('/auth/login', {
            method: 'GET',
            credentials: 'same-origin'
        });
        
        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.status === 'error') {
            console.error('OAuth initiation failed:', data.error);
            alert(`Login failed: ${data.error}`);
            if (data.redirect) {
                window.location.href = data.redirect;
            }
            return;
        }
        
        if (data.status === 'success' && data.auth_url) {
            console.log('Opening OAuth popup...');
            
            // Calculate centered position
            const popupPos = getPopupPosition(600, 700);
            
            // Open popup window at center
            const popupFeatures = [
                `width=${popupPos.width}`,
                `height=${popupPos.height}`,
                `left=${popupPos.left}`,
                `top=${popupPos.top}`,
                'scrollbars=yes',
                'resizable=yes',
                'status=no',
                'location=no',
                'toolbar=no',
                'menubar=no'
            ].join(',');
            
            authPopup = window.open(data.auth_url, 'googleOAuth', popupFeatures);
            
            if (!authPopup) {
                alert('Popup was blocked. Please allow popups for this site and try again.');
                return;
            }
            
            // Focus the popup
            if (authPopup.focus) {
                authPopup.focus();
            }
            
            // Monitor popup for completion
            monitorPopup();
            
        } else {
            console.error('Invalid response from login endpoint:', data);
            alert('Login failed: Invalid server response');
        }
        
    } catch (error) {
        console.error('Login initiation error:', error);
        alert(`Login failed: ${error.message}`);
    }
}

/**
 * Monitor popup window for completion
 */
function monitorPopup() {
    const checkClosed = setInterval(() => {
        if (authPopup && authPopup.closed) {
            clearInterval(checkClosed);
            console.log('OAuth popup closed');
            
            // Check if user is now authenticated by reloading the page
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        }
    }, 1000);
    
    // Also listen for postMessage from popup
    window.addEventListener('message', function(event) {
        if (event.origin !== window.location.origin) {
            return;
        }
        
        if (event.data && event.data.type === 'OAUTH_SUCCESS') {
            console.log('OAuth success message received');
            clearInterval(checkClosed);
            if (authPopup && !authPopup.closed) {
                authPopup.close();
            }
            
            // Redirect or reload based on success
            setTimeout(() => {
                window.location.href = '/workadmin';
            }, 500);
            
        } else if (event.data && event.data.type === 'OAUTH_CANCELLED') {
            console.log('OAuth cancelled by user');
            clearInterval(checkClosed);
            if (authPopup && !authPopup.closed) {
                authPopup.close();
            }
        }
    });
}

/**
 * Initialize login functionality when DOM is ready
 */
document.addEventListener('DOMContentLoaded', function() {
    // Find login buttons and attach event handlers
    const loginButtons = document.querySelectorAll('a[href="/auth/login"], button[data-action="login"]');
    
    loginButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            initiateLogin();
        });
    });
    
    console.log('Login popup functionality initialized');
});
