// AutoRun v2 - Service Management

class ServiceManager {
    constructor() {
        this.services = [];
        this.selectedService = null;
        this.pollInterval = null;
        this.isLoading = false;
    }

    async init() {
        await this.loadSystemStats();
        this.setupEventListeners();
        this.startPolling();
    }

    setupEventListeners() {
        // Add service button
        $('#add-service')?.addEventListener('click', () => {
            this.showModal('add');
        });

        // System controls
        $('#reload-config')?.addEventListener('click', () => this.reloadConfig());
        $('#daemon-reload')?.addEventListener('click', () => this.daemonReload());
        $('#apply-changes')?.addEventListener('click', () => this.reloadConfig());

        // Event delegation for service card buttons (since cards are loaded via HTMX)
        document.addEventListener('click', (e) => {
            const button = e.target.closest('[data-action]');
            if (!button) return;

            const card = button.closest('.service-card');
            if (!card) return;

            const serviceName = card.dataset.service;
            const action = button.dataset.action;

            switch (action) {
                case 'start':
                    this.startService(serviceName);
                    break;
                case 'stop':
                    this.stopService(serviceName);
                    break;
                case 'restart':
                    this.restartService(serviceName);
                    break;
                case 'pull':
                    this.pullService(serviceName);
                    break;
                case 'edit':
                    this.editService(serviceName);
                    break;
                case 'delete':
                    this.showDeleteModal(serviceName);
                    break;
            }
        });
    }

    // Trigger HTMX to reload service cards
    triggerServiceUpdate() {
        document.body.dispatchEvent(new CustomEvent('serviceUpdate'));
    }

    // Load system stats only (services are loaded via HTMX)
    async loadSystemStats() {
        if (this.isLoading) return;
        this.isLoading = true;

        try {
            const response = await API.get('/api/services');

            if (response.status === 'success') {
                this.services = response.data.services;
                this.updateSystemStats(response.data);
            }
        } catch (error) {
            notify.error(`Failed to load services: ${error.message}`);
        } finally {
            this.isLoading = false;
        }
    }

    // Find service for editing (loads fresh data from API)
    async editService(serviceName) {
        try {
            const response = await API.get(`/api/services/${serviceName}`);

            if (response.status === 'success') {
                const service = response.data;
                this.showModal('edit', service);
            }
        } catch (error) {
            notify.error(`Failed to load service: ${error.message}`);
        }
    }

    updateSystemStats(data) {
        $('#total-services').textContent = data.total || 0;
        $('#running-services').textContent = data.running || 0;
        $('#stopped-services').textContent = data.stopped || 0;
        $('#failed-services').textContent = data.failed || 0;

        // Update footer
        $('#footer-info').textContent = `${data.total} services | ${data.running} running`;
    }

    async showModal(mode, service = null) {
        const container = $('#modal-container');
        if (!container) return;

        // Build URL with query params
        let url = `/components/modal/service-form?mode=${mode}`;
        if (mode === 'edit' && service) {
            url += `&service_name=${service.name}`;
            this.selectedService = service.name;
        }

        try {
            // Fetch modal HTML from server
            const response = await fetch(url);
            const html = await response.text();

            // Insert modal into container
            container.innerHTML = html;

            // Show modal (remove hidden class if present)
            const modal = $('#service-modal');
            if (modal) {
                modal.classList.remove('hidden');

                // Attach event listeners
                this.attachModalListeners();
            }
        } catch (error) {
            notify.error(`Failed to load modal: ${error.message}`);
        }
    }

    hideModal() {
        const modal = $('#service-modal');
        if (modal) {
            modal.classList.add('hidden');
            // Clear modal container after animation
            setTimeout(() => {
                $('#modal-container').innerHTML = '';
            }, 300);
            this.selectedService = null;
        }
    }

    attachModalListeners() {
        // Modal close buttons
        $$('.modal-close').forEach(btn => {
            btn.addEventListener('click', () => this.hideModal());
        });

        // Click outside modal to close
        $('#service-modal')?.querySelector('.modal-overlay')?.addEventListener('click', () => {
            this.hideModal();
        });

        // Service form submit
        $('#service-form')?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleFormSubmit();
        });

        // Source toggle buttons (add mode only)
        $$('.source-btn').forEach(btn => {
            btn.addEventListener('click', () => this.setSourceMode(btn.dataset.source));
        });

        // GitHub URL auto-fill (debounced)
        $('#service-github-url')?.addEventListener('input', (e) => {
            clearTimeout(this._githubFetchTimeout);
            this._githubFetchTimeout = setTimeout(() => {
                this.fetchGithubInfo(e.target.value.trim());
            }, 600);
        });
    }

    setSourceMode(mode) {
        $$('.source-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.source === mode);
        });

        const githubSection = $('#github-url-section');
        if (githubSection) {
            githubSection.style.display = mode === 'github' ? '' : 'none';
        }

        if (mode === 'folder') {
            const githubInput = $('#service-github-url');
            if (githubInput) githubInput.value = '';
            const statusEl = $('#github-status');
            if (statusEl) statusEl.textContent = 'Paste a GitHub repository URL to auto-fill details';
        }
    }

    async fetchGithubInfo(url) {
        if (!url) return;

        const match = url.match(/github\.com\/([^/]+)\/([^/\s]+)/);
        if (!match) return;

        const [, owner, repo] = match;
        const repoSlug = repo.replace(/\.git$/, '');
        const statusEl = $('#github-status');

        if (statusEl) statusEl.textContent = 'Fetching repo info...';

        try {
            const res = await fetch(`https://api.github.com/repos/${owner}/${repoSlug}`);
            if (!res.ok) throw new Error('Repo not found');

            const data = await res.json();

            const nameInput = $('#service-name');
            if (nameInput && !nameInput.value) {
                nameInput.value = data.name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
            }

            const descInput = $('#service-description');
            if (descInput && !descInput.value && data.description) {
                descInput.value = data.description;
            }

            if (statusEl) statusEl.textContent = `✓ Found: ${data.full_name}`;
        } catch {
            if (statusEl) statusEl.textContent = 'Could not fetch repo info — check the URL';
        }
    }

    async showDeleteModal(serviceName) {
        const container = $('#modal-container');
        if (!container) return;

        this.selectedService = serviceName;

        try {
            // Fetch delete modal HTML from server
            const response = await fetch(`/components/modal/delete-confirm/${serviceName}`);
            const html = await response.text();

            // Insert modal into container
            container.innerHTML = html;

            // Show modal
            const modal = $('#delete-modal');
            if (modal) {
                modal.classList.remove('hidden');

                // Attach event listeners
                this.attachDeleteModalListeners();
            }
        } catch (error) {
            notify.error(`Failed to load delete modal: ${error.message}`);
        }
    }

    hideDeleteModal() {
        const modal = $('#delete-modal');
        if (modal) {
            modal.classList.add('hidden');
            // Clear modal container after animation
            setTimeout(() => {
                $('#modal-container').innerHTML = '';
            }, 300);
            this.selectedService = null;
        }
    }

    attachDeleteModalListeners() {
        // Modal close buttons
        $$('.modal-close-delete').forEach(btn => {
            btn.addEventListener('click', () => this.hideDeleteModal());
        });

        // Click outside modal to close
        $('#delete-modal')?.querySelector('.modal-overlay')?.addEventListener('click', () => {
            this.hideDeleteModal();
        });

        // Delete confirmation
        $('#confirm-delete')?.addEventListener('click', () => this.confirmDelete());
    }

    async handleFormSubmit() {
        const formData = new FormData($('#service-form'));
        const data = {
            name: formData.get('name'),
            folder: formData.get('folder'),
            entrypoint: formData.get('entrypoint'),
            port: formData.get('port') ? parseInt(formData.get('port')) : null,
            web_interface: formData.get('web_interface') === 'on',
            auto_restart: formData.get('auto_restart'),
            description: formData.get('description') || '',
            enabled: formData.get('enabled') === 'on',
            environment: {},
            depends_on: [],
            github_url: formData.get('github_url') || null,
            auto_update: formData.get('auto_update') === 'on'
        };

        try {
            let response;
            if (this.selectedService) {
                // Update existing service
                response = await API.put(`/api/services/${this.selectedService}`, data);
                notify.success(`Service '${this.selectedService}' updated successfully`);
            } else {
                // Create new service
                response = await API.post('/api/services', data);
                notify.success(`Service '${data.name}' created successfully`);
            }

            this.hideModal();
            await this.loadSystemStats();
            this.triggerServiceUpdate();
        } catch (error) {
            notify.error(`Failed to save service: ${error.message}`);
        }
    }

    async confirmDelete() {
        if (!this.selectedService) return;

        try {
            await API.delete(`/api/services/${this.selectedService}`);
            notify.success(`Service '${this.selectedService}' deleted successfully`);
            this.hideDeleteModal();
            await this.loadSystemStats();
            this.triggerServiceUpdate();
        } catch (error) {
            notify.error(`Failed to delete service: ${error.message}`);
        }
    }

    async startService(name) {
        try {
            await API.post(`/api/services/${name}/start`);
            notify.success(`Service '${name}' started`);
            await this.loadSystemStats();
            this.triggerServiceUpdate();
        } catch (error) {
            notify.error(`Failed to start service: ${error.message}`);
        }
    }

    async stopService(name) {
        try {
            await API.post(`/api/services/${name}/stop`);
            notify.success(`Service '${name}' stopped`);
            await this.loadSystemStats();
            this.triggerServiceUpdate();
        } catch (error) {
            notify.error(`Failed to stop service: ${error.message}`);
        }
    }

    async pullService(name) {
        try {
            notify.info?.(`Pulling latest for '${name}'...`);
            await API.post(`/api/services/${name}/pull`);
            notify.success(`Service '${name}' pulled and restarted`);
            await this.loadSystemStats();
            this.triggerServiceUpdate();
        } catch (error) {
            notify.error(`Pull failed for '${name}': ${error.message}`);
        }
    }

    async restartService(name) {
        try {
            await API.post(`/api/services/${name}/restart`);
            notify.success(`Service '${name}' restarted`);
            await this.loadSystemStats();
            this.triggerServiceUpdate();
        } catch (error) {
            notify.error(`Failed to restart service: ${error.message}`);
        }
    }

    async reloadConfig() {
        try {
            await API.post('/api/system/reload');
            notify.success('Configuration reloaded successfully');
            await this.loadSystemStats();
            this.triggerServiceUpdate();
        } catch (error) {
            notify.error(`Failed to reload configuration: ${error.message}`);
        }
    }

    async daemonReload() {
        try {
            await API.post('/api/system/daemon-reload');
            notify.success('systemctl daemon-reload executed');
        } catch (error) {
            notify.error(`Failed to reload daemon: ${error.message}`);
        }
    }

    startPolling() {
        // Refresh service status every 5 seconds
        this.pollInterval = setInterval(() => {
            this.loadSystemStats();
            this.triggerServiceUpdate();
        }, 5000);
    }

    stopPolling() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
    }
}

// Initialize service manager when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.serviceManager = new ServiceManager();
    window.serviceManager.init();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.serviceManager) {
        window.serviceManager.stopPolling();
    }
});
