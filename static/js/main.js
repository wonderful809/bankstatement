/**
 * BankStatementAI - Main JavaScript
 */

// Auto-dismiss flash messages after 5 seconds
document.addEventListener('DOMContentLoaded', function() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => alert.remove(), 300);
        }, 5000);
    });
});

// Add slideOut animation
if (!document.querySelector('style[data-animations]')) {
    const style = document.createElement('style');
    style.setAttribute('data-animations', 'true');
    style.textContent = `
        @keyframes slideOut {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(100%);
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(style);
}

// Smooth scrolling for anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Add loading state to forms
document.querySelectorAll('form').forEach(form => {
    form.addEventListener('submit', function(e) {
        const submitButton = this.querySelector('button[type="submit"]');
        if (submitButton && !submitButton.disabled) {
            const originalText = submitButton.textContent;
            submitButton.disabled = true;
            submitButton.textContent = 'Processing...';
            
            // Re-enable after 10 seconds as fallback
            setTimeout(() => {
                submitButton.disabled = false;
                submitButton.textContent = originalText;
            }, 10000);
        }
    });
});

// Add active state to navigation
document.addEventListener('DOMContentLoaded', function() {
    const currentPath = window.location.pathname;
    document.querySelectorAll('.nav-links a').forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.style.color = 'var(--primary)';
        }
    });
});

// Utility function to show notifications
function showNotification(message, type = 'info') {
    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.innerHTML = `
        <span>${message}</span>
        <button onclick="this.parentElement.remove()" class="alert-close">&times;</button>
    `;
    
    let container = document.querySelector('.flash-messages');
    if (!container) {
        container = document.createElement('div');
        container.className = 'flash-messages';
        document.body.appendChild(container);
    }
    
    container.appendChild(alert);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        alert.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => alert.remove(), 300);
    }, 5000);
}

// Expose utility functions globally
window.showNotification = showNotification;

// Add click outside to close dropdowns (if any)
document.addEventListener('click', function(event) {
    const dropdowns = document.querySelectorAll('.dropdown');
    dropdowns.forEach(dropdown => {
        if (!dropdown.contains(event.target)) {
            dropdown.classList.remove('open');
        }
    });
});

// Add keyboard navigation
document.addEventListener('keydown', function(e) {
    // ESC to close modals/dropdowns
    if (e.key === 'Escape') {
        document.querySelectorAll('.modal, .dropdown').forEach(el => {
            el.classList.remove('open');
        });
    }
});

// Lazy load images if any
if ('IntersectionObserver' in window) {
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src;
                img.classList.remove('lazy');
                imageObserver.unobserve(img);
            }
        });
    });

    document.querySelectorAll('img.lazy').forEach(img => {
        imageObserver.observe(img);
    });
}

// Add print functionality
function printReceipt(conversionId) {
    window.print();
}

// Copy to clipboard utility
function copyToClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(() => {
            showNotification('Copied to clipboard!', 'success');
        }).catch(() => {
            fallbackCopyToClipboard(text);
        });
    } else {
        fallbackCopyToClipboard(text);
    }
}

function fallbackCopyToClipboard(text) {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);
    textarea.select();
    try {
        document.execCommand('copy');
        showNotification('Copied to clipboard!', 'success');
    } catch (err) {
        showNotification('Failed to copy', 'error');
    }
    document.body.removeChild(textarea);
}

// Export functions
window.copyToClipboard = copyToClipboard;
window.printReceipt = printReceipt;

// Analytics tracking (placeholder for future integration)
function trackEvent(category, action, label) {
    // Integrate with Google Analytics, Mixpanel, etc.
    console.log('Event:', category, action, label);
}

window.trackEvent = trackEvent;

// Performance monitoring
if ('PerformanceObserver' in window) {
    const perfObserver = new PerformanceObserver((items) => {
        items.getEntries().forEach((entry) => {
            // Log performance metrics
            if (entry.duration > 1000) {
                console.warn('Slow operation detected:', entry.name, entry.duration);
            }
        });
    });
    
    try {
        perfObserver.observe({ entryTypes: ['measure', 'navigation'] });
    } catch (e) {
        // Silently fail if not supported
    }
}

// Service worker registration for PWA (optional future enhancement)
if ('serviceWorker' in navigator && window.location.protocol === 'https:') {
    window.addEventListener('load', () => {
        // Uncomment when service worker is ready
        // navigator.serviceWorker.register('/sw.js')
        //     .then(reg => console.log('Service Worker registered'))
        //     .catch(err => console.log('Service Worker registration failed:', err));
    });
}

// Add beforeunload warning for forms with unsaved changes
let formHasChanges = false;

document.querySelectorAll('form input, form textarea, form select').forEach(input => {
    input.addEventListener('change', () => {
        formHasChanges = true;
    });
});

document.querySelectorAll('form').forEach(form => {
    form.addEventListener('submit', () => {
        formHasChanges = false;
    });
});

window.addEventListener('beforeunload', (e) => {
    if (formHasChanges) {
        e.preventDefault();
        e.returnValue = '';
        return '';
    }
});
