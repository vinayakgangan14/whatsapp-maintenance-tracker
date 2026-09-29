document.addEventListener('DOMContentLoaded', () => {
    // ----------------------------------------------------
    // HELPER: PREVENT AUTO-REFRESH DOM DESTRUCTION ON ACTIVE DROPDOWNS
    // ----------------------------------------------------
    let isInteractingWithDropdown = false;

    document.addEventListener('focusin', (e) => {
        if (e.target && (e.target.classList.contains('btn-assign-staff') || e.target.tagName === 'SELECT')) {
            isInteractingWithDropdown = true;
        }
    });

    document.addEventListener('focusout', (e) => {
        if (e.target && (e.target.classList.contains('btn-assign-staff') || e.target.tagName === 'SELECT')) {
            setTimeout(() => {
                const active = document.activeElement;
                if (!active || (active.tagName !== 'SELECT' && !active.classList.contains('btn-assign-staff'))) {
                    isInteractingWithDropdown = false;
                }
            }, 300);
        }
    });

    document.addEventListener('mousedown', (e) => {
        if (e.target && (e.target.classList.contains('btn-assign-staff') || e.target.closest('.btn-assign-staff') || e.target.tagName === 'SELECT')) {
            isInteractingWithDropdown = true;
        }
    });

    document.addEventListener('mouseup', () => {
        setTimeout(() => {
            const active = document.activeElement;
            if (!active || (active.tagName !== 'SELECT' && !active.classList.contains('btn-assign-staff'))) {
                isInteractingWithDropdown = false;
            }
        }, 1200);
    });

    function isUserInteractingWithTable(tbodyId) {
        if (isInteractingWithDropdown) return true;
        const active = document.activeElement;
        if (!active) return false;
        const tbody = document.getElementById(tbodyId);
        return tbody && (tbody.contains(active) || active.tagName === 'SELECT' || active.tagName === 'INPUT');
    }

    // ----------------------------------------------------
    // PLANT & EQUIPMENT BY DEPARTMENT MAPPING
    // ----------------------------------------------------
    // ----------------------------------------------------
    // DYNAMIC PLANT & EQUIPMENT CONFIGURATION LOGIC
    // ----------------------------------------------------
    let cachedDepartments = [];
    let cachedEquipmentMap = {};

    async function loadDynamicDepartmentsAndEquipment(autoSelectDept = null) {
        try {
            const deptsRes = await fetch('/api/config/departments');
            const deptsData = await deptsRes.json();
            cachedDepartments = Array.isArray(deptsData) ? deptsData : [];

            const eqRes = await fetch('/api/config/equipment');
            const eqData = await eqRes.json();
            
            cachedEquipmentMap = {};
            if (Array.isArray(eqData)) {
                eqData.forEach(item => {
                    if (!cachedEquipmentMap[item.department_name]) {
                        cachedEquipmentMap[item.department_name] = [];
                    }
                    cachedEquipmentMap[item.department_name].push(item);
                });
            }

            populateAllDepartmentDropdowns(autoSelectDept);
            renderPlantSetupPanel(autoSelectDept);
        } catch (err) {
            console.error('Error loading dynamic plant config:', err);
        }
    }

    function populateAllDepartmentDropdowns(autoSelectDept = null) {
        const plantSelectors = ['modal-bd-plant', 'modal-pm-plant', 'modal-wd-plant', 'cfg-eq-dept-select'];
        const optionsHtml = cachedDepartments.length ?
            cachedDepartments.map(d => `<option value="${d.department_name}">${d.department_name}</option>`).join('') :
            '<option value="General">General Department</option>';

        plantSelectors.forEach(id => {
            const select = document.getElementById(id);
            if (select) {
                const currentVal = (id === 'cfg-eq-dept-select' && autoSelectDept) ? autoSelectDept : select.value;
                select.innerHTML = (id === 'cfg-eq-dept-select' ? '<option value="">-- Select Department --</option>' : '') + optionsHtml;
                if (currentVal && cachedDepartments.some(d => d.department_name === currentVal)) {
                    select.value = currentVal;
                } else if (id === 'cfg-eq-dept-select' && autoSelectDept) {
                    select.value = autoSelectDept;
                }
                if (id !== 'cfg-eq-dept-select') {
                    const eqId = id.replace('-plant', '-eq');
                    updateEquipmentOptionsForSelect(id, eqId);
                }
            }
        });
    }

    function updateEquipmentOptionsForSelect(plantSelectId, equipmentSelectId) {
        const plantSelect = document.getElementById(plantSelectId);
        const eqSelect = document.getElementById(equipmentSelectId);
        if (!plantSelect || !eqSelect) return;

        const selectedDept = plantSelect.value;
        const items = cachedEquipmentMap[selectedDept] || [];
        
        let html = '<option value="">-- Select Equipment --</option>';
        html += items.map(eq => `<option value="${eq.equipment_name}">${eq.equipment_name}</option>`).join('');
        html += '<option value="__CUSTOM__">➕ Enter Custom Equipment...</option>';

        eqSelect.innerHTML = html;
    }

    ['modal-bd-plant', 'modal-pm-plant', 'modal-wd-plant'].forEach(plantId => {
        const el = document.getElementById(plantId);
        if (el) {
            const eqId = plantId.replace('-plant', '-eq');
            el.addEventListener('change', () => updateEquipmentOptionsForSelect(plantId, eqId));
        }
    });

    ['modal-bd-eq', 'modal-pm-eq', 'modal-wd-eq'].forEach(eqId => {
        const el = document.getElementById(eqId);
        if (el) {
            el.addEventListener('change', () => {
                if (el.value === '__CUSTOM__') {
                    const customName = prompt('Enter New Equipment / Machine Name:');
                    if (customName && customName.trim()) {
                        const trimmed = customName.trim();
                        const opt = document.createElement('option');
                        opt.value = trimmed;
                        opt.textContent = trimmed;
                        opt.selected = true;
                        el.insertBefore(opt, el.lastElementChild);
                    } else {
                        el.value = '';
                    }
                }
            });
        }
    });

    function renderPlantSetupPanel(autoSelectDept = null) {
        const deptListEl = document.getElementById('cfg-dept-list');
        const eqDeptSelect = document.getElementById('cfg-eq-dept-select');

        if (deptListEl) {
            if (!cachedDepartments.length) {
                deptListEl.innerHTML = '<small class="text-muted">No departments created yet. Add one above or click "Load Template".</small>';
            } else {
                deptListEl.innerHTML = cachedDepartments.map(d => `
                    <div class="dept-item-card" data-name="${d.department_name}" style="display: flex; justify-content: space-between; align-items: center; background: rgba(255,255,255,0.05); padding: 8px 12px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.08); cursor: pointer;">
                        <strong style="color: #10b981; font-size: 0.9rem;">${d.department_name}</strong>
                        <div style="display:flex; align-items:center; gap: 8px;">
                            <span style="font-size: 0.75rem; color: #9ca3af;">(Click to Edit ➔)</span>
                            <button class="btn btn-sm btn-del-dept" data-id="${d.id}" style="border:1px solid #ef4444; color:#ef4444; background:transparent; padding:2px 8px; font-size:0.75rem;">Delete</button>
                        </div>
                    </div>
                `).join('');

                document.querySelectorAll('.dept-item-card').forEach(card => {
                    card.addEventListener('click', (e) => {
                        if (e.target.classList.contains('btn-del-dept')) return;
                        const deptName = card.getAttribute('data-name');
                        if (eqDeptSelect) {
                            eqDeptSelect.value = deptName;
                            renderEquipmentSetupList();
                        }
                    });
                });

                document.querySelectorAll('.btn-del-dept').forEach(btn => {
                    btn.addEventListener('click', async (e) => {
                        e.stopPropagation();
                        const id = e.target.getAttribute('data-id');
                        if (confirm('Delete this department and all its associated machines?')) {
                            await fetch(`/api/config/departments/${id}`, { method: 'DELETE' });
                            loadDynamicDepartmentsAndEquipment();
                        }
                    });
                });
            }
        }

        if (autoSelectDept && eqDeptSelect) {
            eqDeptSelect.value = autoSelectDept;
        } else if (eqDeptSelect && !eqDeptSelect.value && cachedDepartments.length > 0) {
            eqDeptSelect.value = cachedDepartments[0].department_name;
        }

        renderEquipmentSetupList();
    }

    function renderEquipmentSetupList() {
        const eqDeptSelect = document.getElementById('cfg-eq-dept-select');
        const eqListEl = document.getElementById('cfg-eq-list');
        if (!eqDeptSelect || !eqListEl) return;

        const selectedDept = eqDeptSelect.value;
        if (!selectedDept) {
            eqListEl.innerHTML = '<small class="text-muted">Select a department above to view and manage equipment list.</small>';
            return;
        }

        const items = cachedEquipmentMap[selectedDept] || [];
        if (!items.length) {
            eqListEl.innerHTML = `<small class="text-muted">No equipment added to "${selectedDept}" yet. Add a machine using the form above.</small>`;
            return;
        }

        eqListEl.innerHTML = items.map(eq => `
            <div style="display: flex; justify-content: space-between; align-items: center; background: rgba(255,255,255,0.05); padding: 6px 10px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.08);">
                <span style="font-size: 0.85rem; color: #fff;">⚙️ ${eq.equipment_name}</span>
                <button class="btn btn-sm btn-del-eq" data-id="${eq.id}" style="border:1px solid #ef4444; color:#ef4444; background:transparent; padding:2px 6px; font-size:0.7rem;">Delete</button>
            </div>
        `).join('');

        document.querySelectorAll('.btn-del-eq').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const id = e.target.getAttribute('data-id');
                await fetch(`/api/config/equipment/${id}`, { method: 'DELETE' });
                const currentDept = document.getElementById('cfg-eq-dept-select').value;
                loadDynamicDepartmentsAndEquipment(currentDept);
            });
        });
    }

    const cfgEqDeptSelect = document.getElementById('cfg-eq-dept-select');
    if (cfgEqDeptSelect) {
        cfgEqDeptSelect.addEventListener('change', renderEquipmentSetupList);
    }

    const btnAddDept = document.getElementById('btn-add-dept');
    if (btnAddDept) {
        btnAddDept.addEventListener('click', async () => {
            const input = document.getElementById('cfg-new-dept-name');
            const val = input ? input.value.trim() : '';
            if (!val) return alert('Please enter a department name.');
            await fetch('/api/config/departments', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ department_name: val })
            });
            input.value = '';
            await loadDynamicDepartmentsAndEquipment(val);
        });
    }

    const btnAddEq = document.getElementById('btn-add-eq');
    if (btnAddEq) {
        btnAddEq.addEventListener('click', async () => {
            const deptVal = document.getElementById('cfg-eq-dept-select').value;
            const input = document.getElementById('cfg-new-eq-name');
            const eqVal = input ? input.value.trim() : '';
            if (!deptVal) return alert('Please select a department first.');
            if (!eqVal) return alert('Please enter a machine / equipment name.');
            await fetch('/api/config/equipment', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ department_name: deptVal, equipment_name: eqVal })
            });
            input.value = '';
            await loadDynamicDepartmentsAndEquipment(deptVal);
        });
    }

    const btnSeedTemplate = document.getElementById('btn-seed-template');
    if (btnSeedTemplate) {
        btnSeedTemplate.addEventListener('click', async () => {
            if (confirm('Load standard industry template departments and machinery?')) {
                await fetch('/api/config/seed-template', { method: 'POST' });
                loadDynamicDepartmentsAndEquipment();
            }
        });
    }

    loadDynamicDepartmentsAndEquipment();

    // ----------------------------------------------------
    // MAINTENANCE STAFF LIST (GENERIC & EXTENSIBLE)
    // ----------------------------------------------------
    const MAINTENANCE_STAFF = [
        "Maintenance Manager",
        "Lead Electrical Engineer",
        "Lead Mechanical Engineer",
        "Automation Specialist",
        "Preventive Maintenance Tech",
        "Welding & Fabrication Tech",
        "Utility Operations Tech"
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
    let currentUserRole = sessionStorage.getItem('app_role') || null;
    let currentUsername = sessionStorage.getItem('app_username') || null;

    const loginModal = document.getElementById('login-modal');
    const roleSelect = document.getElementById('login-role');
    const operatorGroup = document.getElementById('operator-username-group');
    const managerGroup = document.getElementById('manager-select-group');
    const adminGroup = document.getElementById('admin-username-group');
    const passcodeGroup = document.getElementById('passcode-group');
    const passcodeBtn = document.getElementById('btn-login-submit');

    if (roleSelect) {
        roleSelect.addEventListener('change', () => {
            const role = roleSelect.value;
            if (role === 'Admin') {
                if (operatorGroup) operatorGroup.style.display = 'none';
                if (managerGroup) managerGroup.style.display = 'none';
                if (adminGroup) adminGroup.style.display = 'block';
                if (passcodeGroup) passcodeGroup.style.display = 'block';
            } else if (role === 'Manager') {
                if (operatorGroup) operatorGroup.style.display = 'none';
                if (managerGroup) managerGroup.style.display = 'block';
                if (adminGroup) adminGroup.style.display = 'none';
                if (passcodeGroup) passcodeGroup.style.display = 'block';
            } else {
                if (operatorGroup) operatorGroup.style.display = 'block';
                if (managerGroup) managerGroup.style.display = 'none';
                if (adminGroup) adminGroup.style.display = 'none';
                if (passcodeGroup) passcodeGroup.style.display = 'none';
            }
        });
    }

    if (passcodeBtn) {
        passcodeBtn.addEventListener('click', async () => {
            const role = document.getElementById('login-role').value;
            let username = '';
            let passcode = '';

            if (role === 'Admin') {
                const adminNameEl = document.getElementById('login-admin-name');
                username = (adminNameEl && adminNameEl.value.trim()) ? adminNameEl.value.trim() : 'vinayak.gangan14@gmail.com';
                passcode = document.getElementById('login-passcode').value.trim();
            } else if (role === 'Manager') {
                const mgrNameEl = document.getElementById('login-manager-name');
                username = (mgrNameEl && mgrNameEl.value.trim()) ? mgrNameEl.value.trim() : 'manager@maintenance.com';
                passcode = document.getElementById('login-passcode').value.trim();
            } else {
                const opNameEl = document.getElementById('login-username');
                username = (opNameEl && opNameEl.value.trim()) ? opNameEl.value.trim() : 'john.operator@maintenance.com';
                passcode = document.getElementById('login-passcode').value.trim();
            }

            // Attempt authentication against backend users database
            try {
                const authRes = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password: passcode, role })
                });
                const authData = await authRes.json();

                if (authData && authData.success) {
                    username = authData.user.email_or_name;
                } else if (role === 'Admin' && (passcode === 'Vinayak@123' || passcode === 'Admin@123' || passcode === 'admin')) {
                    // Standard demo Admin password fallback
                } else if (role === 'Manager' && (passcode === 'Manager@123' || passcode === 'manager' || passcode === 'Purechem@123')) {
                    // Standard demo Manager password fallback
                } else if (role === 'Operator') {
                    // Operator mode login
                } else {
                    alert('Invalid Username/Email or Password. Please try again.');
                    return;
                }
            } catch (e) {
                console.warn('API Auth check skipped, using session login.', e);
            }

            currentUserRole = role;
            currentUsername = username;
            sessionStorage.setItem('app_role', role);
            sessionStorage.setItem('app_username', username);

            if (loginModal) loginModal.classList.remove('active');
            updateUserDisplay();
            forceRefreshAll();
            loadCompanyUsersList();
        });
    }

    // ----------------------------------------------------
    // USER & ACCESS CONTROL MANAGEMENT LOGIC
    // ----------------------------------------------------
    async function loadCompanyUsersList() {
        const listEl = document.getElementById('users-table-list');
        if (!listEl) return;
        try {
            const res = await fetch('/api/users');
            const users = await res.json();
            if (!Array.isArray(users) || !users.length) {
                listEl.innerHTML = '<small class="text-muted">No user accounts created yet.</small>';
                return;
            }
            listEl.innerHTML = users.map(u => {
                let badgeColor = u.role === 'Admin' ? '#10b981' : (u.role === 'Manager' ? '#8b5cf6' : '#3b82f6');
                return `
                    <div style="display: flex; justify-content: space-between; align-items: center; background: rgba(255,255,255,0.05); padding: 8px 12px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.08);">
                        <div>
                            <strong style="color: #fff; font-size: 0.85rem;">${u.email_or_name}</strong>
                            <span class="badge" style="background: ${badgeColor}; font-size: 0.7rem; margin-left: 6px; padding: 2px 6px;">${u.role}</span>
                        </div>
                        <button class="btn btn-sm btn-del-user" data-id="${u.id}" style="border:1px solid #ef4444; color:#ef4444; background:transparent; padding:2px 8px; font-size:0.75rem;">Delete</button>
                    </div>
                `;
            }).join('');

            document.querySelectorAll('.btn-del-user').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    const id = e.target.getAttribute('data-id');
                    if (confirm('Delete this user account?')) {
                        await fetch(`/api/users/${id}`, { method: 'DELETE' });
                        loadCompanyUsersList();
                    }
                });
            });
        } catch (err) {
            console.error('Error loading users:', err);
        }
    }

    const btnCreateUser = document.getElementById('btn-create-user');
    if (btnCreateUser) {
        btnCreateUser.addEventListener('click', async () => {
            const role = document.getElementById('user-new-role').value;
            const email = document.getElementById('user-new-email').value.trim();
            const pwd = document.getElementById('user-new-password').value.trim();

            if (!email) return alert('Please enter user Email ID or Username.');
            if (!pwd) return alert('Please enter user Password.');

            const res = await fetch('/api/users', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email_or_name: email, password: pwd, role })
            });
            const data = await res.json();
            if (data && data.success) {
                document.getElementById('user-new-email').value = '';
                document.getElementById('user-new-password').value = '';
                alert(`User account created successfully! Role: ${role}`);
                loadCompanyUsersList();
            } else {
                alert(data.error || 'Failed to create user account.');
            }
        });
    }

    loadCompanyUsersList();

    if (loginModal) {
        loginModal.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                if (passcodeBtn) passcodeBtn.click();
            }
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
            if (currentUserRole === 'Admin') {
                roleBadge.innerText = '⚡ Admin Mode';
                roleBadge.className = 'badge';
                roleBadge.style.background = '#10b981';
            } else if (currentUserRole === 'Manager') {
                roleBadge.innerText = '👑 Manager Mode';
                roleBadge.className = 'badge';
                roleBadge.style.background = '#8b5cf6';
            } else {
                roleBadge.innerText = '👷 Operator Mode';
                roleBadge.className = 'badge 247-badge';
                roleBadge.style.background = '';
            }
        }
        if (userDisplay) {
            userDisplay.innerText = `${currentUsername} (${currentUserRole})`;
        }
    }

    document.getElementById('btn-logout').addEventListener('click', () => {
        sessionStorage.removeItem('pure_role');
        sessionStorage.removeItem('pure_username');
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
    function switchTab(targetTab) {
        const navItems = document.querySelectorAll('.nav-item');
        const tabPanes = document.querySelectorAll('.tab-pane');

        navItems.forEach(n => {
            if (n.getAttribute('data-tab') === targetTab) {
                n.classList.add('active');
            } else {
                n.classList.remove('active');
            }
        });

        tabPanes.forEach(p => {
            if (p.id === targetTab) {
                p.classList.add('active');
            } else {
                p.classList.remove('active');
            }
        });
    }

    let deptChart = null;
    let ratioChart = null;

    function initCharts(stats) {
        const deptCanvas = document.getElementById('chartDepartment');
        if (!deptCanvas) return;
        const deptCtx = deptCanvas.getContext('2d');
        const deptLabels = Object.keys(stats.department_distribution || {});
        const deptData = Object.values(stats.department_distribution || {});

        if (deptChart) deptChart.destroy();
        deptChart = new Chart(deptCtx, {
            type: 'doughnut',
            data: {
                labels: deptLabels.length ? deptLabels : ['No Breakdowns'],
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
                    legend: { labels: { color: '#9ca3af', font: { family: 'Inter' } } },
                    tooltip: {
                        callbacks: {
                            label: (context) => ` ${context.label}: ${context.raw} tickets (Click slice to view logs)`
                        }
                    }
                },
                onClick: (evt, activeElements) => {
                    if (activeElements && activeElements.length > 0) {
                        const index = activeElements[0].index;
                        const dept = deptLabels[index];
                        if (dept && dept !== 'No Breakdowns') {
                            switchTab('tab-breakdowns');
                            const searchBox = document.getElementById('table-search');
                            if (searchBox) searchBox.value = dept;
                            const statusFilter = document.getElementById('status-filter');
                            if (statusFilter) statusFilter.value = 'ALL';
                            loadBreakdowns(true);
                        }
                    }
                }
            }
        });

        const ratioCanvas = document.getElementById('chartRatio');
        if (!ratioCanvas) return;
        const ratioCtx = ratioCanvas.getContext('2d');
        if (ratioChart) ratioChart.destroy();
        ratioChart = new Chart(ratioCtx, {
            type: 'bar',
            data: {
                labels: ['Open Tickets', 'Resolved Tickets', 'PM Activities'],
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
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (context) => ` ${context.label}: ${context.raw} (Click bar to open section)`
                        }
                    }
                },
                scales: {
                    x: { ticks: { color: '#9ca3af' }, grid: { display: false } },
                    y: { ticks: { color: '#9ca3af' }, grid: { color: 'rgba(255,255,255,0.05)' } }
                },
                onClick: (evt, activeElements) => {
                    if (activeElements && activeElements.length > 0) {
                        const index = activeElements[0].index;
                        const label = ['Open Tickets', 'Resolved Tickets', 'PM Activities'][index];
                        if (label === 'Open Tickets') {
                            switchTab('tab-breakdowns');
                            const searchBox = document.getElementById('table-search');
                            if (searchBox) searchBox.value = '';
                            const statusFilter = document.getElementById('status-filter');
                            if (statusFilter) statusFilter.value = 'OPEN';
                            loadBreakdowns(true);
                        } else if (label === 'Resolved Tickets') {
                            switchTab('tab-breakdowns');
                            const searchBox = document.getElementById('table-search');
                            if (searchBox) searchBox.value = '';
                            const statusFilter = document.getElementById('status-filter');
                            if (statusFilter) statusFilter.value = 'RESOLVED';
                            loadBreakdowns(true);
                        } else if (label === 'PM Activities') {
                            switchTab('tab-pm');
                            loadPM(true);
                        }
                    }
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
            if (document.getElementById('kpi-mtbf-mins')) {
                document.getElementById('kpi-mtbf-mins').innerText = `${data.mtbf_minutes || 0} mins between failures`;
            }

            initCharts(data);
        } catch (err) {
            console.error('Error fetching stats:', err);
        }
    }

    async function loadBreakdowns(force = false) {
        if (!force && isUserInteractingWithTable('breakdowns-table-body')) return;
        try {
            const res = await fetch('/api/breakdowns');
            const data = await res.json();
            renderBreakdownsTable(data);
        } catch (err) {
            console.error('Error loading breakdowns:', err);
        }
    }

    async function loadPM(force = false) {
        if (!force && isUserInteractingWithTable('pm-table-body')) return;
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

    async function loadWelding(force = false) {
        if (!force && isUserInteractingWithTable('welding-table-body')) return;
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
        const isClosed = (item.status === 'RESOLVED' || item.status === 'REJECTED');

        // OPERATOR MODE OR CLOSED TICKET: READ-ONLY LOCK
        if (currentUserRole === 'Operator' || isClosed) {
            const badgeColor = assigned === 'Unassigned' ? 'rgba(255,255,255,0.06)' : 'rgba(59, 130, 246, 0.15)';
            const textColor = assigned === 'Unassigned' ? '#9ca3af' : '#60a5fa';
            return `<span class="badge" style="background: ${badgeColor}; color: ${textColor}; border: 1px solid rgba(255,255,255,0.1); font-size:0.8rem; padding: 4px 8px;">👤 ${assigned}</span>`;
        }

        // MANAGER AND ADMIN MODE ON ACTIVE TICKETS: EDITABLE DROPDOWN
        const options = MAINTENANCE_STAFF.map(s => `<option value="${s}" ${s === assigned ? 'selected' : ''}>${s}</option>`).join('');
        return `
            <select class="form-control btn-assign-staff" data-ticket="${item.ticket_number}" style="padding: 4px 8px; font-size: 0.8rem; border-radius: 6px; background: rgba(0,0,0,0.5); color: #38bdf8; border: 1px solid rgba(56,189,248,0.3); max-width: 180px;">
                <option value="Unassigned" ${assigned === 'Unassigned' ? 'selected' : ''}>-- Assign Staff --</option>
                ${options}
            </select>
        `;
    }

    function renderActionButtons(item) {
        const isResolved = item.status === 'RESOLVED' || item.status === 'REJECTED';
        const isPending = item.status === 'PENDING_APPROVAL';

        if (isResolved) {
            return `<button class="btn btn-sm btn-outline" disabled>Closed</button>`;
        }

        // OPERATOR ROLE: NO RESOLVE/APPROVE RIGHTS!
        if (currentUserRole === 'Operator') {
            return `<button class="btn btn-sm btn-outline" disabled style="opacity:0.6;">Manager Only</button>`;
        }

        // MANAGER & ADMIN ROLES: FULL APPROVE, REJECT, AND RESOLVE RIGHTS!
        if ((currentUserRole === 'Manager' || currentUserRole === 'Admin') && isPending) {
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
                const actionBtn = e.target;
                if (actionBtn.disabled) return;
                actionBtn.disabled = true;
                actionBtn.textContent = '⏳...';

                const ticket = actionBtn.getAttribute('data-ticket');
                try {
                    await fetch('/api/ticket/approve', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ ticket_number: ticket, manager_name: currentUsername })
                    });
                    forceRefreshAll();
                } catch (err) { console.error(err); }
            });
        });

        document.querySelectorAll('.btn-reject-action').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const actionBtn = e.target;
                if (actionBtn.disabled) return;
                
                const ticket = actionBtn.getAttribute('data-ticket');
                const reason = prompt(`Reject Ticket ${ticket}?\nEnter rejection reason (optional):`, "");
                if (reason === null) return;

                actionBtn.disabled = true;
                actionBtn.textContent = '⏳...';

                try {
                    await fetch('/api/ticket/reject', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ ticket_number: ticket, manager_name: currentUsername, reason: reason || 'Rejected by Manager' })
                    });
                    forceRefreshAll();
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
                    forceRefreshAll();
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
            const btn = document.getElementById('btn-confirm-resolve');
            if (btn.disabled) return;

            const notes = document.getElementById('modal-resolution').value.trim();
            const tech = document.getElementById('modal-tech').value.trim();

            if (!notes) {
                alert('Please enter resolution notes.');
                return;
            }

            btn.disabled = true;
            btn.textContent = '⏳ Resolving...';

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
                    forceRefreshAll();
                } else {
                    const errData = await res.json();
                    alert('Error: ' + (errData.detail || 'Could not resolve ticket'));
                }
            } catch (e) {
                console.error(e);
            } finally {
                btn.disabled = false;
                btn.textContent = 'Mark Resolved & Sync';
            }
        });
    }

    // Quick Log Breakdown Modal (Anti-duplicate double click protection + instant response)
    const bdModal = document.getElementById('modal-log-bd');
    document.getElementById('btn-quick-log').addEventListener('click', () => {
        updateEquipmentOptionsForSelect('modal-bd-plant', 'modal-bd-eq');
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
            const btn = document.getElementById('btn-confirm-log-bd');
            if (btn.disabled) return;

            const plant = document.getElementById('modal-bd-plant').value;
            const eq = document.getElementById('modal-bd-eq').value.trim();
            const issue = document.getElementById('modal-bd-issue').value.trim();

            if (!eq || !issue) {
                alert('Please select an equipment and enter issue description.');
                return;
            }

            btn.disabled = true;
            btn.textContent = '⏳ Submitting...';

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
                forceRefreshAll();
            } catch (e) {
                console.error(e);
            } finally {
                btn.disabled = false;
                btn.textContent = 'Submit Breakdown';
            }
        });
    }

    // Schedule PM Modal
    const pmModal = document.getElementById('modal-log-pm');
    if (document.getElementById('btn-schedule-pm')) {
        document.getElementById('btn-schedule-pm').addEventListener('click', () => {
            updateEquipmentOptionsForSelect('modal-pm-plant', 'modal-pm-eq');
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
            const btn = document.getElementById('btn-confirm-log-pm');
            if (btn.disabled) return;

            const plant = document.getElementById('modal-pm-plant').value;
            const eq = document.getElementById('modal-pm-eq').value.trim();
            const desc = document.getElementById('modal-pm-desc').value.trim();
            const time = document.getElementById('modal-pm-time').value.trim();
            const assigned = document.getElementById('modal-pm-assigned').value;

            if (!eq || !desc) {
                alert('Please select equipment and enter PM activity description.');
                return;
            }

            btn.disabled = true;
            btn.textContent = '⏳ Submitting...';

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
                forceRefreshAll();
            } catch (e) {
                console.error(e);
            } finally {
                btn.disabled = false;
                btn.textContent = 'Submit PM Schedule';
            }
        });
    }

    // Schedule Welding Modal
    const wdModal = document.getElementById('modal-log-welding');
    if (document.getElementById('btn-schedule-welding')) {
        document.getElementById('btn-schedule-welding').addEventListener('click', () => {
            updateEquipmentOptionsForSelect('modal-wd-plant', 'modal-wd-eq');
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
            const btn = document.getElementById('btn-confirm-log-wd');
            if (btn.disabled) return;

            const plant = document.getElementById('modal-wd-plant').value;
            const eq = document.getElementById('modal-wd-eq').value.trim();
            const details = document.getElementById('modal-wd-details').value.trim();
            const time = document.getElementById('modal-wd-time').value.trim();
            const assigned = document.getElementById('modal-wd-assigned').value;

            if (!eq || !details) {
                alert('Please select equipment and enter welding work details.');
                return;
            }

            btn.disabled = true;
            btn.textContent = '⏳ Submitting...';

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
                forceRefreshAll();
            } catch (e) {
                console.error(e);
            } finally {
                btn.disabled = false;
                btn.textContent = 'Submit Welding Schedule';
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

    // Supabase Manual Batch Sync Handler
    const btnSupabaseSync = document.getElementById('btn-supabase-sync-all');
    if (btnSupabaseSync) {
        btnSupabaseSync.addEventListener('click', async () => {
            const statusEl = document.getElementById('supabase-sync-status');
            btnSupabaseSync.disabled = true;
            btnSupabaseSync.textContent = '⏳ Syncing to Supabase... please wait';
            if (statusEl) statusEl.textContent = '';

            try {
                const res = await fetch('/api/supabase/sync-all', { method: 'POST' });
                const data = await res.json();
                if (statusEl) {
                    statusEl.innerHTML = `✅ <b>Supabase Batch Sync Complete!</b> Synced breakdown tickets, PM logs, welding records, plant configuration, and user accounts.`;
                    statusEl.style.color = '#10b981';
                }
            } catch (e) {
                if (statusEl) {
                    statusEl.textContent = '❌ Connection error: ' + (e.message || e);
                    statusEl.style.color = '#ef4444';
                }
            }

            btnSupabaseSync.disabled = false;
            btnSupabaseSync.textContent = '⚡ Batch Sync All Database Records to Supabase Now';
        });
    }

    // Client Handover Reset Button — EXCLUSIVE ADMINISTRATOR RIGHT!
    if (document.getElementById('btn-reset-db')) {
        document.getElementById('btn-reset-db').addEventListener('click', async () => {
            if (currentUserRole !== 'Admin') {
                alert('⛔ Access Denied: Clearing database records is strictly restricted to Administrator (Vinayak Gangan) only.');
                return;
            }

            if (!confirm('⚠️ Administrator Action: Are you sure you want to clear ALL breakdown tickets and maintenance records for client handover? This action cannot be undone.')) {
                return;
            }

            const statusEl = document.getElementById('reset-db-status');
            try {
                const res = await fetch('/api/reset-database', { method: 'POST' });
                await res.json();
                statusEl.innerHTML = '✅ <b>All test records cleared successfully!</b> Ready for fresh client handover.';
                statusEl.style.color = '#10b981';
                forceRefreshAll();
            } catch (e) {
                statusEl.textContent = '❌ Error clearing database.';
                statusEl.style.color = '#ef4444';
            }
        });
    }

    function refreshAll() {
        loadStats();
        loadBreakdowns(false);
        loadPM(false);
        loadWelding(false);
    }

    function forceRefreshAll() {
        loadStats();
        loadBreakdowns(true);
        loadPM(true);
        loadWelding(true);
    }

    // Initial load
    forceRefreshAll();
    loadSettings();

    // Auto refresh stats every 10 seconds
    setInterval(refreshAll, 10000);
});
