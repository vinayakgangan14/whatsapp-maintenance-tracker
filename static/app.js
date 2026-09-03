document.addEventListener('DOMContentLoaded', () => {
    // ----------------------------------------------------
    // PURECHEM EQUIPMENT BY PLANT MAPPING
    // ----------------------------------------------------
    const EQUIPMENT_BY_PLANT = {
        "Utility": [
            "NEPA 33KVA TRANSFORMER",
            "CAT GG-1218 KVA",
            "CAT GG-600 KVA",
            "PERKINS GG-500 KVA",
            "CAT DG-1100 KVA",
            "PERKINS DG-500 KVA",
            "LT ROOM",
            "STEAM BOILER -1",
            "STEAM BOILER -2",
            "THERMIC BOILER -3",
            "HERZT COMPRESSOR",
            "ELGI COMPRESSOR",
            "FIRE HYDRATANT SYSTEM",
            "COOLING TOWER",
            "DM WATER PLANT",
            "ETP PLANT"
        ],
        "LCP/PU": [
            "LCP REACTOR-1",
            "LCP REACTOR-2",
            "PU REACTOR-1",
            "PU REACTOR-2",
            "PU REACTOR-3",
            "PU REACTOR-4",
            "PU REACTOR-5",
            "TOP GIT FILLING / CAPPING MACHINE",
            "TOP GUM FILLING / LABELLING MACHINE"
        ],
        "PVAC": [
            "PVAC-1 REACTOR-1",
            "PVAC-1 REACTOR-2",
            "PROCESSSING VESSEL -1",
            "PROCESSSING VESSEL -2",
            "HOLDING TANK( 1,2 & 3)",
            "TOPBOUND PRODUCTION LINE-1 (10-20 KG)",
            "TOPBOUND PRODUCTION LINE-2 (2-10 KG)",
            "TOPBOUND PRODUCTION LINE-3 (100G-1 KG)",
            "TOPBOUND PRODUCTION LINE-4 (250G-1 KG)"
        ],
        "PVAC Extension": [
            "PVAC-2 REACTOR-1 (5KL)",
            "PVAC-2 BLENDER-2 (20KL)"
        ],
        "DCP": [
            "SAND PLANT",
            "BLENDER -2",
            "BLENDER -3",
            "BLENDER -4",
            "BLENDER -5",
            "BLENDER -6"
        ],
        "Plastic": [
            "1LTR-1",
            "1LTR-2",
            "2LTR-DH",
            "1LTR.DH",
            "5LTR.S/S",
            "5LTR-DH",
            "IBM(Injection Blow Molding)",
            "Omega-1",
            "Omega-2",
            "Omega-3",
            "Hydron-1",
            "Hydron-2",
            "SP750 Printing Machine",
            "SPVL1OOO Printing Machine",
            "TECHNO PRINT 5 kg",
            "TECHNO PRINT 10 kg",
            "UV Printing Machine"
        ]
    };

    function updateEquipmentOptions(plantSelectId, equipmentSelectId) {
        const plantSelect = document.getElementById(plantSelectId);
        const eqSelect = document.getElementById(equipmentSelectId);
        if (!plantSelect || !eqSelect) return;

        const selectedPlant = plantSelect.value;
        const items = EQUIPMENT_BY_PLANT[selectedPlant] || [];

        eqSelect.innerHTML = '<option value="">-- Select Equipment --</option>' +
            items.map(eq => `<option value="${eq}">${eq}</option>`).join('');
    }

    ['modal-bd-plant', 'modal-pm-plant', 'modal-wd-plant'].forEach(plantId => {
        const el = document.getElementById(plantId);
        if (el) {
            const eqId = plantId.replace('-plant', '-eq');
            el.addEventListener('change', () => updateEquipmentOptions(plantId, eqId));
            updateEquipmentOptions(plantId, eqId);
        }
    });

    // ----------------------------------------------------
    // PURECHEM MAINTENANCE STAFF LIST
    // ----------------------------------------------------
    const MAINTENANCE_STAFF = [
        "MR. RAJU NEEL - MAINTENANCE MANAGER",
        "Mr. Shanmugham - MAINTENANCE MANAGER",
        "AKEEM ELEGBEDE - MAINTENANCE ASST.",
        "NKWOR HENRY - MECHANICAL Dept",
        "AFOLABI BABATUNDEY - ELECTRICAL Dept",
        "OLAOLUWA ADEADOYIN - ELECTRICAL Dept",
        "SAMSUDEEN ABOLADE - ELECTRICAL Dept",
        "DAMILOLA OYAMOYE - ELECTRICAL Dept",
        "ANDREW PETER - MECHANICAL Dept",
        "IRIYOMINE MATHEW - MECHANICAL Dept",
        "JULIOUS SAMUEL - MECHANICAL Dept",
        "MUYIDEEN SOLABI - MECHANICAL Dept",
        "AFEEZ BELLO - MECHANICAL Dept",
        "OLUWAJAYOGBE TUNDE - ELECTRICAL Dept",
        "IDOWU SAMUEL - ELECTRICAL Dept"
    ];

    function populateStaffDropdowns() {
        document.querySelectorAll('.staff-dropdown').forEach(select => {
            select.innerHTML = '<option value="Unassigned">-- Select Maintenance Staff --</option>' +
                MAINTENANCE_STAFF.map(staff => `<option value="${staff}">${staff}</option>`).join('');
        });
    }
    populateStaffDropdowns();

    // ----------------------------------------------------
    // AUTH & ROLE MANAGEMENT
    // ----------------------------------------------------
    let currentUserRole = localStorage.getItem('pure_role') || null;
    let currentUsername = localStorage.getItem('pure_username') || null;

    const loginModal = document.getElementById('login-modal');
    const roleSelect = document.getElementById('login-role');
    const passcodeGroup = document.getElementById('passcode-group');
    const passcodeBtn = document.getElementById('btn-login-submit');

    if (roleSelect) {
        roleSelect.addEventListener('change', () => {
            if (roleSelect.value === 'Manager') {
                passcodeGroup.style.display = 'block';
            } else {
                passcodeGroup.style.display = 'none';
            }
        });
    }

    if (passcodeBtn) {
        passcodeBtn.addEventListener('click', () => {
            const role = document.getElementById('login-role').value;
            const username = document.getElementById('login-username').value.trim() || 'User';
            const passcode = document.getElementById('login-passcode').value.trim();

            if (role === 'Manager' && passcode !== 'admin123') {
                alert('Invalid Manager Passcode! (Default passcode: admin123)');
                return;
            }

            currentUserRole = role;
            currentUsername = username;
            localStorage.setItem('pure_role', role);
            localStorage.setItem('pure_username', username);

            if (loginModal) loginModal.classList.remove('active');
            updateUserDisplay();
            refreshAll();
        });
    }

    function updateUserDisplay() {
        if (!currentUserRole) {
            if (loginModal) loginModal.classList.add('active');
            return;
        }
        if (loginModal) loginModal.classList.remove('active');

        const roleBadge = document.getElementById('sidebar-role-badge');
        const userDisplay = document.getElementById('logged-user-display');
        if (roleBadge) {
            roleBadge.innerText = currentUserRole === 'Manager' ? '👑 Manager Mode' : '👷 Operator Mode';
            roleBadge.className = currentUserRole === 'Manager' ? 'badge' : 'badge 247-badge';
            if (currentUserRole === 'Manager') roleBadge.style.background = '#8b5cf6';
        }
        if (userDisplay) {
            userDisplay.innerText = `${currentUsername} (${currentUserRole})`;
        }
    }

    document.getElementById('btn-logout').addEventListener('click', () => {
        localStorage.removeItem('pure_role');
        localStorage.removeItem('pure_username');
        currentUserRole = null;
        currentUsername = null;
        if (loginModal) loginModal.classList.add('active');
    });

    updateUserDisplay();

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
                tbody.innerHTML = '<tr><td colspan="8" class="text-center">No preventive maintenance logs found.</td></tr>';
                return;
            }
            tbody.innerHTML = data.map(item => {
                const statusHtml = renderStatusBadge(item.status);
                const assignedHtml = renderAssignedToColumn(item);
                const actionHtml = renderActionButtons(item);
                return `
                <tr>
                    <td><strong>${item.ticket_number}</strong></td>
                    <td><span class="badge 247-badge">${item.department}</span></td>
                    <td><strong>${item.equipment_id}</strong></td>
                    <td>${item.activity_description}</td>
                    <td>${item.scheduled_time || 'As Scheduled'}</td>
                    <td>${statusHtml}</td>
                    <td>${assignedHtml}</td>
                    <td>${actionHtml}</td>
                </tr>
            `}).join('');

            bindApprovalEvents();
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
                tbody.innerHTML = '<tr><td colspan="8" class="text-center">No welding logs found.</td></tr>';
                return;
            }
            tbody.innerHTML = data.map(item => {
                const statusHtml = renderStatusBadge(item.status);
                const assignedHtml = renderAssignedToColumn(item);
                const actionHtml = renderActionButtons(item);
                return `
                <tr>
                    <td><strong>${item.ticket_number}</strong></td>
                    <td><span class="badge 247-badge">${item.department || item.location || 'General'}</span></td>
                    <td><strong>${item.equipment_id}</strong></td>
                    <td>${item.welding_details}</td>
                    <td>${item.scheduled_time || 'As Scheduled'}</td>
                    <td>${statusHtml}</td>
                    <td>${assignedHtml}</td>
                    <td>${actionHtml}</td>
                </tr>
            `}).join('');

            bindApprovalEvents();
        } catch (err) {
            console.error('Error loading welding logs:', err);
        }
    }

    function renderStatusBadge(status) {
        if (status === 'PENDING_APPROVAL') {
            return `<span class="badge" style="background: rgba(245, 158, 11, 0.15); color: #f59e0b; border: 1px solid #f59e0b;">⏳ PENDING APPROVAL</span>`;
        }
        if (status === 'APPROVED' || status === 'OPEN') {
            return `<span class="badge" style="background: rgba(59, 130, 246, 0.15); color: #3b82f6; border: 1px solid #3b82f6;">⚡ APPROVED / OPEN</span>`;
        }
        if (status === 'RESOLVED') {
            return `<span class="badge status-resolved">✅ RESOLVED</span>`;
        }
        if (status === 'REJECTED') {
            return `<span class="badge" style="background: rgba(239, 68, 68, 0.15); color: #ef4444; border: 1px solid #ef4444;">❌ REJECTED</span>`;
        }
        return `<span class="badge status-open">${status}</span>`;
    }

    function renderAssignedToColumn(item) {
        const assigned = item.assigned_to || 'Unassigned';
        if (currentUserRole === 'Manager') {
            const options = MAINTENANCE_STAFF.map(s => `<option value="${s}" ${s === assigned ? 'selected' : ''}>${s}</option>`).join('');
            return `
                <select class="form-control btn-assign-staff" data-ticket="${item.ticket_number}" style="padding: 4px 8px; font-size: 0.8rem; border-radius: 6px; background: rgba(0,0,0,0.5); color: #fff; border: 1px solid rgba(255,255,255,0.2); max-width: 180px;">
                    <option value="Unassigned" ${assigned === 'Unassigned' ? 'selected' : ''}>-- Unassigned --</option>
                    ${options}
                </select>
            `;
        }
        return `<span class="badge" style="background: rgba(255,255,255,0.06); color: #e2e8f0; font-size:0.8rem;">${assigned}</span>`;
    }

    function renderActionButtons(item) {
        const isResolved = item.status === 'RESOLVED' || item.status === 'REJECTED';
        const isPending = item.status === 'PENDING_APPROVAL';

        if (isResolved) {
            return `<button class="btn btn-sm btn-outline" disabled>Closed</button>`;
        }

        // OPERATOR/TECHNICIAN ROLE: NO RESOLVE/APPROVE RIGHTS!
        if (currentUserRole === 'Operator') {
            return `<button class="btn btn-sm btn-outline" disabled style="opacity:0.6;">Manager Only</button>`;
        }

        // MAINTENANCE MANAGER ROLE: HAS FULL APPROVE, REJECT, AND RESOLVE RIGHTS!
        if (currentUserRole === 'Manager' && isPending) {
            return `
                <button class="btn btn-sm btn-emerald btn-approve-action" data-ticket="${item.ticket_number}" style="margin-right:4px;">Approve</button>
                <button class="btn btn-sm btn-outline btn-reject-action" data-ticket="${item.ticket_number}" style="border-color:#ef4444;color:#ef4444;">Reject</button>
            `;
        }

        return `<button class="btn btn-sm btn-emerald btn-resolve-action" data-ticket="${item.ticket_number}" data-eq="${item.equipment_id}">Resolve</button>`;
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
                item.department.toLowerCase().includes(searchVal) ||
                (item.assigned_to && item.assigned_to.toLowerCase().includes(searchVal))
            );

            let matchesStatus = true;
            if (filterVal === 'PENDING_APPROVAL') matchesStatus = (item.status === 'PENDING_APPROVAL');
            if (filterVal === 'OPEN') matchesStatus = (item.status === 'OPEN' || item.status === 'APPROVED');
            if (filterVal === 'RESOLVED') matchesStatus = (item.status === 'RESOLVED');

            return matchesSearch && matchesStatus;
        });

        if (!filtered.length) {
            tbody.innerHTML = '<tr><td colspan="10" class="text-center">No breakdowns matching filter.</td></tr>';
            return;
        }

        tbody.innerHTML = filtered.map(item => {
            const statusHtml = renderStatusBadge(item.status);
            const assignedHtml = renderAssignedToColumn(item);
            const actionHtml = renderActionButtons(item);
            const durationStr = item.status === 'RESOLVED' ? `${item.duration_minutes} mins` : '-';
            const endTimeStr = item.end_time ? item.end_time.slice(0, 16).replace('T', ' ') : '-';

            return `
                <tr>
                    <td><strong>${item.ticket_number}</strong></td>
                    <td><span class="badge 247-badge">${item.department}</span></td>
                    <td><strong>${item.equipment_id}</strong></td>
                    <td>${item.issue_description}</td>
                    <td>${statusHtml}</td>
                    <td>${assignedHtml}</td>
                    <td>${item.start_time.slice(0, 16).replace('T', ' ')}</td>
                    <td>${endTimeStr}</td>
                    <td>${durationStr}</td>
                    <td>${actionHtml}</td>
                </tr>
            `;
        }).join('');

        bindApprovalEvents();
    }

    function bindApprovalEvents() {
        document.querySelectorAll('.btn-resolve-action').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const ticket = e.target.getAttribute('data-ticket');
                const eq = e.target.getAttribute('data-eq');
                openResolveModal(ticket, eq);
            });
        });

        document.querySelectorAll('.btn-approve-action').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const ticket = e.target.getAttribute('data-ticket');
                try {
                    await fetch('/api/ticket/approve', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ ticket_number: ticket, manager_name: currentUsername })
                    });
                    refreshAll();
                } catch (err) { console.error(err); }
            });
        });

        document.querySelectorAll('.btn-reject-action').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const ticket = e.target.getAttribute('data-ticket');
                const reason = prompt("Enter rejection reason (optional):", "Scope out of bounds");
                try {
                    await fetch('/api/ticket/reject', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ ticket_number: ticket, manager_name: currentUsername, reason: reason || '' })
                    });
                    refreshAll();
                } catch (err) { console.error(err); }
            });
        });

        document.querySelectorAll('.btn-assign-staff').forEach(select => {
            select.addEventListener('change', async (e) => {
                const ticket = e.target.getAttribute('data-ticket');
                const assignedTo = e.target.value;
                try {
                    await fetch('/api/ticket/assign', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ ticket_number: ticket, assigned_to: assignedTo })
                    });
                    refreshAll();
                } catch (err) { console.error(err); }
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
        document.getElementById('modal-tech').value = currentUsername || '';
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
                        technician: tech || currentUsername || 'Technician'
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
        updateEquipmentOptions('modal-bd-plant', 'modal-bd-eq');
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
                alert('Please select an equipment and enter issue description.');
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
                        sender_name: currentUsername || 'Portal User'
                    })
                });
                if (bdModal) bdModal.classList.remove('active');
                refreshAll();
            } catch (e) {
                console.error(e);
            }
        });
    }

    // Schedule PM Modal
    const pmModal = document.getElementById('modal-log-pm');
    if (document.getElementById('btn-schedule-pm')) {
        document.getElementById('btn-schedule-pm').addEventListener('click', () => {
            updateEquipmentOptions('modal-pm-plant', 'modal-pm-eq');
            document.getElementById('modal-pm-desc').value = '';
            if (pmModal) pmModal.classList.add('active');
        });
    }

    if (document.getElementById('btn-close-pm-modal')) {
        document.getElementById('btn-close-pm-modal').addEventListener('click', () => {
            if (pmModal) pmModal.classList.remove('active');
        });
    }

    if (document.getElementById('btn-confirm-log-pm')) {
        document.getElementById('btn-confirm-log-pm').addEventListener('click', async () => {
            const plant = document.getElementById('modal-pm-plant').value;
            const eq = document.getElementById('modal-pm-eq').value.trim();
            const desc = document.getElementById('modal-pm-desc').value.trim();
            const time = document.getElementById('modal-pm-time').value.trim();
            const assigned = document.getElementById('modal-pm-assigned').value;

            if (!eq || !desc) {
                alert('Please select equipment and enter PM activity description.');
                return;
            }

            try {
                await fetch('/api/pm/log', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        department: plant,
                        equipment_id: eq,
                        activity_description: desc,
                        scheduled_time: time || 'Tomorrow 10 AM',
                        technician: assigned !== 'Unassigned' ? assigned : (currentUsername || 'Tech')
                    })
                });
                if (pmModal) pmModal.classList.remove('active');
                refreshAll();
            } catch (e) { console.error(e); }
        });
    }

    // Schedule Welding Modal
    const wdModal = document.getElementById('modal-log-welding');
    if (document.getElementById('btn-schedule-welding')) {
        document.getElementById('btn-schedule-welding').addEventListener('click', () => {
            updateEquipmentOptions('modal-wd-plant', 'modal-wd-eq');
            document.getElementById('modal-wd-details').value = '';
            if (wdModal) wdModal.classList.add('active');
        });
    }

    if (document.getElementById('btn-close-wd-modal')) {
        document.getElementById('btn-close-wd-modal').addEventListener('click', () => {
            if (wdModal) wdModal.classList.remove('active');
        });
    }

    if (document.getElementById('btn-confirm-log-wd')) {
        document.getElementById('btn-confirm-log-wd').addEventListener('click', async () => {
            const plant = document.getElementById('modal-wd-plant').value;
            const eq = document.getElementById('modal-wd-eq').value.trim();
            const details = document.getElementById('modal-wd-details').value.trim();
            const time = document.getElementById('modal-wd-time').value.trim();
            const assigned = document.getElementById('modal-wd-assigned').value;

            if (!eq || !details) {
                alert('Please select equipment and enter welding work details.');
                return;
            }

            try {
                await fetch('/api/welding/log', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        department: plant,
                        equipment_id: eq,
                        welding_details: details,
                        scheduled_time: time || 'Today 3 PM',
                        technician: assigned !== 'Unassigned' ? assigned : (currentUsername || 'Welder')
                    })
                });
                if (wdModal) wdModal.classList.remove('active');
                refreshAll();
            } catch (e) { console.error(e); }
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
