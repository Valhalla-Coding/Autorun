// AutoRun v2 - Dashboard Settings Panel

document.addEventListener('DOMContentLoaded', () => {
    const toggle  = $('#dashboard-settings-toggle');
    const body    = $('#dashboard-settings-body');
    const input   = $('#dashboard-port-input');
    const saveBtn = $('#dashboard-port-save');
    const status  = $('#dashboard-port-status');

    if (!toggle) return;

    toggle.addEventListener('click', () => {
        const collapsed = body.style.display === 'none';
        body.style.display = collapsed ? '' : 'none';
        toggle.querySelector('.collapse-icon').textContent = collapsed ? '▾' : '▸';
    });

    async function loadCurrentPort() {
        try {
            const res = await API.get('/api/settings/dashboard-port');
            if (res.status === 'success') {
                input.value = res.data.port;
                status.textContent = `Current port: ${res.data.port}`;
            }
        } catch {
            status.textContent = 'Could not load current port';
        }
    }

    saveBtn?.addEventListener('click', async () => {
        const port = parseInt(input.value, 10);
        if (!port || port < 1 || port > 65535) {
            status.textContent = 'Enter a valid port (1–65535)';
            return;
        }
        try {
            saveBtn.disabled = true;
            saveBtn.textContent = 'Saving…';
            const res = await API.put('/api/settings/dashboard-port', { port });
            status.textContent = res.message || 'Saved. Reconnect at the new port.';
            notify.success(res.message || 'Port saved — server is restarting');
        } catch (e) {
            status.textContent = `Failed: ${e.message}`;
            saveBtn.disabled = false;
            saveBtn.textContent = 'Save & Restart';
        }
    });

    loadCurrentPort();
});
