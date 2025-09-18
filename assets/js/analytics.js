/**
 * Google Analytics configuration
 * Production-ready analytics tracking
 */

// Initialize Google Analytics
window.dataLayer = window.dataLayer || [];
function gtag() { 
    dataLayer.push(arguments); 
}

gtag('js', new Date());
gtag('config', 'UA-27877508-5');