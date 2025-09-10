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
                openOAuthPopup(data.auth_url);
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
                openAdminLoginPopup();
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
            window.location.reload(); // Reload the page to reflect login state
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
            window.location.reload(); // Reload the page to reflect login state
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
