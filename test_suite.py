import sys
import os
from pathlib import Path

# Configure UTF-8 output for Windows console
sys.stdout.reconfigure(encoding='utf-8')

import database
import parser
import excel_generator

print("--- STARTING SYSTEM VERIFICATION TESTS FOR PURE BOT ---")

# 1. Test database initialization
database.init_db()
print("[OK] SQLite database initialized successfully.")

# 2. Test Menu Reply
reply_menu, action_menu, _ = parser.parse_whatsapp_message("MENU")
print(f"[OK] Menu trigger verified:\n  Action: {action_menu}\n  Reply snippet: {reply_menu[:60]}...")

# 3. Test Option 1 (Report Breakdown)
reply_bd1, action_bd1, _ = parser.parse_whatsapp_message("1", sender_phone="+12345")
assert action_bd1 == "PROMPT_BD"
print("[OK] Option 1 Breakdown Prompt verified.")

reply_bd2, action_bd2, details_bd = parser.parse_whatsapp_message("Press #4 | Production Line B | Valve Leak", sender_phone="+12345", sender_name="John Tech")
assert action_bd2 == "BD_SUCCESS"
ticket_bd = details_bd.get('ticket')
print(f"[OK] Option 1 Breakdown Logged: {ticket_bd} ({details_bd.get('equipment')})")

# 4. Test Option 2 (Preventive Maintenance)
reply_pm, action_pm, details_pm = parser.parse_whatsapp_message("2 Compressor #3 | Line A | Quarterly Service | Tomorrow 10 AM", sender_name="Alex Tech")
assert action_pm == "PM_SUCCESS"
ticket_pm = details_pm.get('ticket')
print(f"[OK] Option 2 PM Logged: {ticket_pm} ({details_pm.get('equipment')})")

# 5. Test Option 3 (Scheduled Welding Work)
reply_wd, action_wd, details_wd = parser.parse_whatsapp_message("3 Conveyor Rail | Factory Line C | Guard Rail Welding | 2 PM Today", sender_name="Sam Welder")
assert action_wd == "WD_SUCCESS"
ticket_wd = details_wd.get('ticket')
print(f"[OK] Option 3 Welding Logged: {ticket_wd} ({details_wd.get('equipment')})")

# 6. Test Option 4 (Open Orders Query)
reply_open, action_open, details_open = parser.parse_whatsapp_message("4")
assert action_open == "OPEN_ORDERS"
print(f"[OK] Option 4 Open Orders query verified: {details_open}")

# 7. Test Option 6 (Close Order)
reply_close, action_close, details_close = parser.parse_whatsapp_message(f"{ticket_bd} Fixed", sender_name="Supervisor")
assert action_close == "FIX_SUCCESS"
print(f"[OK] Option 6 Order Closed: Ticket {details_close.get('ticket_number')} Status: {details_close.get('status')}")

# 8. Test Option 5 (MTBF & MTTR Statistics)
stats = database.get_statistics()
assert "mtbf_hours" in stats, "MTBF hours must be present in statistics"
assert "mttr_minutes" in stats, "MTTR minutes must be present in statistics"
print(f"[OK] MTTR & MTBF Statistics calculated:\n  Total BDs: {stats['total_breakdowns']}\n  MTTR: {stats['mttr_minutes']} mins\n  MTBF: {stats['mtbf_hours']} hrs\n  PM Logs: {stats['total_pm_logs']}\n  Welding Logs: {stats['total_welding_logs']}")

# 9. Test Excel Report Generation
filepath, filename = excel_generator.generate_excel_report()
assert os.path.exists(filepath), "Excel file must exist"
print(f"[OK] Formatted Excel report generated: {filename} ({os.path.getsize(filepath)} bytes)")

print("--- ALL VERIFICATION TESTS PASSED SUCCESSFULLY! ---")
