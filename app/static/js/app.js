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

console.log('%c FlexTime Pro ', 'background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white; font-size: 14px; padding: 4px 12px; border-radius: 6px; font-weight: bold;');
