// AutoRun v2 - Service Management

class ServiceManager {
    constructor() {
        this.services = [];
        this.selectedService = null;
        this.pollInterval = null;
        this.isLoading = false;
    }

    async init() {
        await this.loadServices();
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
    }

    async loadServices() {
        if (this.isLoading) return;
        this.isLoading = true;

        try {
            const response = await API.get('/api/services');

            if (response.status === 'success') {
                this.services = response.data.services;
                this.renderServices();
                this.updateSystemStats(response.data);
            }
        } catch (error) {
            notify.error(`Failed to load services: ${error.message}`);
        } finally {
            this.isLoading = false;
        }
    }

    renderServices() {
        const grid = $('#services-grid');
        if (!grid) return;

        if (this.services.length === 0) {
            grid.innerHTML = '<div class="loading-placeholder">No services configured. Click "+ Add Service" to get started.</div>';
            return;
        }

        grid.innerHTML = this.services.map(service => this.createServiceCard(service)).join('');

        // Attach event listeners to action buttons
        $$('.service-card').forEach(card => {
            const serviceName = card.dataset.service;

            card.querySelector('[data-action="start"]')?.addEventListener('click', () => {
                this.startService(serviceName);
            });

            card.querySelector('[data-action="stop"]')?.addEventListener('click', () => {
                this.stopService(serviceName);
            });

            card.querySelector('[data-action="restart"]')?.addEventListener('click', () => {
                this.restartService(serviceName);
            });

            card.querySelector('[data-action="edit"]')?.addEventListener('click', () => {
                this.showModal('edit', this.findService(serviceName));
            });

            card.querySelector('[data-action="delete"]')?.addEventListener('click', () => {
                this.showDeleteModal(serviceName);
            });
        });
    }

    createServiceCard(service) {
        const status = service.status || 'unknown';
        const config = service.config;

        return `
            <div class="service-card status-${status}" data-service="${service.name}">
                <div class="card-header">
                    <div class="card-title">
                        <span class="status-indicator status-${status}"></span>
                        <h3>${service.name}</h3>
                    </div>
                    <span class="badge badge-${status}">${status.toUpperCase()}</span>
                </div>
                <div class="card-body">
                    <p class="service-description">${config.description || 'No description'}</p>
                    <div class="service-info">
                        <span class="info-item">📁 ${config.folder}</span>
                        ${config.port ? `<span class="info-item">🌐 Port ${config.port}</span>` : ''}
                        ${service.pid ? `<span class="info-item">🔢 PID ${service.pid}</span>` : ''}
                        ${service.uptime && service.uptime !== 'N/A' ? `<span class="info-item">⏱️ ${service.uptime}</span>` : ''}
                        ${service.memory_mb > 0 ? `<span class="info-item">💾 ${formatMemory(service.memory_mb)}</span>` : ''}
                    </div>
                </div>
                <div class="card-actions">
                    <button class="btn-icon" data-action="start" ${status === 'running' ? 'disabled' : ''} title="Start">▶️</button>
                    <button class="btn-icon" data-action="stop" ${status !== 'running' ? 'disabled' : ''} title="Stop">⏹️</button>
                    <button class="btn-icon" data-action="restart" ${status !== 'running' ? 'disabled' : ''} title="Restart">🔄</button>
                    <button class="btn-icon" data-action="edit" title="Edit">✏️</button>
                    <button class="btn-icon btn-danger" data-action="delete" title="Delete">🗑️</button>
                </div>
            </div>
        `;
    }

    updateSystemStats(data) {
        $('#total-services').textContent = data.total || 0;
        $('#running-services').textContent = data.running || 0;
        $('#stopped-services').textContent = data.stopped || 0;
        $('#failed-services').textContent = data.failed || 0;

        // Update footer
        $('#footer-info').textContent = `${data.total} services | ${data.running} running`;
    }

    findService(name) {
        return this.services.find(s => s.name === name);
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
            await this.loadServices();
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
            await this.loadServices();
        } catch (error) {
            notify.error(`Failed to delete service: ${error.message}`);
        }
    }

    async startService(name) {
        try {
            await API.post(`/api/services/${name}/start`);
            notify.success(`Service '${name}' started`);
            await this.loadServices();
        } catch (error) {
            notify.error(`Failed to start service: ${error.message}`);
        }
    }

    async stopService(name) {
        try {
            await API.post(`/api/services/${name}/stop`);
            notify.success(`Service '${name}' stopped`);
            await this.loadServices();
        } catch (error) {
            notify.error(`Failed to stop service: ${error.message}`);
        }
    }

    async restartService(name) {
        try {
            await API.post(`/api/services/${name}/restart`);
            notify.success(`Service '${name}' restarted`);
            await this.loadServices();
        } catch (error) {
            notify.error(`Failed to restart service: ${error.message}`);
        }
    }

    async reloadConfig() {
        try {
            await API.post('/api/system/reload');
            notify.success('Configuration reloaded successfully');
            await this.loadServices();
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
        // Refresh service list every 5 seconds
        this.pollInterval = setInterval(() => {
            this.loadServices();
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
