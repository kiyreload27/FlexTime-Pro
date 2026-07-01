/* FlexTime Pro — Global Application JavaScript */

// Toast notification system
window.showToast = function(message, type = 'success', duration = 3000) {
    const toast = document.getElementById('toast');
    if (!toast || !toast.__x) return;

    toast.__x.$data.message = message;
    toast.__x.$data.type = type;
    toast.__x.$data.show = true;

    setTimeout(() => {
        if (toast.__x) toast.__x.$data.show = false;
    }, duration);
};

// Haptic feedback helper
window.hapticVibrate = function(pattern = 30) {
    if (navigator.vibrate) {
        navigator.vibrate(pattern);
    }
};

// Global click haptics for interactive elements
document.addEventListener('click', function(e) {
    const target = e.target.closest('button, a.btn-primary, a.btn-secondary, a.btn-danger, .nav-link, .card');
    if (target) {
        window.hapticVibrate(15); // Very light tap
    }
});

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + S = Save (prevent default, submit active form)
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        const activeForm = document.querySelector('form:focus-within');
        if (activeForm) activeForm.submit();
    }

    // Ctrl/Cmd + N = Go to new entry
    if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
        e.preventDefault();
        const quickInput = document.getElementById('quick-add-input');
        if (quickInput) quickInput.focus();
    }

    // Escape = Close modals
    if (e.key === 'Escape') {
        document.querySelectorAll('[x-data]').forEach(el => {
            if (el.__x && el.__x.$data.showModal !== undefined) {
                el.__x.$data.showModal = false;
            }
            if (el.__x && el.__x.$data.editing !== undefined) {
                el.__x.$data.editing = false;
            }
        });
    }
});

// CSRF token helper for fetch requests
window.getCSRFToken = function() {
    return document.cookie.split('; ')
        .find(row => row.startsWith('csrf_token='))
        ?.split('=')[1] || '';
};

// Auto-remove URL params after showing toast (clean URL)
if (window.history.replaceState) {
    const url = new URL(window.location);
    const params = ['saved', 'quick_saved', 'copied', 'duplicated', 'no_yesterday'];
    let changed = false;
    params.forEach(p => {
        if (url.searchParams.has(p)) {
            url.searchParams.delete(p);
            changed = true;
        }
    });
    if (changed) {
        setTimeout(() => window.history.replaceState({}, '', url), 100);
}
}

// Helper to calculate hours from start/end times
window.calcHours = function(startStr, endStr, breakMins) {
    if (!startStr || !endStr) return '';
    const start = startStr.split(':');
    const end = endStr.split(':');
    let startM = parseInt(start[0]) * 60 + parseInt(start[1]);
    let endM = parseInt(end[0]) * 60 + parseInt(end[1]);
    if (endM < startM) endM += 24 * 60; // handle overnight
    let total = endM - startM - (parseInt(breakMins) || 0);
    if (total <= 0) return '0';
    return (total / 60).toFixed(2).replace(/\.?0+$/, ''); // e.g. 8.5 or 8 instead of 8.50
};

// Form submission loading states
document.addEventListener('submit', function(e) {
    const form = e.target;
    // Don't apply to search forms or forms explicitly asking to be ignored
    if (form.method.toLowerCase() === 'get' || form.hasAttribute('data-no-loading')) return;

    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn && !submitBtn.disabled) {
        // Prevent double clicks
        submitBtn.disabled = true;
        
        window.hapticVibrate([30, 50, 30]); // More pronounced haptic on save
        
        // Add visual loading state
        const originalHtml = submitBtn.innerHTML;
        submitBtn.setAttribute('data-original-html', originalHtml);
        submitBtn.innerHTML = `
            <svg class="w-4 h-4 animate-spin inline mr-1" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Saving...
        `;
        submitBtn.classList.add('opacity-80', 'cursor-not-allowed');
    }
});

console.log('%c FlexTime Pro ', 'background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white; font-size: 14px; padding: 4px 12px; border-radius: 6px; font-weight: bold;');

// Alpine.js swipe directive
document.addEventListener('alpine:init', () => {
    Alpine.directive('swipe', (el, { expression, modifiers }, { evaluateLater, cleanup }) => {
        let touchstartX = 0;
        let touchendX = 0;
        const threshold = 50;
        const handleGesture = () => {
            if (touchendX < touchstartX - threshold && modifiers.includes('left')) evaluateLater(expression)();
            if (touchendX > touchstartX + threshold && modifiers.includes('right')) evaluateLater(expression)();
        };
        const touchStart = e => touchstartX = e.changedTouches[0].screenX;
        const touchEnd = e => {
            touchendX = e.changedTouches[0].screenX;
            handleGesture();
        };
        el.addEventListener('touchstart', touchStart, { passive: true });
        el.addEventListener('touchend', touchEnd, { passive: true });
        cleanup(() => {
            el.removeEventListener('touchstart', touchStart);
            el.removeEventListener('touchend', touchEnd);
        });
    });
});
