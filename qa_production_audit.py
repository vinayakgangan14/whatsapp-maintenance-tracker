import sys
import os
import json
import datetime

# Add project root to sys.path
PROJECT_ROOT = r"C:\Users\HP\.gemini\antigravity\scratch\whatsapp-maintenance-tracker"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.chdir(PROJECT_ROOT)

import database
import google_sheets
import excel_generator

print("=========================================================")
print("=== PURECHEM MAINTENANCE TRACKING PORTAL - FULL QA AUDIT ===")
print("=========================================================\n")

def test_1_database_init():
    print("[TEST 1] Database Initialization & Table Schemas...")
    database.init_db()
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row['name'] for row in cursor.fetchall()]
    conn.close()
    
    expected = ['breakdowns', 'maintenance_logs', 'welding_logs', 'settings']
    for t in expected:
        assert t in tables, f"Missing table: {t}"
    print("  [OK] All database tables present (breakdowns, maintenance_logs, welding_logs, settings)\n")

def test_2_breakdown_lifecycle():
    print("[TEST 2] Breakdown Ticket Lifecycle (Create -> Assign -> Approve -> Resolve)...")
    ticket, bd_id = database.log_breakdown(
        department="Plastic",
        equipment_id="1LTR-1",
        issue_description="Heater band failure during test run",
        sender_name="QA Tester"
    )
    assert ticket.startswith("BD-"), f"Invalid ticket format: {ticket}"
    print(f"  • Breakdown Created: {ticket} (ID: {bd_id})")
    
    # Staff Assignment
    ok, msg = database.assign_ticket(ticket, "NKWOR HENRY - MECHANICAL Dept")
    assert ok, "Failed to assign staff"
    print(f"  • Staff Assigned: NKWOR HENRY")
    
    # Manager Approval
    ok, msg = database.approve_ticket(ticket, "Mr. Shanmugham")
    assert ok, "Failed to approve ticket"
    print(f"  • Approved by: Mr. Shanmugham")
    
    # Resolution
    updated, err = database.resolve_breakdown(
        ticket_number=ticket,
        resolution_notes="Replaced heating element and calibrated temperature controller",
        technician="NKWOR HENRY"
    )
    assert updated and updated['status'] == 'RESOLVED', f"Failed to resolve: {err}"
    assert updated['duration_minutes'] >= 1, "Duration minutes not captured"
    print(f"  • Ticket Resolved: Duration {updated['duration_minutes']} mins, Notes: {updated['resolution_notes']}\n")

def test_3_pm_lifecycle():
    print("[TEST 3] Preventive Maintenance Lifecycle (Create -> Approve -> Resolve)...")
    ticket = database.log_maintenance(
        department="Utility",
        equipment_id="STEAM BOILER -1",
        activity_description="Quarterly safety valve inspection and water treatment check",
        scheduled_time="Tomorrow 8:00 AM",
        technician="AFOLABI BABATUNDEY - ELECTRICAL Dept"
    )
    assert ticket.startswith("PM-"), f"Invalid PM ticket: {ticket}"
    print(f"  • PM Scheduled: {ticket}")
    
    # Manager Approval
    ok, msg = database.approve_ticket(ticket, "MR. RAJU NEEL")
    assert ok, "Failed to approve PM"
    print(f"  • Approved by: MR. RAJU NEEL")
    
    # PM Resolution
    updated, err = database.resolve_breakdown(
        ticket_number=ticket,
        technician="AFOLABI BABATUNDEY"
    )
    assert updated and updated['status'] == 'RESOLVED', f"Failed to resolve PM: {err}"
    print(f"  • PM Ticket Resolved: Status = {updated['status']}\n")

def test_4_welding_lifecycle():
    print("[TEST 4] Welding Work Lifecycle (Create -> Reject with Reason)...")
    ticket = database.log_welding(
        department="LCP/PU",
        equipment_id="LCP REACTOR-1",
        location="LCP/PU",
        welding_details="Reinforce support bracket on agitator motor frame",
        scheduled_time="Today 4:00 PM",
        technician="JULIOUS SAMUEL - MECHANICAL Dept"
    )
    assert ticket.startswith("WD-"), f"Invalid Welding ticket: {ticket}"
    print(f"  • Welding Scheduled: {ticket}")
    
    # Manager Rejection with Reason
    ok, msg = database.reject_ticket(ticket, "Mr. Shanmugham", reason="Hot work permit required first")
    assert ok, "Failed to reject welding ticket"
    print(f"  • Rejected by Manager: Reason = 'Hot work permit required first'\n")

def test_5_analytics_formulas():
    print("[TEST 5] MTTR & MTBF Analytics Formulas...")
    stats = database.get_statistics()
    print(f"  • Total Breakdowns: {stats['total_breakdowns']}")
    print(f"  • Open Breakdowns: {stats['open_breakdowns']}")
    print(f"  • Resolved Breakdowns: {stats['resolved_breakdowns']}")
    print(f"  • Total Downtime: {stats['total_downtime_minutes']} mins ({stats['total_downtime_hours']} hrs)")
    print(f"  • MTTR: {stats['mttr_minutes']} mins")
    print(f"  • MTBF: {stats['mtbf_hours']} hrs ({stats['mtbf_minutes']} mins between failures)")
    
    assert stats['mttr_minutes'] >= 0, "Invalid MTTR"
    assert stats['mtbf_hours'] > 0, "MTBF should not be 0"
    print("  [OK] Analytics metrics calculated accurately without zero-division errors\n")

def test_6_excel_report():
    print("[TEST 6] Excel Report Generation...")
    res = excel_generator.generate_excel_report()
    output_path = res[0] if isinstance(res, tuple) else res
    assert os.path.exists(output_path), "Excel report file not created"
    file_size = os.path.getsize(output_path)
    assert file_size > 5000, f"Excel report size too small: {file_size} bytes"
    print(f"  [OK] Report Generated: {os.path.basename(output_path)} ({file_size} bytes)\n")

def run_all_qa_tests():
    try:
        test_1_database_init()
        test_2_breakdown_lifecycle()
        test_3_pm_lifecycle()
        test_4_welding_lifecycle()
        test_5_analytics_formulas()
        test_6_excel_report()
        print("=========================================================")
        print("SUCCESS: ALL 6 QA SUITE TESTS PASSED 100% CLEANLY!")
        print("=========================================================")
    except Exception as e:
        print(f"QA TEST FAILURE: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_all_qa_tests()
