# WhatsApp Maintenance & Breakdown Tracking Agent

An automated, 24/7 intelligent **WhatsApp Tracking Agent** built to log equipment breakdowns, preventive maintenance tasks, and calculate Mean Time To Repair (MTTR) across multiple departments. Connected live to **Google Sheets** and generates formatted **Excel (.xlsx)** reports.

---

## 🌟 Key Features

- **24/7 Offline Ready**: Can be deployed to free cloud hosts (Render / Railway / Fly.io) so it listens & records WhatsApp messages even when your PC is offline.
- **Multi-Department Support**: Staff from any department (Production, HVAC, Utilities, Logistics, Facilities) can post messages to the central WhatsApp number.
- **Auto Duration & MTTR Calculation**: Automatically records breakdown start time when reported and calculates total downtime ($T_{end} - T_{start}$) when marked fixed.
- **Google Sheets Live Sync**: Every breakdown and resolution event streams to a cloud Google Spreadsheet in real-time.
- **Styled Excel (.xlsx) Reports**: Export formatted workbooks with color-coded status badges, KPI summaries, and PM logs.
- **Modern Web Admin Dashboard**: Live MTTR charts, active breakdown list, Excel downloader, and built-in interactive WhatsApp simulator.

---

## 📱 WhatsApp Command Examples

| Activity | What Staff Sends to WhatsApp | Agent Action & Response |
| :--- | :--- | :--- |
| **Report Breakdown** | `BREAKDOWN [Production] Press #3 - Hydraulic oil leak` | Logs Ticket `BD-202608-001`, records start timestamp, notifies team. |
| **Resolve & Log Repair** | `FIX Press #3 - Replaced oil seal and tested ok` | Calculates downtime (e.g. `45 mins`), updates status to `RESOLVED`, syncs to Sheets. |
| **Preventive Maintenance** | `MAINT [Utilities] Air Compressor #4 - Monthly filter changed` | Logs PM Ticket `PM-202608-001`. |
| **Check Active Tickets** | `STATUS` | Replies with list of open equipment breakdowns. |
| **View MTTR & Summary** | `SUMMARY` | Replies with total downtime hours, MTTR, and incident counts per department. |

---

## 🚀 How to Run Locally

1. Open PowerShell in the project directory:
   `C:\Users\HP\.gemini\antigravity\scratch\whatsapp-maintenance-tracker`

2. Run the application server:
   ```powershell
   .\.venv\Scripts\python.exe main.py
   ```

3. Open your web browser to:
   `http://localhost:3000`

---

## ☁️ 24/7 Offline Deployment Guide (Keeping it running when PC is OFF)

To ensure the WhatsApp agent works when your PC is turned off:

### Option 1: Render.com (Free Tier)
1. Push this repository to GitHub.
2. Log into [Render.com](https://render.com) and create a **Web Service**.
3. Set build command to:
   `pip install fastapi "uvicorn[standard]" openpyxl google-api-python-client google-auth-httplib2 google-auth-oauthlib requests pydantic jinja2 python-multipart`
4. Set start command to:
   `python main.py`
5. Render provides a free public URL (e.g. `https://your-maint-agent.onrender.com`).
6. Set your Meta WhatsApp Webhook URL to: `https://your-maint-agent.onrender.com/webhook`.

---

## 📗 Google Sheets Integration Setup

1. Create a Google Cloud Project & enable **Google Sheets API**.
2. Create a **Service Account** and download its `service_account.json` key file.
3. Open your Google Sheet, click **Share**, and paste the Service Account email address with **Editor** permissions.
4. Upload `service_account.json` via the agent's Web Dashboard under **Sheets & Excel Sync**.
5. Paste your Google Spreadsheet ID (from the sheet URL) into the dashboard settings.
