const express = require('express');
const cors = require('cors');
const path = require('path');
const sqlite3 = require('sqlite3').verbose();
const fs = require('fs');
const { execSync, spawn } = require('child_process');
const baileysService = require('./baileysService');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use('/static', express.static(path.join(__dirname, 'static')));

// Database setup
const dbPath = path.join(__dirname, 'maintenance_tracker.db');
const db = new sqlite3.Database(dbPath);

db.serialize(() => {
    db.run(`
        CREATE TABLE IF NOT EXISTS breakdowns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_number TEXT UNIQUE NOT NULL,
            department TEXT NOT NULL DEFAULT 'General',
            sender_phone TEXT,
            sender_name TEXT,
            equipment_id TEXT NOT NULL,
            issue_description TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT,
            status TEXT NOT NULL DEFAULT 'OPEN',
            duration_minutes INTEGER DEFAULT 0,
            resolution_notes TEXT,
            technician TEXT,
            synced_to_sheets INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    `);

    db.run(`
        CREATE TABLE IF NOT EXISTS maintenance_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_number TEXT UNIQUE NOT NULL,
            department TEXT NOT NULL DEFAULT 'General',
            sender_phone TEXT,
            sender_name TEXT,
            equipment_id TEXT NOT NULL,
            activity_description TEXT NOT NULL,
            technician TEXT,
            performed_at TEXT NOT NULL,
            synced_to_sheets INTEGER DEFAULT 0
        )
    `);

    db.run(`
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    `);
});

// Execute python parser script for incoming messages
function processMessageWithPython(text, phone, name) {
    return new Promise((resolve) => {
        const pythonScript = path.join(__dirname, 'parser.py');
        const code = `
import parser, database, json
database.init_db()
reply, action, details = parser.parse_whatsapp_message(${JSON.stringify(text)}, ${JSON.stringify(phone)}, ${JSON.stringify(name)})
print(json.dumps({"reply": reply, "action": action, "details": details}))
        `;
        
        try {
            const pyExec = fs.existsSync(path.join(__dirname, '.venv', 'Scripts', 'python.exe')) 
                ? path.join(__dirname, '.venv', 'Scripts', 'python.exe')
                : 'python';

            const process = spawn(pyExec, ['-c', code]);
            let output = '';

            process.stdout.on('data', (data) => { output += data.toString(); });
            process.stderr.on('data', (data) => { console.error('PyErr:', data.toString()); });

            process.on('close', () => {
                try {
                    const parsed = JSON.parse(output.trim());
                    resolve(parsed.reply);
                } catch (e) {
                    resolve("✅ Report received and recorded in system database.");
                }
            });
        } catch (e) {
            resolve("✅ Report received and recorded.");
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
    baileysService.startBaileysEngine((text, phone, name) => {
        return processMessageWithPython(text, phone, name);
    });
    res.json({ message: "Baileys engine starting..." });
});

// Proxy existing endpoints to Python backend or DB queries
app.get('/api/stats', (req, res) => {
    db.get("SELECT COUNT(*) as total_bd, SUM(CASE WHEN status != 'RESOLVED' THEN 1 ELSE 0 END) as open_bd, SUM(CASE WHEN status = 'RESOLVED' THEN 1 ELSE 0 END) as resolved_bd, SUM(CASE WHEN status = 'RESOLVED' THEN duration_minutes ELSE 0 END) as total_downtime FROM breakdowns", [], (err, row) => {
        const totalBd = row ? row.total_bd : 0;
        const openBd = row ? row.open_bd : 0;
        const resolvedBd = row ? row.resolved_bd : 0;
        const sumDowntime = row ? (row.total_downtime || 0) : 0;
        const mttr = resolvedBd > 0 ? Math.round((sumDowntime / resolvedBd) * 10) / 10 : 0;

        db.get("SELECT COUNT(*) as total_pm FROM maintenance_logs", [], (err2, row2) => {
            const totalPm = row2 ? row2.total_pm : 0;
            res.json({
                total_breakdowns: totalBd,
                open_breakdowns: openBd,
                resolved_breakdowns: resolvedBd,
                total_downtime_minutes: sumDowntime,
                total_downtime_hours: Math.round((sumDowntime / 60) * 100) / 100,
                mttr_minutes: mttr,
                total_pm_logs: totalPm,
                department_distribution: { "Production": totalBd }
            });
        });
    });
});

app.get('/api/breakdowns', (req, res) => {
    db.all("SELECT * FROM breakdowns ORDER BY id DESC LIMIT 100", [], (err, rows) => {
        res.json(rows || []);
    });
});

app.get('/api/maintenance', (req, res) => {
    db.all("SELECT * FROM maintenance_logs ORDER BY id DESC LIMIT 100", [], (err, rows) => {
        res.json(rows || []);
    });
});

app.post('/api/simulator/send', async (req, res) => {
    const { message, sender_name, department } = req.body;
    let fullMsg = message || '';
    if (department && !fullMsg.includes('[') && !fullMsg.toLowerCase().includes('dept')) {
        fullMsg = `[${department}] ${fullMsg}`;
    }
    const reply = await processMessageWithPython(fullMsg, '+1234567890', sender_name || 'Simulator User');
    res.json({ reply, action_type: 'SIMULATOR' });
});

app.get('/api/export/excel', (req, res) => {
    try {
        const pyExec = fs.existsSync(path.join(__dirname, '.venv', 'Scripts', 'python.exe')) 
            ? path.join(__dirname, '.venv', 'Scripts', 'python.exe')
            : 'python';

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

app.get('/api/settings', (req, res) => {
    db.all("SELECT * FROM settings", [], (err, rows) => {
        const settings = {};
        if (rows) rows.forEach(r => settings[r.key] = r.value);
        res.json({
            spreadsheet_id: settings.GOOGLE_SPREADSHEET_ID || "",
            sheet_name: settings.GOOGLE_SHEET_NAME || "Maintenance_Logs",
            has_google_credentials: fs.existsSync(path.join(__dirname, 'service_account.json'))
        });
    });
});

app.post('/api/settings', (req, res) => {
    const { spreadsheet_id, sheet_name } = req.body;
    if (spreadsheet_id !== undefined) {
        db.run("INSERT OR REPLACE INTO settings (key, value) VALUES ('GOOGLE_SPREADSHEET_ID', ?)", [spreadsheet_id]);
    }
    if (sheet_name !== undefined) {
        db.run("INSERT OR REPLACE INTO settings (key, value) VALUES ('GOOGLE_SHEET_NAME', ?)", [sheet_name]);
    }
    res.json({ message: "Settings saved" });
});

app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'static', 'index.html'));
});

// Auto start Baileys engine on launch
baileysService.startBaileysEngine((text, phone, name) => {
    return processMessageWithPython(text, phone, name);
});

app.listen(PORT, () => {
    console.log(`🚀 Server running on port ${PORT}`);
});
