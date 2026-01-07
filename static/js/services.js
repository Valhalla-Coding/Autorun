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

        // Modal close buttons
        $$('.modal-close').forEach(btn => {
            btn.addEventListener('click', () => this.hideModal());
        });

        $$('.modal-close-delete').forEach(btn => {
            btn.addEventListener('click', () => this.hideDeleteModal());
        });

        // Click outside modal to close
        $('#service-modal')?.querySelector('.modal-overlay')?.addEventListener('click', () => {
            this.hideModal();
        });

        $('#delete-modal')?.querySelector('.modal-overlay')?.addEventListener('click', () => {
            this.hideDeleteModal();
        });

        // Service form submit
        $('#service-form')?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleFormSubmit();
        });

        // System controls
        $('#reload-config')?.addEventListener('click', () => this.reloadConfig());
        $('#daemon-reload')?.addEventListener('click', () => this.daemonReload());
        $('#apply-changes')?.addEventListener('click', () => this.reloadConfig());

        // Delete confirmation
        $('#confirm-delete')?.addEventListener('click', () => this.confirmDelete());

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

    showModal(mode, service = null) {
        const modal = $('#service-modal');
        const form = $('#service-form');
        const title = $('#modal-title');

        if (!modal || !form) return;

        // Reset form
        form.reset();

        if (mode === 'add') {
            title.textContent = 'Add Service';
            // Set defaults
            $('#service-entrypoint').value = 'run.py';
            $('#service-restart').value = 'always';
            $('#service-enabled').checked = true;
        } else if (mode === 'edit' && service) {
            title.textContent = 'Edit Service';
            const config = service.config;

            // Populate form
            $('#service-name').value = config.name;
            $('#service-name').disabled = true; // Can't change name
            $('#service-folder').value = config.folder;
            $('#service-entrypoint').value = config.entrypoint;
            $('#service-port').value = config.port || '';
            $('#service-web-interface').checked = config.web_interface;
            $('#service-restart').value = config.auto_restart;
            $('#service-description').value = config.description || '';
            $('#service-enabled').checked = config.enabled;

            this.selectedService = service.name;
        }

        modal.classList.remove('hidden');
    }

    hideModal() {
        const modal = $('#service-modal');
        if (modal) {
            modal.classList.add('hidden');
            $('#service-name').disabled = false; // Re-enable for next add
            this.selectedService = null;
        }
    }

    showDeleteModal(serviceName) {
        const modal = $('#delete-modal');
        if (!modal) return;

        $('#delete-service-name').textContent = serviceName;
        this.selectedService = serviceName;
        modal.classList.remove('hidden');
    }

    hideDeleteModal() {
        const modal = $('#delete-modal');
        if (modal) {
            modal.classList.add('hidden');
            this.selectedService = null;
        }
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
            depends_on: []
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
