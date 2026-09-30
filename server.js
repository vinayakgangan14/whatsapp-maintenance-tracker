const express = require('express');
const cors = require('cors');
const path = require('path');
const fs = require('fs');
const http = require('http');
const { spawn } = require('child_process');

const app = express();
const PORT = process.env.PORT || 3000;

// Python microservice port
const PY_PORT = process.env.PY_PORT || (process.env.PORT ? parseInt(process.env.PORT) - 1000 : 5555);

app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use('/static', express.static(path.join(__dirname, 'static')));

// ----------------------------------------------------------------
// PYTHON MICROSERVICE PROXY — All DB calls go through persistent service
// ----------------------------------------------------------------

/**
 * Make an HTTP request to the persistent Python database microservice.
 * Returns a Promise that resolves with parsed JSON.
 */
function pyRequest(method, urlPath, bodyObj = null) {
    return new Promise((resolve, reject) => {
        const options = {
            hostname: '127.0.0.1',
            port: PY_PORT,
            path: urlPath,
            method: method,
            headers: { 'Content-Type': 'application/json' },
            timeout: 15000
        };

        const req = http.request(options, (res) => {
            let data = '';
            res.on('data', (chunk) => { data += chunk; });
            res.on('end', () => {
                try {
                    resolve({ status: res.statusCode, body: JSON.parse(data) });
                } catch (e) {
                    resolve({ status: res.statusCode, body: { raw: data } });
                }
            });
        });

        req.on('error', (e) => {
            console.error(`[Py Proxy Error] ${method} ${urlPath}:`, e.message);
            reject(e);
        });

        req.on('timeout', () => {
            req.destroy();
            reject(new Error('Python service timeout'));
        });

        if (bodyObj) {
            req.write(JSON.stringify(bodyObj));
        }
        req.end();
    });
}

// Helper: proxy GET with query string passthrough
async function pyGet(apiPath, query = {}) {
    const qs = Object.entries(query)
        .filter(([, v]) => v !== undefined && v !== null && v !== '')
        .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
        .join('&');
    const fullPath = qs ? `${apiPath}?${qs}` : apiPath;
    const { body } = await pyRequest('GET', fullPath);
    return body;
}

// Helper: proxy POST with JSON body
async function pyPost(apiPath, data = {}) {
    const { status, body } = await pyRequest('POST', apiPath, data);
    return { status, body };
}

// Helper: proxy DELETE with query string
async function pyDelete(apiPath, query = {}) {
    const qs = Object.entries(query)
        .filter(([, v]) => v !== undefined && v !== null && v !== '')
        .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
        .join('&');
    const fullPath = qs ? `${apiPath}?${qs}` : apiPath;
    const { body } = await pyRequest('DELETE', fullPath);
    return body;
}

// ----------------------------------------------------------------
// GET ENDPOINTS — Proxy to Python microservice
// ----------------------------------------------------------------

app.get('/api/stats', async (req, res) => {
    try {
        const data = await pyGet('/api/stats', { company_id: req.query.company_id });
        res.json(data || {});
    } catch (e) { res.json({}); }
});

app.get('/api/breakdowns', async (req, res) => {
    try {
        const data = await pyGet('/api/breakdowns', { company_id: req.query.company_id });
        res.json(Array.isArray(data) ? data : []);
    } catch (e) { res.json([]); }
});

app.get('/api/maintenance', async (req, res) => {
    try {
        const data = await pyGet('/api/maintenance', { company_id: req.query.company_id });
        res.json(Array.isArray(data) ? data : []);
    } catch (e) { res.json([]); }
});

app.get('/api/welding', async (req, res) => {
    try {
        const data = await pyGet('/api/welding', { company_id: req.query.company_id });
        res.json(Array.isArray(data) ? data : []);
    } catch (e) { res.json([]); }
});

app.get('/api/settings', async (req, res) => {
    try {
        const data = await pyGet('/api/settings');
        res.json(data || {});
    } catch (e) { res.json({}); }
});

app.get('/api/config/departments', async (req, res) => {
    try {
        const data = await pyGet('/api/config/departments', { company_id: req.query.company_id });
        res.json(Array.isArray(data) ? data : []);
    } catch (e) { res.json([]); }
});

app.get('/api/config/equipment', async (req, res) => {
    try {
        const data = await pyGet('/api/config/equipment', {
            company_id: req.query.company_id,
            department: req.query.department
        });
        res.json(Array.isArray(data) ? data : []);
    } catch (e) { res.json([]); }
});

app.get('/api/users', async (req, res) => {
    try {
        const data = await pyGet('/api/users', { company_id: req.query.company_id });
        res.json(Array.isArray(data) ? data : []);
    } catch (e) { res.json([]); }
});

app.get('/api/companies/check-admin', async (req, res) => {
    try {
        const data = await pyGet('/api/companies/check-admin', { company_id: req.query.company_id });
        res.json(data || { has_admin: false, admin_count: 0 });
    } catch (e) { res.json({ has_admin: false, admin_count: 0 }); }
});

// ----------------------------------------------------------------
// POST ENDPOINTS — Proxy to Python microservice
// ----------------------------------------------------------------

app.post('/api/breakdowns/log', async (req, res) => {
    try {
        const { body } = await pyPost('/api/breakdowns/log', req.body);
        res.json(body.ticket ? body : { message: "Logged" });
    } catch (e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/pm/log', async (req, res) => {
    try {
        const { body } = await pyPost('/api/pm/log', req.body);
        res.json(body);
    } catch (e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/welding/log', async (req, res) => {
    try {
        const { body } = await pyPost('/api/welding/log', req.body);
        res.json(body);
    } catch (e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/ticket/approve', async (req, res) => {
    try {
        const { body } = await pyPost('/api/ticket/approve', req.body);
        res.json(body);
    } catch (e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/ticket/reject', async (req, res) => {
    try {
        const { body } = await pyPost('/api/ticket/reject', req.body);
        res.json(body);
    } catch (e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/ticket/assign', async (req, res) => {
    try {
        const { body } = await pyPost('/api/ticket/assign', req.body);
        res.json(body);
    } catch (e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/breakdowns/resolve', async (req, res) => {
    try {
        const { status, body } = await pyPost('/api/breakdowns/resolve', req.body);
        if (body.err) {
            return res.status(400).json({ detail: body.err });
        }
        res.json({ message: "Breakdown resolved successfully", record: body.updated });
    } catch (e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/config/departments', async (req, res) => {
    try {
        const { body } = await pyPost('/api/config/departments', req.body);
        res.json(body);
    } catch (e) { res.status(500).json({ error: e.message }); }
});

app.delete('/api/config/departments/:id', async (req, res) => {
    try {
        const data = await pyDelete(`/api/config/departments/${req.params.id}`, {
            company_id: req.query.company_id
        });
        res.json(data);
    } catch (e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/config/equipment', async (req, res) => {
    try {
        const { body } = await pyPost('/api/config/equipment', req.body);
        res.json(body);
    } catch (e) { res.status(500).json({ error: e.message }); }
});

app.delete('/api/config/equipment/:id', async (req, res) => {
    try {
        const data = await pyDelete(`/api/config/equipment/${req.params.id}`, {
            company_id: req.query.company_id
        });
        res.json(data);
    } catch (e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/config/seed-template', async (req, res) => {
    try {
        const { body } = await pyPost('/api/config/seed-template', req.body);
        res.json(body);
    } catch (e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/companies/register', async (req, res) => {
    try {
        const { body } = await pyPost('/api/companies/register', req.body);
        res.json(body);
    } catch (e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/auth/login', async (req, res) => {
    try {
        const { body } = await pyPost('/api/auth/login', req.body);
        res.json(body);
    } catch (e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/auth/register-admin', async (req, res) => {
    try {
        const { body } = await pyPost('/api/auth/register-admin', req.body);
        res.json(body);
    } catch (e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/users', async (req, res) => {
    try {
        const { body } = await pyPost('/api/users', req.body);
        res.json(body);
    } catch (e) { res.status(500).json({ error: e.message }); }
});

app.delete('/api/users/:id', async (req, res) => {
    try {
        const data = await pyDelete(`/api/users/${req.params.id}`, {
            company_id: req.query.company_id
        });
        res.json(data);
    } catch (e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/reset-database', async (req, res) => {
    try {
        const { body } = await pyPost('/api/reset-database', {});
        res.json(body);
    } catch (e) { res.status(500).json({ error: e.message }); }
});

app.all('/api/supabase/sync-all', async (req, res) => {
    try {
        const { body } = await pyPost('/api/supabase/sync-all', {});
        res.json(body);
    } catch (e) { res.status(500).json({ error: e.message }); }
});

app.all('/api/sync-all', async (req, res) => {
    try {
        // Google Sheets sync still uses spawn since it requires google_sheets module
        const pyExec = getPythonExecutable();
        const proc = spawn(pyExec, ['-c', `
import database, json, google_sheets
database.init_db()
ok, data = google_sheets.sync_all_records_batch()
if ok:
    print(json.dumps(data))
else:
    print(json.dumps({"error": data}))
        `]);
        let output = '';
        proc.stdout.on('data', (d) => { output += d.toString(); });
        proc.stderr.on('data', (d) => { console.error('PyErr:', d.toString()); });
        proc.on('close', () => {
            try { res.json(JSON.parse(output.trim())); }
            catch (e) { res.json({ error: output.trim() }); }
        });
    } catch (e) { res.status(500).json({ error: e.message }); }
});

app.get('/api/export/excel', (req, res) => {
    try {
        const pyExec = getPythonExecutable();
        const { execSync } = require('child_process');
        execSync(`${pyExec} -c "import excel_generator; excel_generator.generate_excel_report()"`);
        const exportsDir = path.join(__dirname, 'exports');
        const files = fs.readdirSync(exportsDir);
        if (files.length > 0) {
            const latestFile = files.sort().reverse()[0];
            return res.download(path.join(exportsDir, latestFile));
        }
        res.status(404).send('No report generated');
    } catch (e) {
        res.status(500).send('Error generating report');
    }
});

app.get('/api/debug-sheets', async (req, res) => {
    try {
        const pyExec = getPythonExecutable();
        const proc = spawn(pyExec, ['-c', `
import json, os, google_sheets, database
database.init_db()
result = {"status": "unknown", "email": "", "error": ""}
try:
    env_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if env_json:
        import json as j
        info = j.loads(env_json)
        result["email"] = info.get("client_email", "NOT FOUND")
    service = google_sheets.get_sheets_service()
    if not service:
        result["status"] = "NO_CREDENTIALS"
        result["error"] = "No credentials found"
    else:
        sid = os.getenv("GOOGLE_SPREADSHEET_ID") or database.get_setting("GOOGLE_SPREADSHEET_ID")
        resp = service.spreadsheets().get(spreadsheetId=sid).execute()
        result["status"] = "OK"
        result["sheet_title"] = resp.get("properties", {}).get("title", "")
        result["sheet_tabs"] = [s["properties"]["title"] for s in resp.get("sheets", [])]
except Exception as e:
    result["status"] = "ERROR"
    result["error"] = str(e)
print(json.dumps(result))
        `]);
        let output = '';
        proc.stdout.on('data', (d) => { output += d.toString(); });
        proc.stderr.on('data', (d) => { console.error('PyErr:', d.toString()); });
        proc.on('close', () => {
            try { res.json(JSON.parse(output.trim())); }
            catch (e) { res.json({ error: output.trim() }); }
        });
    } catch (e) { res.status(500).json({ error: e.message }); }
});

// ----------------------------------------------------------------
// STATIC FILES & STARTUP
// ----------------------------------------------------------------

function getPythonExecutable() {
    if (fs.existsSync(path.join(__dirname, '.venv', 'Scripts', 'python.exe'))) {
        return path.join(__dirname, '.venv', 'Scripts', 'python.exe');
    }
    if (process.platform === 'win32') return 'python';
    try {
        const { execSync } = require('child_process');
        execSync('python3 --version', { stdio: 'ignore' });
        return 'python3';
    } catch (e) {
        return 'python';
    }
}

app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'static', 'index.html'));
});

// Wait for Python microservice to be ready, then start Express
function waitForPythonService(retries = 30, delay = 1000) {
    return new Promise((resolve, reject) => {
        function attempt(n) {
            const req = http.request({
                hostname: '127.0.0.1',
                port: PY_PORT,
                path: '/health',
                method: 'GET',
                timeout: 2000
            }, (res) => {
                resolve(true);
            });
            req.on('error', () => {
                if (n <= 0) {
                    reject(new Error('Python microservice did not start'));
                } else {
                    setTimeout(() => attempt(n - 1), delay);
                }
            });
            req.on('timeout', () => {
                req.destroy();
                if (n <= 0) reject(new Error('Python microservice timeout'));
                else setTimeout(() => attempt(n - 1), delay);
            });
            req.end();
        }
        attempt(retries);
    });
}

async function startServer() {
    console.log(`⏳ Waiting for Python database service on port ${PY_PORT}...`);
    try {
        await waitForPythonService();
        console.log(`✅ Python database service ready on port ${PY_PORT}`);
    } catch (e) {
        console.error(`⚠️ Python service not detected: ${e.message}. Starting Express anyway...`);
    }

    app.listen(PORT, () => {
        console.log(`🚀 Maintenance Portal running on port ${PORT}`);
    });
}

startServer();
