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
        const container = $('#modal-container');
        if (!container) return;

        this.selectedPath = null;

        try {
            // Build URL with query params
            let url = `/components/modal/file-browser?type=${this.mode}`;
            if (startPath) {
                url += `&path=${encodeURIComponent(startPath)}`;
            }

            // Fetch modal HTML from server
            const response = await fetch(url);
            const html = await response.text();

            // Insert modal into container
            container.innerHTML = html;

            // Show modal
            const modal = $('#browser-modal');
            if (modal) {
                modal.classList.remove('hidden');
                this.currentPath = $('#browser-current-path')?.textContent;

                // Attach event listeners
                this.setupBrowserEventListeners();
                this.attachBrowserItemListeners();
            }
        } catch (error) {
            notify.error(`Failed to load browser: ${error.message}`);
        }
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
            // Clear modal container after animation
            setTimeout(() => {
                $('#modal-container').innerHTML = '';
            }, 300);
            this.selectedPath = null;
        }
    }

    async navigateToPath(path) {
        // Reload the browser modal with new path
        await this.showBrowser(null, path);
    }

    attachBrowserItemListeners() {
        // Attach click handlers to browser items
        $$('.browser-item').forEach(item => {
            item.addEventListener('click', async (e) => {
                const path = e.currentTarget.dataset.path;

                if (this.mode === 'folder') {
                    // For folders: navigate on single click, select on double click
                    if (e.currentTarget.classList.contains('parent')) {
                        // Navigate to parent
                        await this.navigateToPath(path);
                    } else {
                        // Select folder
                        this.selectItem(e.currentTarget, path);
                    }
                } else {
                    // For files: select on single click
                    this.selectItem(e.currentTarget, path);
                }
            });

            // Double-click handling
            item.addEventListener('dblclick', async (e) => {
                const path = e.currentTarget.dataset.path;

                if (this.mode === 'folder' && !e.currentTarget.classList.contains('parent')) {
                    // Navigate into folder
                    await this.navigateToPath(path);
                } else if (this.mode === 'file') {
                    // Select file and close
                    this.selectedPath = path;
                    if (this.targetInput) {
                        this.targetInput.value = path;
                        this.hideBrowser();
                    }
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

    // Use event delegation for browse buttons (they're dynamically loaded with modals)
    document.addEventListener('click', (e) => {
        if (e.target.id === 'browse-folder' || e.target.closest('#browse-folder')) {
            window.fileBrowser.openFolderBrowser('service-folder');
        } else if (e.target.id === 'browse-file' || e.target.closest('#browse-file')) {
            window.fileBrowser.openFileBrowser('service-entrypoint');
        }
    });
});
