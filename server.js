const express = require('express');
const cors = require('cors');
const path = require('path');
const fs = require('fs');
const { execSync, spawn } = require('child_process');
const baileysService = require('./baileysService');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use('/static', express.static(path.join(__dirname, 'static')));

function getPythonExecutable() {
    if (fs.existsSync(path.join(__dirname, '.venv', 'Scripts', 'python.exe'))) {
        return path.join(__dirname, '.venv', 'Scripts', 'python.exe');
    }
    if (process.platform === 'win32') return 'python';
    try {
        execSync('python3 --version', { stdio: 'ignore' });
        return 'python3';
    } catch (e) {
        return 'python';
    }
}

// Execute python helper script
function runPythonCode(pythonCode) {
    return new Promise((resolve) => {
        try {
            const pyExec = getPythonExecutable();
            const proc = spawn(pyExec, ['-c', pythonCode]);
            let output = '';

            proc.stdout.on('data', (data) => { output += data.toString(); });
            proc.stderr.on('data', (data) => { console.error('PyErr:', data.toString()); });

            proc.on('close', () => {
                try {
                    resolve(JSON.parse(output.trim()));
                } catch (e) {
                    resolve({ raw: output.trim() });
                }
            });
        } catch (e) {
            resolve({ error: String(e) });
        }
    });
}

// ---------------------------------------------------
// BAILEYS QR CODE ENDPOINTS
// ---------------------------------------------------
app.get('/api/baileys/status', (req, res) => {
    res.json(baileysService.getBaileysStatus());
});

app.post('/api/baileys/start', (req, res) => {
    baileysService.startBaileysEngine(async (text, phone, name) => {
        const code = `
import parser, database, json
database.init_db()
reply, action, details = parser.parse_whatsapp_message(${JSON.stringify(text)}, ${JSON.stringify(phone)}, ${JSON.stringify(name)})
print(json.dumps({"reply": reply}))
        `;
        const resObj = await runPythonCode(code);
        return resObj.reply || "✅ Report received and logged.";
    });
    res.json({ message: "Baileys engine starting..." });
});

// Proxy stats, breakdowns, maintenance to Python Database engine
app.get('/api/stats', async (req, res) => {
    const data = await runPythonCode('import database, json; database.init_db(); print(json.dumps(database.get_statistics()))');
    res.json(data.raw ? {} : data);
});

app.get('/api/breakdowns', async (req, res) => {
    const data = await runPythonCode('import database, json; database.init_db(); print(json.dumps(database.get_all_breakdowns()))');
    res.json(Array.isArray(data) ? data : []);
});

app.get('/api/maintenance', async (req, res) => {
    const data = await runPythonCode('import database, json; database.init_db(); print(json.dumps(database.get_all_maintenance()))');
    res.json(Array.isArray(data) ? data : []);
});

// Debug: test Google Sheets connection and show service account email
app.get('/api/debug-sheets', async (req, res) => {
    const code = `
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
    `;
    const data = await runPythonCode(code);
    res.json(data.raw ? { error: data.raw } : data);
});

// One-time fast batch sync: push ALL records to Google Sheets (supports GET & POST)
app.all('/api/sync-all', async (req, res) => {
    const code = `
import database, json, google_sheets
database.init_db()
ok, data = google_sheets.sync_all_records_batch()
if ok:
    print(json.dumps(data))
else:
    print(json.dumps({"error": data}))
    `;
    const data = await runPythonCode(code);
    res.json(data.raw ? { error: data.raw } : data);
});

app.post('/api/breakdowns/log', async (req, res) => {
    const { department, equipment_id, issue_description, sender_name } = req.body;
    const code = `
import database, json, google_sheets
database.init_db()
ticket, bd_id = database.log_breakdown(
    department=${JSON.stringify(department || 'General')},
    equipment_id=${JSON.stringify(equipment_id)},
    issue_description=${JSON.stringify(issue_description)},
    sender_name=${JSON.stringify(sender_name || 'Web Admin')}
)
open_bds = database.get_open_breakdowns()
matching = [b for b in open_bds if b['ticket_number'] == ticket]
if matching:
    google_sheets.sync_breakdown_to_sheet(matching[0])
print(json.dumps({"ticket": ticket, "id": bd_id}))
    `;
    const data = await runPythonCode(code);
    res.json(data.ticket ? data : { message: "Logged" });
});

app.post('/api/breakdowns/resolve', async (req, res) => {
    const { ticket_number, equipment_id, resolution_notes, technician } = req.body;

    // Build Python-safe values (None vs quoted string)
    const pyTicket   = ticket_number   ? JSON.stringify(ticket_number)   : 'None';
    const pyEquip    = equipment_id    ? JSON.stringify(equipment_id)    : 'None';
    const pyNotes    = JSON.stringify(resolution_notes || 'Fixed manually via dashboard');
    const pyTech     = JSON.stringify(technician || 'Technician');

    const code = `
import database, json, google_sheets
database.init_db()
updated, err = database.resolve_breakdown(
    ticket_number=${pyTicket},
    equipment_id=${pyEquip},
    resolution_notes=${pyNotes},
    technician=${pyTech}
)
if updated:
    try:
        google_sheets.sync_breakdown_to_sheet(updated)
    except Exception as gs_err:
        pass
print(json.dumps({"updated": updated, "err": err}))
    `;
    const data = await runPythonCode(code);
    if (data.err) {
        return res.status(400).json({ detail: data.err });
    }
    res.json({ message: "Breakdown resolved successfully", record: data.updated });
});

app.post('/api/simulator/send', async (req, res) => {
    const { message, sender_name, department } = req.body;
    let fullMsg = message || '';
    if (department && !fullMsg.includes('[') && !fullMsg.toLowerCase().includes('dept')) {
        fullMsg = `[${department}] ${fullMsg}`;
    }
    const code = `
import parser, database, json
database.init_db()
reply, action, details = parser.parse_whatsapp_message(${JSON.stringify(fullMsg)}, "+1234567890", ${JSON.stringify(sender_name || 'Simulator User')})
print(json.dumps({"reply": reply, "action_type": action, "stats": database.get_statistics()}))
    `;
    const data = await runPythonCode(code);
    res.json(data.reply ? data : { reply: "✅ Logged in system." });
});

app.get('/api/export/excel', (req, res) => {
    try {
        const pyExec = getPythonExecutable();
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

app.get('/api/settings', async (req, res) => {
    const data = await runPythonCode(`
import database, json, os, config
database.init_db()
has_creds = os.path.exists(config.CREDENTIALS_FILE) or bool(os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"))
has_spreadsheet = bool(
    os.getenv("GOOGLE_SPREADSHEET_ID")
    or database.get_setting("GOOGLE_SPREADSHEET_ID")
    or config.DEFAULT_CONFIG.get("GOOGLE_SPREADSHEET_ID")
)
print(json.dumps({
    "spreadsheet_id": os.getenv("GOOGLE_SPREADSHEET_ID") or database.get_setting("GOOGLE_SPREADSHEET_ID") or config.DEFAULT_CONFIG["GOOGLE_SPREADSHEET_ID"],
    "sheet_name": os.getenv("GOOGLE_SHEET_NAME") or database.get_setting("GOOGLE_SHEET_NAME") or config.DEFAULT_CONFIG["GOOGLE_SHEET_NAME"],
    "has_google_credentials": has_creds,
    "has_spreadsheet_configured": has_spreadsheet
}))
    `);
    res.json(data.raw ? {} : data);
});

app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'static', 'index.html'));
});

// Auto-start Baileys engine on startup
baileysService.startBaileysEngine(async (text, phone, name) => {
    const code = `
import parser, database, json
database.init_db()
reply, action, details = parser.parse_whatsapp_message(${JSON.stringify(text)}, ${JSON.stringify(phone)}, ${JSON.stringify(name)})
print(json.dumps({"reply": reply}))
    `;
    const resObj = await runPythonCode(code);
    return resObj.reply || "✅ Report received and logged.";
});

app.listen(PORT, async () => {
    console.log(`🚀 Server running on port ${PORT}`);
    // Restore database from Google Sheets on startup if empty
    try {
        await runPythonCode('import google_sheets; google_sheets.restore_database_from_sheets()');
        console.log('[Pure Bot] Startup database restore completed.');
    } catch (e) {
        console.error('[Pure Bot] Database restore skipped:', e);
    }
});
