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

            // Close mobile menu when a tab is selected
            if (sidebar) sidebar.classList.remove('mobile-open');
        });
    });

    // ----------------------------------------------------
    // CHARTS INITIALIZATION
    // ----------------------------------------------------
    let deptChart = null;
    let ratioChart = null;

    function initCharts(stats) {
        // Department Doughnut Chart
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

        // Ratio Bar Chart
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

    let rawBreakdowns = [];

    function renderBreakdownsTable(data) {
        rawBreakdowns = data;
        filterAndRenderTable();
    }

    function filterAndRenderTable() {
        const search = document.getElementById('table-search').value.toLowerCase();
        const status = document.getElementById('status-filter').value;
        const tbody = document.getElementById('breakdowns-table-body');

        const filtered = rawBreakdowns.filter(item => {
            const matchesSearch = item.equipment_id.toLowerCase().includes(search) ||
                                  item.ticket_number.toLowerCase().includes(search) ||
                                  item.department.toLowerCase().includes(search) ||
                                  item.issue_description.toLowerCase().includes(search);
            const matchesStatus = status === 'ALL' || item.status === status;
            return matchesSearch && matchesStatus;
        });

        if (!filtered.length) {
            tbody.innerHTML = '<tr><td colspan="9" class="text-center text-muted">No breakdown records match criteria.</td></tr>';
            return;
        }

        tbody.innerHTML = filtered.map(item => {
            const isResolved = item.status === 'RESOLVED';
            const actionBtn = isResolved 
                ? '<span class="text-success" style="font-size: 0.8rem">Resolved</span>'
                : `<button class="btn btn-emerald btn-resolve-row" data-ticket="${item.ticket_number}" data-eq="${item.equipment_id}" style="padding: 0.25rem 0.65rem; font-size: 0.78rem;">Resolve</button>`;

            const durationStr = isResolved 
                ? `${item.duration_minutes} mins` 
                : '<span class="text-danger">Active Down</span>';

            return `
                <tr>
                    <td><strong>${item.ticket_number}</strong></td>
                    <td><span class="badge 247-badge">${item.department}</span></td>
                    <td><strong>${item.equipment_id}</strong></td>
                    <td>${item.issue_description}</td>
                    <td><span class="status-pill ${item.status}">${item.status}</span></td>
                    <td>${item.start_time.slice(0, 16).replace('T', ' ')}</td>
                    <td>${item.end_time ? item.end_time.slice(0, 16).replace('T', ' ') : '-'}</td>
                    <td>${durationStr}</td>
                    <td>${actionBtn}</td>
                </tr>
            `;
        }).join('');

        // Attach event listeners to Resolve buttons
        document.querySelectorAll('.btn-resolve-row').forEach(btn => {
            btn.addEventListener('click', () => {
                const ticket = btn.getAttribute('data-ticket');
                const eq = btn.getAttribute('data-eq');
                openResolveModal(ticket, eq);
            });
        });
    }

    document.getElementById('table-search').addEventListener('input', filterAndRenderTable);
    document.getElementById('status-filter').addEventListener('change', filterAndRenderTable);

    // ----------------------------------------------------
    // RESOLVE MODAL
    // ----------------------------------------------------
    const modal = document.getElementById('modal-resolve');
    let currentResolveTicket = null;

    function openResolveModal(ticket, eq) {
        currentResolveTicket = ticket;
        document.getElementById('modal-ticket-info').innerText = `Resolving Breakdown Ticket ${ticket} (${eq})`;
        document.getElementById('modal-resolution').value = '';
        modal.classList.add('active');
    }

    document.getElementById('btn-close-modal').addEventListener('click', () => {
        modal.classList.remove('active');
    });

    document.getElementById('btn-confirm-resolve').addEventListener('click', async () => {
        const resolution = document.getElementById('modal-resolution').value.trim();
        const tech = document.getElementById('modal-tech').value.trim() || 'Technician';

        if (!resolution) {
            alert('Please enter resolution notes.');
            return;
        }

        try {
            const res = await fetch('/api/breakdowns/resolve', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ticket_number: currentResolveTicket,
                    resolution_notes: resolution,
                    technician: tech
                })
            });

            if (res.ok) {
                modal.classList.remove('active');
                refreshAll();
            } else {
                const err = await res.json();
                alert(err.detail || 'Error resolving breakdown');
            }
        } catch (e) {
            console.error(e);
        }
    });

    // Quick Log Breakdown button
    document.getElementById('btn-quick-log').addEventListener('click', () => {
        const dept = prompt("Enter Department Name:", "Production Line A");
        if (!dept) return;
        const eq = prompt("Enter Equipment ID / Name:", "Compressor #1");
        if (!eq) return;
        const issue = prompt("Enter Issue Description:", "Overheating pressure valve");
        if (!issue) return;

        fetch('/api/breakdowns/log', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                department: dept,
                equipment_id: eq,
                issue_description: issue
            })
        }).then(r => r.json()).then(() => refreshAll());
    });

    // ----------------------------------------------------
    // WHATSAPP SIMULATOR LOGIC
    // ----------------------------------------------------
    const simInput = document.getElementById('sim-input');
    const simSendBtn = document.getElementById('sim-send-btn');
    const chatMessages = document.getElementById('chat-messages');

    async function sendSimulatedMessage(text) {
        if (!text.trim()) return;

        // Append user bubble
        appendChatBubble(text, 'sent');
        simInput.value = '';

        try {
            const res = await fetch('/api/simulator/send', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: text,
                    department: 'Production',
                    sender_name: 'Shift Supervisor'
                })
            });

            const data = await res.json();
            // Append WhatsApp bot reply
            appendChatBubble(data.reply.replace(/\*(.*?)\*/g, '<b>$1</b>'), 'received');
            refreshAll();
        } catch (err) {
            appendChatBubble('⚠️ Error connecting to server backend.', 'received');
        }
    }

    function appendChatBubble(htmlContent, type) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `msg msg-${type}`;
        msgDiv.innerHTML = htmlContent.replace(/\n/g, '<br>');
        chatMessages.appendChild(msgDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    simSendBtn.addEventListener('click', () => sendSimulatedMessage(simInput.value));
    simInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendSimulatedMessage(simInput.value);
    });

    document.querySelectorAll('.preset-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const msg = btn.getAttribute('data-msg');
            sendSimulatedMessage(msg);
        });
    });

    // ----------------------------------------------------
    // SETTINGS LOGIC
    // ----------------------------------------------------
    async function loadSettings() {
        try {
            const res = await fetch('/api/settings');
            const data = await res.json();

            document.getElementById('cfg-sheet-id').value = data.spreadsheet_id || '';
            document.getElementById('cfg-sheet-name').value = data.sheet_name || 'Maintenance_Logs';
            document.getElementById('cfg-meta-token').value = data.meta_token || '';
            document.getElementById('cfg-phone-id').value = data.phone_number_id || '';
            document.getElementById('cfg-verify-token').value = data.verify_token || 'antigravity_verify_123';

            const statusEl = document.getElementById('json-status-text');
            if (data.has_google_credentials && data.has_spreadsheet_configured) {
                statusEl.innerHTML = '✅ <b>Google Sheets fully configured!</b> Credentials + Spreadsheet ID both active.';
                statusEl.style.color = '#10b981';
            } else if (data.has_google_credentials && !data.has_spreadsheet_configured) {
                statusEl.innerHTML = '⚠️ <b>Credentials loaded</b> but Spreadsheet ID is missing. Add GOOGLE_SPREADSHEET_ID to Render env vars.';
                statusEl.style.color = '#f59e0b';
            } else if (!data.has_google_credentials && data.has_spreadsheet_configured) {
                statusEl.innerHTML = '⚠️ <b>Spreadsheet ID set</b> but service account credentials missing. Add GOOGLE_SERVICE_ACCOUNT_JSON to Render env vars.';
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
            if (data.synced_breakdowns !== undefined) {
                statusEl.innerHTML = `✅ <b>Sync complete!</b> ${data.synced_breakdowns} breakdown(s) and ${data.synced_pm} PM log(s) pushed to Google Sheets.` +
                    (data.errors.length ? `<br>⚠️ ${data.errors.length} error(s): ${data.errors[0]}` : '');
                statusEl.style.color = data.errors.length ? '#f59e0b' : '#10b981';
            } else {
                statusEl.textContent = '⚠️ Sync attempted — check Render logs for details.';
            }
        } catch (e) {
            statusEl.textContent = '❌ Error connecting to server.';
            statusEl.style.color = '#ef4444';
        }

        btn.disabled = false;
        btn.textContent = '⬆️ Sync All Records to Google Sheets Now';
    });

    document.getElementById('btn-save-meta').addEventListener('click', async () => {
        const token = document.getElementById('cfg-meta-token').value.trim();
        const phoneId = document.getElementById('cfg-phone-id').value.trim();
        const verifyToken = document.getElementById('cfg-verify-token').value.trim();

        await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ meta_token: token, phone_number_id: phoneId, verify_token: verifyToken })
        });
        alert('WhatsApp settings saved!');
    });

    // File upload for JSON key
    const jsonInput = document.getElementById('json-file-input');
    jsonInput.addEventListener('change', async () => {
        if (!jsonInput.files.length) return;
        const formData = new FormData();
        formData.append('file', jsonInput.files[0]);

        try {
            const res = await fetch('/api/credentials/upload', {
                method: 'POST',
                body: formData
            });

            if (res.ok) {
                document.getElementById('json-status-text').innerHTML = '✅ <b>service_account.json uploaded & verified successfully!</b>';
            } else {
                alert('Invalid JSON file.');
            }
        } catch (e) {
            console.error(e);
        }
    });

    // ----------------------------------------------------
    // BAILEYS WHATSAPP QR CODE CONTROLLER
    // ----------------------------------------------------
    async function checkBaileysQR() {
        try {
            const res = await fetch('/api/baileys/status');
            const data = await res.json();
            const loadingText = document.getElementById('qr-loading-text');
            const qrImg = document.getElementById('qr-code-img');
            const badge = document.getElementById('qr-status-badge');

            if (!loadingText || !qrImg || !badge) return;

            if (data.status === 'CONNECTED') {
                loadingText.style.display = 'none';
                qrImg.style.display = 'none';
                badge.innerHTML = '🟢 <b>CONNECTED TO WHATSAPP 24/7</b>';
                badge.className = 'badge 247-badge';
            } else if (data.qrCode) {
                loadingText.style.display = 'none';
                qrImg.style.display = 'block';
                qrImg.src = data.qrCode;
                badge.innerHTML = '⚡ <b>SCAN QR CODE WITH WHATSAPP ON YOUR PHONE</b>';
                badge.className = 'badge text-warning';
            } else {
                loadingText.innerText = 'Click "Generate / Reset QR Code" below to display WhatsApp QR code...';
                loadingText.style.display = 'block';
                qrImg.style.display = 'none';
                badge.innerText = 'Status: ' + (data.status || 'Disconnected');
            }
        } catch (e) {
            console.error('Error fetching Baileys status:', e);
        }
    }

    const startQrBtn = document.getElementById('btn-start-qr');
    if (startQrBtn) {
        startQrBtn.addEventListener('click', () => {
            fetch('/api/baileys/start', { method: 'POST' }).then(() => checkBaileysQR());
        });
    }

    setInterval(checkBaileysQR, 3000);
    checkBaileysQR();

    function refreshAll() {
        loadStats();
        loadBreakdowns();
        loadPM();
    }

    // Initial load
    refreshAll();
    loadSettings();

    // Auto refresh stats every 10 seconds
    setInterval(refreshAll, 10000);
});
