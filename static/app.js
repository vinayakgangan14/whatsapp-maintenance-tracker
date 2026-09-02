document.addEventListener('DOMContentLoaded', () => {
    // ----------------------------------------------------
    // MOBILE NAVIGATION TOGGLE
    // ----------------------------------------------------
    const mobileMenuBtn = document.getElementById('mobile-menu-btn');
    const sidebar = document.querySelector('.sidebar');

    if (mobileMenuBtn && sidebar) {
        mobileMenuBtn.addEventListener('click', () => {
            sidebar.classList.toggle('mobile-open');
        });
    }

    // ----------------------------------------------------
    // TAB NAVIGATION
    // ----------------------------------------------------
    const navItems = document.querySelectorAll('.nav-item');
    const tabPanes = document.querySelectorAll('.tab-pane');

    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const targetTab = item.getAttribute('data-tab');
            
            navItems.forEach(n => n.classList.remove('active'));
            tabPanes.forEach(p => p.classList.remove('active'));

            item.classList.add('active');
            const targetElement = document.getElementById(targetTab);
            if (targetElement) targetElement.classList.add('active');

            if (sidebar) sidebar.classList.remove('mobile-open');
        });
    });

    // ----------------------------------------------------
    // CHARTS INITIALIZATION
    // ----------------------------------------------------
    let deptChart = null;
    let ratioChart = null;

    function initCharts(stats) {
        const deptCtx = document.getElementById('chartDepartment').getContext('2d');
        const deptLabels = Object.keys(stats.department_distribution || {});
        const deptData = Object.values(stats.department_distribution || {});

        if (deptChart) deptChart.destroy();
        deptChart = new Chart(deptCtx, {
            type: 'doughnut',
            data: {
                labels: deptLabels.length ? deptLabels : ['No Incidents'],
                datasets: [{
                    data: deptData.length ? deptData : [1],
                    backgroundColor: ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ef4444', '#06b6d4'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { labels: { color: '#9ca3af', font: { family: 'Inter' } } }
                }
            }
        });

        const ratioCtx = document.getElementById('chartRatio').getContext('2d');
        if (ratioChart) ratioChart.destroy();
        ratioChart = new Chart(ratioCtx, {
            type: 'bar',
            data: {
                labels: ['Open Incidents', 'Resolved Tickets', 'PM Activities'],
                datasets: [{
                    label: 'Count',
                    data: [stats.open_breakdowns, stats.resolved_breakdowns, stats.total_pm_logs],
                    backgroundColor: ['#ef4444', '#10b981', '#3b82f6'],
                    borderRadius: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: { ticks: { color: '#9ca3af' }, grid: { display: false } },
                    y: { ticks: { color: '#9ca3af' }, grid: { color: 'rgba(255,255,255,0.05)' } }
                }
            }
        });
    }

    // ----------------------------------------------------
    // DATA FETCHING & REFRESH
    // ----------------------------------------------------
    async function loadStats() {
        try {
            const res = await fetch('/api/stats');
            const data = await res.json();

            document.getElementById('kpi-open-bd').innerText = data.open_breakdowns;
            document.getElementById('kpi-resolved-bd').innerText = data.resolved_breakdowns;
            document.getElementById('kpi-downtime').innerHTML = `${data.total_downtime_hours} <small style="font-size: 1rem">hrs</small>`;
            document.getElementById('kpi-downtime-mins').innerText = `${data.total_downtime_minutes} total minutes`;
            document.getElementById('kpi-mttr').innerHTML = `${data.mttr_minutes} <small style="font-size: 1rem">mins</small>`;
            if (document.getElementById('kpi-mtbf')) {
                document.getElementById('kpi-mtbf').innerHTML = `${data.mtbf_hours || 0} <small style="font-size: 1rem">hrs</small>`;
            }

            initCharts(data);
        } catch (err) {
            console.error('Error fetching stats:', err);
        }
    }

    async function loadBreakdowns() {
        try {
            const res = await fetch('/api/breakdowns');
            const data = await res.json();
            renderBreakdownsTable(data);
        } catch (err) {
            console.error('Error loading breakdowns:', err);
        }
    }

    async function loadPM() {
        try {
            const res = await fetch('/api/maintenance');
            const data = await res.json();
            const tbody = document.getElementById('pm-table-body');
            if (!tbody) return;
            if (!data.length) {
                tbody.innerHTML = '<tr><td colspan="6" class="text-center">No preventive maintenance logs found.</td></tr>';
                return;
            }
            tbody.innerHTML = data.map(item => `
                <tr>
                    <td><strong>${item.ticket_number}</strong></td>
                    <td><span class="badge 247-badge">${item.department}</span></td>
                    <td><strong>${item.equipment_id}</strong></td>
                    <td>${item.activity_description}</td>
                    <td>${item.technician}</td>
                    <td>${item.performed_at.slice(0, 16).replace('T', ' ')}</td>
                </tr>
            `).join('');
        } catch (err) {
            console.error('Error loading PM:', err);
        }
    }

    async function loadWelding() {
        try {
            const res = await fetch('/api/welding');
            const data = await res.json();
            const tbody = document.getElementById('welding-table-body');
            if (!tbody) return;
            if (!data.length) {
                tbody.innerHTML = '<tr><td colspan="7" class="text-center">No welding logs found.</td></tr>';
                return;
            }
            tbody.innerHTML = data.map(item => `
                <tr>
                    <td><strong>${item.ticket_number}</strong></td>
                    <td><span class="badge 247-badge">${item.department || item.location || 'General'}</span></td>
                    <td><strong>${item.equipment_id}</strong></td>
                    <td>${item.welding_details}</td>
                    <td>${item.scheduled_time || 'As Scheduled'}</td>
                    <td><span class="badge ${item.status === 'OPEN' ? 'status-open' : 'status-resolved'}">${item.status}</span></td>
                    <td>${item.technician || item.sender_name}</td>
                </tr>
            `).join('');
        } catch (err) {
            console.error('Error loading welding logs:', err);
        }
    }

    function renderBreakdownsTable(data) {
        const tbody = document.getElementById('breakdowns-table-body');
        const searchVal = document.getElementById('table-search').value.toLowerCase();
        const filterVal = document.getElementById('status-filter').value;

        const filtered = data.filter(item => {
            const matchesSearch = (
                item.ticket_number.toLowerCase().includes(searchVal) ||
                item.equipment_id.toLowerCase().includes(searchVal) ||
                item.issue_description.toLowerCase().includes(searchVal) ||
                item.department.toLowerCase().includes(searchVal)
            );

            let matchesStatus = true;
            if (filterVal === 'OPEN') matchesStatus = (item.status === 'OPEN');
            if (filterVal === 'RESOLVED') matchesStatus = (item.status === 'RESOLVED');

            return matchesSearch && matchesStatus;
        });

        if (!filtered.length) {
            tbody.innerHTML = '<tr><td colspan="9" class="text-center">No breakdowns matching filter.</td></tr>';
            return;
        }

        tbody.innerHTML = filtered.map(item => {
            const isResolved = item.status === 'RESOLVED';
            const statusBadge = isResolved
                ? `<span class="badge status-resolved">RESOLVED</span>`
                : `<span class="badge status-open">OPEN</span>`;

            const actionBtn = isResolved
                ? `<button class="btn btn-sm btn-outline" disabled>Closed</button>`
                : `<button class="btn btn-sm btn-emerald btn-resolve-action" data-ticket="${item.ticket_number}" data-eq="${item.equipment_id}">Resolve</button>`;

            const durationStr = isResolved ? `${item.duration_minutes} mins` : '-';
            const endTimeStr = item.end_time ? item.end_time.slice(0, 16).replace('T', ' ') : '-';

            return `
                <tr>
                    <td><strong>${item.ticket_number}</strong></td>
                    <td><span class="badge 247-badge">${item.department}</span></td>
                    <td><strong>${item.equipment_id}</strong></td>
                    <td>${item.issue_description}</td>
                    <td>${statusBadge}</td>
                    <td>${item.start_time.slice(0, 16).replace('T', ' ')}</td>
                    <td>${endTimeStr}</td>
                    <td>${durationStr}</td>
                    <td>${actionBtn}</td>
                </tr>
            `;
        }).join('');

        document.querySelectorAll('.btn-resolve-action').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const ticket = e.target.getAttribute('data-ticket');
                const eq = e.target.getAttribute('data-eq');
                openResolveModal(ticket, eq);
            });
        });
    }

    document.getElementById('table-search').addEventListener('input', () => loadBreakdowns());
    document.getElementById('status-filter').addEventListener('change', () => loadBreakdowns());

    // ----------------------------------------------------
    // MODALS HANDLING
    // ----------------------------------------------------
    const resolveModal = document.getElementById('modal-resolve');
    let currentResolveTicket = null;
    let currentResolveEq = null;

    function openResolveModal(ticket, eq) {
        currentResolveTicket = ticket;
        currentResolveEq = eq;
        document.getElementById('modal-ticket-info').innerText = `Closing Ticket: ${ticket} (${eq})`;
        document.getElementById('modal-resolution').value = '';
        document.getElementById('modal-tech').value = '';
        if (resolveModal) resolveModal.classList.add('active');
    }

    if (document.getElementById('btn-close-modal')) {
        document.getElementById('btn-close-modal').addEventListener('click', () => {
            if (resolveModal) resolveModal.classList.remove('active');
        });
    }

    if (document.getElementById('btn-confirm-resolve')) {
        document.getElementById('btn-confirm-resolve').addEventListener('click', async () => {
            const notes = document.getElementById('modal-resolution').value.trim();
            const tech = document.getElementById('modal-tech').value.trim();

            if (!notes) {
                alert('Please enter resolution notes.');
                return;
            }

            try {
                const res = await fetch('/api/breakdowns/resolve', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        ticket_number: currentResolveTicket,
                        equipment_id: currentResolveEq,
                        resolution_notes: notes,
                        technician: tech || 'Web Portal User'
                    })
                });

                if (res.ok) {
                    if (resolveModal) resolveModal.classList.remove('active');
                    refreshAll();
                } else {
                    const errData = await res.json();
                    alert('Error: ' + (errData.detail || 'Could not resolve ticket'));
                }
            } catch (e) {
                console.error(e);
            }
        });
    }

    // Quick Log Breakdown Modal
    const bdModal = document.getElementById('modal-log-bd');
    document.getElementById('btn-quick-log').addEventListener('click', () => {
        document.getElementById('modal-bd-eq').value = '';
        document.getElementById('modal-bd-issue').value = '';
        if (bdModal) bdModal.classList.add('active');
    });

    if (document.getElementById('btn-close-bd-modal')) {
        document.getElementById('btn-close-bd-modal').addEventListener('click', () => {
            if (bdModal) bdModal.classList.remove('active');
        });
    }

    if (document.getElementById('btn-confirm-log-bd')) {
        document.getElementById('btn-confirm-log-bd').addEventListener('click', async () => {
            const plant = document.getElementById('modal-bd-plant').value;
            const eq = document.getElementById('modal-bd-eq').value.trim();
            const issue = document.getElementById('modal-bd-issue').value.trim();

            if (!eq || !issue) {
                alert('Please enter both equipment details and issue description.');
                return;
            }

            try {
                await fetch('/api/breakdowns/log', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        department: plant,
                        equipment_id: eq,
                        issue_description: issue,
                        sender_name: 'Web Portal User'
                    })
                });
                if (bdModal) bdModal.classList.remove('active');
                refreshAll();
            } catch (e) {
                console.error(e);
            }
        });
    }

    // ----------------------------------------------------
    // SETTINGS & SYNC HANDLERS
    // ----------------------------------------------------
    async function loadSettings() {
        try {
            const res = await fetch('/api/settings');
            const data = await res.json();

            document.getElementById('cfg-sheet-id').value = data.spreadsheet_id || '';
            document.getElementById('cfg-sheet-name').value = data.sheet_name || 'Maintenance_Logs';

            const statusEl = document.getElementById('json-status-text');
            if (data.has_google_credentials && data.has_spreadsheet_configured) {
                statusEl.innerHTML = '✅ <b>Google Sheets fully configured!</b> Real-time sync active.';
                statusEl.style.color = '#10b981';
            } else if (data.has_google_credentials && !data.has_spreadsheet_configured) {
                statusEl.innerHTML = '⚠️ <b>Credentials loaded</b> but Spreadsheet ID missing.';
                statusEl.style.color = '#f59e0b';
            } else {
                statusEl.innerHTML = '❌ Google Sheets not configured. Add GOOGLE_SERVICE_ACCOUNT_JSON and GOOGLE_SPREADSHEET_ID to Render env vars.';
                statusEl.style.color = '#ef4444';
            }
        } catch (err) {
            console.error('Error loading settings:', err);
        }
    }

    document.getElementById('btn-save-sheets').addEventListener('click', async () => {
        const sheetId = document.getElementById('cfg-sheet-id').value.trim();
        const sheetName = document.getElementById('cfg-sheet-name').value.trim();

        await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ spreadsheet_id: sheetId, sheet_name: sheetName })
        });
        alert('Google Sheets configuration saved!');
    });

    document.getElementById('btn-sync-all').addEventListener('click', async () => {
        const statusEl = document.getElementById('sync-all-status');
        const btn = document.getElementById('btn-sync-all');
        btn.disabled = true;
        btn.textContent = '⏳ Syncing... please wait';
        statusEl.textContent = '';

        try {
            const res = await fetch('/api/sync-all', { method: 'POST' });
            const data = await res.json();
            if (data.error) {
                statusEl.innerHTML = `⚠️ <b>Sync Error:</b> ${data.error}`;
                statusEl.style.color = '#ef4444';
            } else if (data.synced_breakdowns !== undefined) {
                statusEl.innerHTML = `✅ <b>Sync complete!</b> All records synced to Google Sheets.`;
                statusEl.style.color = '#10b981';
            } else {
                statusEl.textContent = '⚠️ Sync response received.';
            }
        } catch (e) {
            statusEl.textContent = '❌ Connection error: ' + (e.message || e);
            statusEl.style.color = '#ef4444';
        }

        btn.disabled = false;
        btn.textContent = '⬆️ Sync All Records to Google Sheets Now';
    });

    // Client Handover Reset Button
    if (document.getElementById('btn-reset-db')) {
        document.getElementById('btn-reset-db').addEventListener('click', async () => {
            if (!confirm('⚠️ Are you sure you want to clear ALL breakdown tickets and maintenance records for client handover? This action cannot be undone.')) {
                return;
            }

            const statusEl = document.getElementById('reset-db-status');
            try {
                const res = await fetch('/api/reset-database', { method: 'POST' });
                await res.json();
                statusEl.innerHTML = '✅ <b>All test records cleared successfully!</b> Ready for fresh client handover.';
                statusEl.style.color = '#10b981';
                refreshAll();
            } catch (e) {
                statusEl.textContent = '❌ Error clearing database.';
                statusEl.style.color = '#ef4444';
            }
        });
    }

    function refreshAll() {
        loadStats();
        loadBreakdowns();
        loadPM();
        loadWelding();
    }

    // Initial load
    refreshAll();
    loadSettings();

    // Auto refresh stats every 10 seconds
    setInterval(refreshAll, 10000);
});
