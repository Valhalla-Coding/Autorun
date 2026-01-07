// AutoRun v2 - Tab Management

class TabManager {
    constructor() {
        this.tabs = new Map();
        this.activeTab = 'management';
        this.init();
    }

    init() {
        // Setup tab click handlers
        const tabElements = document.querySelectorAll('.tab');
        tabElements.forEach(tab => {
            const tabId = tab.dataset.tab;
            this.tabs.set(tabId, {
                element: tab,
                panel: document.getElementById(`tab-${tabId}`)
            });

            tab.addEventListener('click', () => this.switchTab(tabId));
        });
    }

    switchTab(tabId) {
        if (this.activeTab === tabId) return;

        // Deactivate current tab
        const currentTab = this.tabs.get(this.activeTab);
        if (currentTab) {
            currentTab.element.classList.remove('active');
            currentTab.panel.classList.remove('active');
        }

        // Activate new tab
        const newTab = this.tabs.get(tabId);
        if (newTab) {
            newTab.element.classList.add('active');
            newTab.panel.classList.add('active');
            this.activeTab = tabId;
        }
    }

    // Phase 2: Dynamic tab management for service iframes
    addDynamicTab(id, title, content) {
        // TODO: Implement in Phase 2
        console.log('Dynamic tabs will be implemented in Phase 2');
    }

    removeDynamicTab(id) {
        // TODO: Implement in Phase 2
        console.log('Dynamic tabs will be implemented in Phase 2');
    }
}

// Initialize tab manager when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.tabManager = new TabManager();
});
