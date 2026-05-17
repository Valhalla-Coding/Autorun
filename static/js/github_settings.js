// AutoRun v2 - GitHub Settings Panel

document.addEventListener('DOMContentLoaded', () => {
    const toggle   = $('#github-settings-toggle');
    const body     = $('#github-settings-body');
    const input    = $('#github-token-input');
    const saveBtn  = $('#github-token-save');
    const clearBtn = $('#github-token-clear');
    const status   = $('#github-token-status');

    if (!toggle) return;

    // Collapsible header
    toggle.addEventListener('click', () => {
        const collapsed = body.style.display === 'none';
        body.style.display = collapsed ? '' : 'none';
        toggle.querySelector('.collapse-icon').textContent = collapsed ? '▾' : '▸';
    });

    // Load current token state
    async function loadTokenStatus() {
        try {
            const res = await API.get('/api/settings/github-token');
            if (res.status === 'success') {
                status.textContent = res.data.configured
                    ? '✓ Token is configured'
                    : 'No token set — only public repos will work';
                status.className = res.data.configured ? 'token-ok' : 'token-missing';
            }
        } catch {
            status.textContent = 'Could not load token status';
        }
    }

    saveBtn?.addEventListener('click', async () => {
        const token = input.value.trim();
        if (!token) { status.textContent = 'Enter a token first'; return; }
        try {
            await API.put('/api/settings/github-token', { token });
            input.value = '';
            status.textContent = '✓ Token saved';
            status.className = 'token-ok';
        } catch (e) {
            status.textContent = `Failed to save: ${e.message}`;
        }
    });

    clearBtn?.addEventListener('click', async () => {
        try {
            await API.put('/api/settings/github-token', { token: '' });
            input.value = '';
            status.textContent = 'Token cleared';
            status.className = 'token-missing';
        } catch (e) {
            status.textContent = `Failed to clear: ${e.message}`;
        }
    });

    loadTokenStatus();
});
