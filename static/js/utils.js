// AutoRun v2 - Utility Functions and API Wrapper

// ============================================================================
// API Wrapper
// ============================================================================
const API = {
    async request(url, options = {}) {
        try {
            const response = await fetch(url, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error?.message || `HTTP ${response.status}`);
            }

            return data;
        } catch (error) {
            console.error(`API Error (${url}):`, error);
            throw error;
        }
    },

    async get(url) {
        return this.request(url, { method: 'GET' });
    },

    async post(url, data = {}) {
        return this.request(url, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    async put(url, data = {}) {
        return this.request(url, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },

    async delete(url) {
        return this.request(url, { method: 'DELETE' });
    }
};

// ============================================================================
// Toast Notification System
// ============================================================================
const notify = {
    container: null,

    init() {
        this.container = document.getElementById('toast-container');
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.id = 'toast-container';
            document.body.appendChild(this.container);
        }
    },

    show(message, type = 'info', duration = 4000) {
        if (!this.container) this.init();

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;

        this.container.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => toast.remove(), 300);
        }, duration);
    },

    success(message) {
        this.show(message, 'success');
    },

    error(message) {
        this.show(message, 'error', 6000); // Errors stay longer
    },

    info(message) {
        this.show(message, 'info');
    }
};

// ============================================================================
// DOM Helpers
// ============================================================================
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => document.querySelectorAll(selector);

// ============================================================================
// Utility Functions
// ============================================================================
function formatUptime(uptime) {
    if (!uptime || uptime === 'N/A') return 'N/A';
    return uptime;
}

function formatMemory(memoryMb) {
    if (!memoryMb || memoryMb === 0) return 'N/A';
    return `${memoryMb.toFixed(1)} MB`;
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Add slideOut animation to CSS if not present
const style = document.createElement('style');
style.textContent = `
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// Initialize notifications on load
notify.init();
