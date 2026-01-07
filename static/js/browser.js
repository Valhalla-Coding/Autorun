// AutoRun v2 - File/Folder Browser

class FileBrowser {
    constructor() {
        this.mode = null; // 'folder' or 'file'
        this.currentPath = null;
        this.selectedPath = null;
        this.targetInput = null;
    }

    async openFolderBrowser(targetInputId) {
        this.mode = 'folder';
        this.targetInput = $(`#${targetInputId}`);

        // Start from the current input value or home directory
        const startPath = this.targetInput?.value || null;

        await this.showBrowser('Browse Folders', startPath);
    }

    async openFileBrowser(targetInputId) {
        this.mode = 'file';
        this.targetInput = $(`#${targetInputId}`);

        // Get folder from the folder input
        const folderInput = $('#service-folder');
        const startPath = folderInput?.value || null;

        if (!startPath) {
            notify.warning('Please select a folder first');
            return;
        }

        await this.showBrowser('Browse Files', startPath);
    }

    async showBrowser(title, startPath) {
        const modal = $('#browser-modal');
        if (!modal) return;

        $('#browser-title').textContent = title;
        this.selectedPath = null;

        modal.classList.remove('hidden');

        if (this.mode === 'folder') {
            await this.loadFolders(startPath);
        } else {
            await this.loadFiles(startPath);
        }

        this.setupBrowserEventListeners();
    }

    setupBrowserEventListeners() {
        // Close buttons
        $$('.modal-close-browser').forEach(btn => {
            btn.addEventListener('click', () => this.hideBrowser());
        });

        // Select button
        $('#browser-select')?.addEventListener('click', () => {
            if (this.selectedPath && this.targetInput) {
                this.targetInput.value = this.selectedPath;
                this.hideBrowser();
            } else {
                notify.warning('Please select an item');
            }
        });

        // Click outside modal to close
        $('#browser-modal')?.querySelector('.modal-overlay')?.addEventListener('click', () => {
            this.hideBrowser();
        });
    }

    hideBrowser() {
        const modal = $('#browser-modal');
        if (modal) {
            modal.classList.add('hidden');
            this.selectedPath = null;
        }
    }

    async loadFolders(path) {
        const listEl = $('#browser-list');
        if (!listEl) return;

        listEl.innerHTML = '<div class="loading-placeholder">Loading...</div>';

        try {
            const url = path ? `/api/browse/folders?path=${encodeURIComponent(path)}` : '/api/browse/folders';
            const response = await API.get(url);

            if (response.status === 'success') {
                this.currentPath = response.data.current_path;
                $('#browser-current-path').textContent = this.currentPath;

                this.renderFolders(response.data);
            }
        } catch (error) {
            listEl.innerHTML = `<div class="loading-placeholder">Error: ${error.message}</div>`;
        }
    }

    renderFolders(data) {
        const listEl = $('#browser-list');
        if (!listEl) return;

        let html = '';

        // Add parent directory option
        if (data.parent) {
            html += `
                <div class="browser-item parent" data-path="${data.parent}" data-type="parent">
                    <span>📁 ..</span>
                </div>
            `;
        }

        // Add folders
        if (data.folders.length === 0) {
            html += '<div class="loading-placeholder">No folders found</div>';
        } else {
            data.folders.forEach(folder => {
                html += `
                    <div class="browser-item" data-path="${folder.path}" data-type="folder">
                        <span>📁 ${folder.name}</span>
                    </div>
                `;
            });
        }

        listEl.innerHTML = html;

        // Attach click handlers
        $$('.browser-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const path = e.currentTarget.dataset.path;
                const type = e.currentTarget.dataset.type;

                if (type === 'parent' || type === 'folder') {
                    // Navigate into folder
                    this.loadFolders(path);
                } else {
                    // Select folder
                    this.selectItem(e.currentTarget, path);
                }
            });

            // Double-click to select folder and close
            item.addEventListener('dblclick', (e) => {
                const path = e.currentTarget.dataset.path;
                this.selectedPath = path;
                if (this.targetInput) {
                    this.targetInput.value = path;
                    this.hideBrowser();
                }
            });
        });
    }

    async loadFiles(folderPath) {
        const listEl = $('#browser-list');
        if (!listEl) return;

        listEl.innerHTML = '<div class="loading-placeholder">Loading...</div>';

        try {
            const response = await API.get(`/api/browse/files?path=${encodeURIComponent(folderPath)}`);

            if (response.status === 'success') {
                this.currentPath = response.data.folder;
                $('#browser-current-path').textContent = this.currentPath;

                this.renderFiles(response.data);
            }
        } catch (error) {
            listEl.innerHTML = `<div class="loading-placeholder">Error: ${error.message}</div>`;
        }
    }

    renderFiles(data) {
        const listEl = $('#browser-list');
        if (!listEl) return;

        let html = '';

        if (data.files.length === 0) {
            html = '<div class="loading-placeholder">No Python files found in this folder</div>';
        } else {
            data.files.forEach(file => {
                html += `
                    <div class="browser-item" data-path="${file.name}" data-type="file">
                        <span>📄 ${file.name}</span>
                    </div>
                `;
            });
        }

        listEl.innerHTML = html;

        // Attach click handlers
        $$('.browser-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const filename = e.currentTarget.dataset.path;
                this.selectItem(e.currentTarget, filename);
            });

            // Double-click to select and close
            item.addEventListener('dblclick', (e) => {
                const filename = e.currentTarget.dataset.path;
                this.selectedPath = filename;
                if (this.targetInput) {
                    this.targetInput.value = filename;
                    this.hideBrowser();
                }
            });
        });
    }

    selectItem(element, path) {
        // Remove previous selection
        $$('.browser-item.selected').forEach(el => el.classList.remove('selected'));

        // Add selection to clicked item
        element.classList.add('selected');
        this.selectedPath = path;
    }
}

// Initialize browser when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.fileBrowser = new FileBrowser();

    // Wire up browse buttons
    $('#browse-folder')?.addEventListener('click', () => {
        window.fileBrowser.openFolderBrowser('service-folder');
    });

    $('#browse-file')?.addEventListener('click', () => {
        window.fileBrowser.openFileBrowser('service-entrypoint');
    });
});
