/**
 * Google OAuth Login with Popup Window
 * Centered popup positioning and OAuth flow management
 */

let authPopup = null;

/**
 * Detect if user is on a mobile device
 */
function isMobileDevice() {
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) ||
           (window.innerWidth <= 768) ||
           ('ontouchstart' in window);
}

/**
 * Calculate centered popup position
 */
function getPopupPosition(width = 500, height = 600) {
    const screenLeft = window.screenLeft !== undefined ? window.screenLeft : window.screenX;
    const screenTop = window.screenTop !== undefined ? window.screenTop : window.screenY;
    
    const windowWidth = window.innerWidth ? window.innerWidth : document.documentElement.clientWidth ? document.documentElement.clientWidth : screen.width;
    const windowHeight = window.innerHeight ? window.innerHeight : document.documentElement.clientHeight ? document.documentElement.clientHeight : screen.height;
    
    const left = ((windowWidth / 2) - (width / 2)) + screenLeft;
    // Position popup 50% higher than center by reducing top by 25% of window height
    const top = ((windowHeight / 2) - (height / 2)) - (windowHeight * 0.25) + screenTop;
    
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
// assets/js/auth-login.js

function initiateLogin() {
    fetch('/auth/login')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            if (data.auth_url) {
                // Check if user is on mobile device
                if (isMobileDevice()) {
                    // On mobile, redirect to OAuth URL in same window
                    window.location.href = data.auth_url;
                } else {
                    // On desktop, use popup
                    openOAuthPopup(data.auth_url);
                }
            } else {
                console.error('Auth URL not found in response:', data);
                alert('Could not initiate login. The authentication URL was not provided.');
            }
        })
        .catch(error => {
            console.error('Error initiating login:', error);
            
            // Show a fallback dialog with admin login option
            const useAdminLogin = confirm(
                'Google OAuth login failed. Would you like to use admin login instead?'
            );
            
            if (useAdminLogin) {
                if (isMobileDevice()) {
                    // On mobile, redirect to admin login page
                    window.location.href = '/auth/admin-login';
                } else {
                    // On desktop, use popup
                    openAdminLoginPopup();
                }
            } else {
                alert('An error occurred during login. Please check the console for more details.');
            }
        });
}

function openOAuthPopup(url) {
    const width = 500;
    const height = 600;
    const { top, left } = getPopupPosition(width, height);

    const popup = window.open(
        url,
        'oauthPopup',
        `width=${width},height=${height},top=${top},left=${left},resizable=yes,scrollbars=yes,status=yes`
    );

    // Listen for messages from the popup
    window.addEventListener('message', function(event) {
        // Ensure the message is from a trusted origin
        if (event.origin !== window.location.origin) {
            return;
        }
        // Check for the success message
        if (event.data.type === 'OAUTH_SUCCESS') {
            if (popup) {
                popup.close();
            }
            
            // Set the cookie with the token from the popup
            if (event.data.token) {
                const isSecure = window.location.protocol === 'https:';
                const securePart = isSecure ? '; Secure' : '';
                document.cookie = `access_token=${event.data.token}; path=/; max-age=${8*60*60}; SameSite=Lax${securePart}`;
            }
            
            // Show success notification
            showLoginSuccessNotification(event.data.user);
            
            // Redirect to /work page after a short delay to show the notification
            setTimeout(() => {
                window.location.href = '/work';
            }, 2000);
        }
    }, false);

    // Periodically check if the popup was closed by the user
    const checkPopup = setInterval(() => {
        if (popup && popup.closed) {
            clearInterval(checkPopup);
            // Optional: could check login status here in case the user
            // completed auth but the message failed. For now, we do nothing.
        }
    }, 1000);
}

/**
 * Open admin login popup as fallback when OAuth fails
 */
function openAdminLoginPopup() {
    const width = 400;
    const height = 500;
    const { top, left } = getPopupPosition(width, height);

    const popup = window.open(
        '/auth/admin-login',
        'adminLoginPopup',
        `width=${width},height=${height},top=${top},left=${left},resizable=yes,scrollbars=yes,status=yes`
    );

    // Listen for messages from the popup
    window.addEventListener('message', function(event) {
        // Ensure the message is from a trusted origin
        if (event.origin !== window.location.origin) {
            return;
        }
        // Check for the success message
        if (event.data.type === 'ADMIN_LOGIN_SUCCESS') {
            if (popup) {
                popup.close();
            }
            window.location.href = '/work'; // Redirect to work page to show admin links
        }
    }, false);

    // Periodically check if the popup was closed by the user
    const checkPopup = setInterval(() => {
        if (popup && popup.closed) {
            clearInterval(checkPopup);
            // Optional: could check login status here
        }
    }, 1000);
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

/**
 * Show a success notification when login is completed
 */
function showLoginSuccessNotification(user) {
    // Remove any existing notifications
    const existingNotification = document.getElementById('login-success-notification');
    if (existingNotification) {
        existingNotification.remove();
    }
    
    // Create notification element
    const notification = document.createElement('div');
    notification.id = 'login-success-notification';
    notification.innerHTML = `
        <div style="
            position: fixed;
            top: 20px;
            right: 20px;
            background: linear-gradient(135deg, #28a745, #20c997);
            color: white;
            padding: 1rem 1.5rem;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(40, 167, 69, 0.3);
            z-index: 10000;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 300px;
            animation: slideIn 0.3s ease-out;
        ">
            <div style="display: flex; align-items: center; margin-bottom: 0.5rem;">
                <div style="font-size: 1.2rem; margin-right: 0.5rem;">✓</div>
                <div style="font-weight: 600;">Login Successful!</div>
            </div>
            <div style="font-size: 0.9rem; opacity: 0.9;">
                Welcome back${user && user.email ? ', ' + user.email.split('@')[0] : ''}!
            </div>
            <div style="font-size: 0.8rem; opacity: 0.8; margin-top: 0.5rem;">
                Page will refresh automatically...
            </div>
        </div>
    `;
    
    // Add CSS animation
    if (!document.getElementById('notification-styles')) {
        const style = document.createElement('style');
        style.id = 'notification-styles';
        style.textContent = `
            @keyframes slideIn {
                from {
                    transform: translateX(100%);
                    opacity: 0;
                }
                to {
                    transform: translateX(0);
                    opacity: 1;
                }
            }
        `;
        document.head.appendChild(style);
    }
    
    // Add to page
    document.body.appendChild(notification);
    
    // Auto-remove after 3 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.style.animation = 'slideIn 0.3s ease-out reverse';
            setTimeout(() => {
                notification.remove();
            }, 300);
        }
    }, 3000);
}
