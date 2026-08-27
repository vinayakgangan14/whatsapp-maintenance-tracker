# WhatsApp Maintenance & Breakdown Tracking Agent (100% FREE)

An automated 24/7 **WhatsApp Tracking Agent** built to log equipment breakdowns, preventive maintenance tasks, and calculate Mean Time To Repair (MTTR) across multiple departments.

Features **100% FREE WhatsApp QR Code Connect** (No Meta Developer account, no Twilio, no OTPs, and no credit card required!).

---

## 📱 How to Connect WhatsApp (100% FREE - 30 Seconds)

1. Open your live Web Dashboard (`https://whatsapp-maintenance-tracker.onrender.com`).
2. Click the **📱 WhatsApp QR Connect (Free)** tab in the menu.
3. Click **Generate / Reset QR Code**.
4. Open **WhatsApp** on your phone (any personal or business number).
5. Tap **Settings** (or ⋮ 3 dots) -> **Linked Devices** -> **Link a Device**.
6. Scan the QR code on your dashboard screen!

Your WhatsApp number is now linked 24/7 in the cloud for **$0.00 FREE forever**!

---

## 💬 WhatsApp Command Reference

Staff from any department can send messages to the linked WhatsApp number:

| Activity | What Staff Sends to WhatsApp | Agent Action & Response |
| :--- | :--- | :--- |
| **Report Breakdown** | `BREAKDOWN [Production] Press #3 - Hydraulic oil leak` | Logs Ticket `BD-202608-001`, records start timestamp, notifies team. |
| **Resolve & Log Repair** | `FIX Press #3 - Replaced oil seal and tested ok` | Calculates downtime (e.g. `45 mins`), updates status to `RESOLVED`, syncs to Sheets. |
| **Preventive Maintenance** | `MAINT [Utilities] Air Compressor #4 - Monthly filter changed` | Logs PM Ticket `PM-202608-001`. |
| **Check Active Tickets** | `STATUS` | Replies with list of open equipment breakdowns. |
| **View MTTR & Summary** | `SUMMARY` | Replies with total downtime hours, MTTR, and incident counts per department. |

---

## 📗 Google Sheets Setup

1. Share your master Google Sheet with your Service Account email as **Editor**.
2. Go to **Sheets & Excel Sync** tab in your Web Dashboard:
   - Paste your **Google Spreadsheet ID**.
   - Upload `service_account.json`.
   - Click **Save Google Sheet Configuration**.
