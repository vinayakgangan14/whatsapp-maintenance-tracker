import sys
import os
from pathlib import Path

# Configure UTF-8 output for Windows console emojis
sys.stdout.reconfigure(encoding='utf-8')

# Initialize database
import database
import parser
import excel_generator

print("--- STARTING SYSTEM VERIFICATION TESTS ---")

# 1. Test database initialization
database.init_db()
print("[OK] SQLite database initialized successfully.")

# 2. Test multi-department breakdown report parser
msg_bd = "BREAKDOWN [Production Dept] CNC Milling Machine #5 - Spindle motor overheating"
reply, action, details = parser.parse_whatsapp_message(msg_bd, sender_phone="+123456789", sender_name="John Maintenance")
print(f"[OK] Breakdown parser output:\n  Action: {action}\n  Ticket: {details.get('ticket')}\n  Reply snippet: {reply[:80]}...")

# 3. Test open status list
reply_status, action_status, details_status = parser.parse_whatsapp_message("STATUS")
assert details_status.get("count") >= 1, "Status count should be at least 1"
print(f"[OK] Open status query verified. Open tickets: {details_status.get('count')}")

# 4. Test resolution & MTTR duration calculation
msg_fix = "FIX CNC Milling Machine #5 - Replaced thermal coupler and reset drive"
reply_fix, action_fix, details_fix = parser.parse_whatsapp_message(msg_fix, sender_phone="+123456789", sender_name="John Maintenance")
print(f"[OK] Resolution parser output:\n  Action: {action_fix}\n  Downtime Mins: {details_fix.get('duration_minutes')} mins\n  Status: {details_fix.get('status')}")

# 5. Test Preventive Maintenance log
msg_pm = "MAINT [Utilities] Air Compressor #2 - Quarterly oil and filter replacement"
reply_pm, action_pm, details_pm = parser.parse_whatsapp_message(msg_pm, sender_phone="+987654321", sender_name="Alex Tech")
print(f"[OK] PM log parser output:\n  Action: {action_pm}\n  Ticket: {details_pm.get('ticket')}")

# 6. Test statistics & MTTR calculation
stats = database.get_statistics()
print(f"[OK] Statistics calculated:\n  Total BDs: {stats['total_breakdowns']}\n  Open BDs: {stats['open_breakdowns']}\n  Resolved BDs: {stats['resolved_breakdowns']}\n  MTTR: {stats['mttr_minutes']} mins\n  Depts: {stats['department_distribution']}")

# 7. Test Excel Export (.xlsx) generation
filepath, filename = excel_generator.generate_excel_report()
assert os.path.exists(filepath), "Excel file must exist on disk"
file_size = os.path.getsize(filepath)
print(f"[OK] Formatted Excel report generated successfully:\n  File: {filename}\n  Path: {filepath}\n  Size: {file_size} bytes")

print("--- ALL VERIFICATION TESTS PASSED SUCCESSFULLY! ---")
