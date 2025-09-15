/**
 * Mouse Activity Analytics Tracker
 * Detects mouse movement to filter out bot traffic from analytics
 */

(function() {
    'use strict';
    
    let mouseActivityDetected = false;
    let pageLoadTime = Date.now();
    let currentPath = window.location.pathname;
    
    // Debounce function to prevent excessive API calls
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = function() {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    // Send mouse activity confirmation to server
    function sendMouseActivity() {
        if (mouseActivityDetected) {
            return; // Already sent
        }
        
        mouseActivityDetected = true;
        
        // Send analytics update via fetch API
        fetch('/analytics/mouse-activity', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                page_path: currentPath,
                timestamp: new Date().toISOString(),
                session_duration: Date.now() - pageLoadTime
            })
        }).catch(function(error) {
            // Silently handle errors - don't break the page
            console.debug('Mouse activity tracking failed:', error);
        });
    }
    
    // Debounced version to prevent rapid-fire calls
    const debouncedSendMouseActivity = debounce(sendMouseActivity, 1000);
    
    // Mouse movement detection
    function onMouseMove() {
        if (!mouseActivityDetected) {
            debouncedSendMouseActivity();
        }
    }
    
    // Touch detection for mobile devices
    function onTouchStart() {
        if (!mouseActivityDetected) {
            debouncedSendMouseActivity();
        }
    }
    
    // Click detection as additional human activity indicator
    function onClick() {
        if (!mouseActivityDetected) {
            sendMouseActivity(); // Immediate for clicks
        }
    }
    
    // Keyboard activity detection
    function onKeyDown() {
        if (!mouseActivityDetected) {
            sendMouseActivity(); // Immediate for keyboard
        }
    }
    
    // Initialize tracking when DOM is ready
    function initMouseTracking() {
        // Add event listeners
        document.addEventListener('mousemove', onMouseMove, { passive: true });
        document.addEventListener('touchstart', onTouchStart, { passive: true });
        document.addEventListener('click', onClick, { passive: true });
        document.addEventListener('keydown', onKeyDown, { passive: true });
        
        // Also track scroll as human activity
        document.addEventListener('scroll', onMouseMove, { passive: true });
        
        // Clean up on page unload
        window.addEventListener('beforeunload', function() {
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('touchstart', onTouchStart);
            document.removeEventListener('click', onClick);
            document.removeEventListener('keydown', onKeyDown);
            document.removeEventListener('scroll', onMouseMove);
        });
    }
    
    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initMouseTracking);
    } else {
        initMouseTracking();
    }
    
})();