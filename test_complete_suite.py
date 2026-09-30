import sys
import os
import json
import time

import database

def run_tests():
    print("=" * 60)
    print("STARTING COMPREHENSIVE MULTI-TENANT TEST SUITE")
    print("=" * 60)

    database.init_db()

    ts = int(time.time())
    comp_a_name = f"Test Alpha Motors {ts}"
    comp_b_name = f"Test Beta Plastics {ts}"

    # TEST 1: Register Company A
    print("\n--- Test 1: Register New Company A (Blank Slate Check) ---")
    comp_a = database.get_or_create_company(comp_a_name)
    comp_a_id = comp_a["id"]
    print(f"Company A Created: ID={comp_a_id}, Name={comp_a['company_name']}")

    users_a = database.get_company_users(comp_a_id)
    depts_a = database.get_custom_departments(comp_a_id)
    bds_a = database.get_all_breakdowns(company_id=comp_a_id)
    admin_check_a = database.check_company_has_admin(comp_a_id)

    print(f"Company A Users count: {len(users_a)} (Expected: 0)")
    print(f"Company A Depts count: {len(depts_a)} (Expected: 0)")
    print(f"Company A Breakdowns count: {len(bds_a)} (Expected: 0)")
    print(f"Company A Has Admin: {admin_check_a['has_admin']} (Expected: False)")

    assert len(users_a) == 0, "New company must start with 0 users!"
    assert len(depts_a) == 0, "New company must start with 0 departments!"
    assert len(bds_a) == 0, "New company must start with 0 breakdowns!"
    assert admin_check_a['has_admin'] is False, "New company must not have admin!"
    print("PASS: Company A started 100% BLANK slate.")

    # TEST 2: First-Time Admin Registration for Company A
    print("\n--- Test 2: First-Time Admin Registration ---")
    admin_a, err = database.add_user("admin@alpha.com", "AlphaSecret123", "Admin", company_id=comp_a_id)
    print(f"Registered Admin A: {admin_a}")
    assert err is None and admin_a is not False, f"Admin creation failed: {err}"
    
    admin_check_a_after = database.check_company_has_admin(comp_a_id)
    print(f"Company A Has Admin now: {admin_check_a_after['has_admin']} (Expected: True)")
    assert admin_check_a_after['has_admin'] is True, "Admin check failed!"
    print("PASS: First-Time Admin registered successfully.")

    # TEST 3: Admin Creates Operators & Managers
    print("\n--- Test 3: Create Company Staff & Plant Config ---")
    op_a, _ = database.add_user("operator.sam@alpha.com", "OpPass123", "Operator", company_id=comp_a_id)
    mgr_a, _ = database.add_user("manager.jane@alpha.com", "MgrPass123", "Manager", company_id=comp_a_id)
    print(f"Created Operator: {op_a['email_or_name']}")
    print(f"Created Manager: {mgr_a['email_or_name']}")

    dept_id = database.add_custom_department("Assembly Line B", company_id=comp_a_id)
    eq_id = database.add_custom_equipment("Assembly Line B", "Robotic Arm #4", company_id=comp_a_id)
    print(f"Added Department ID: {dept_id}")
    print(f"Added Equipment ID: {eq_id}")
    print("PASS: Company staff and plant config created.")

    # TEST 4: Ticket Lifecycle (Log -> Approve & Assign -> Resolve)
    print("\n--- Test 4: Ticket Lifecycle (Breakdown -> Approve -> Assign -> Resolve) ---")
    ticket_no, bd_id = database.log_breakdown(
        department="Assembly Line B",
        equipment_id="Robotic Arm #4",
        issue_description="Motor overheating and noise",
        sender_name="operator.sam@alpha.com",
        company_id=comp_a_id
    )
    print(f"Logged Breakdown Ticket: {ticket_no}")

    # Check status is PENDING_APPROVAL
    bds = database.get_all_breakdowns(company_id=comp_a_id)
    assert len(bds) == 1, f"Should have 1 breakdown ticket, got {len(bds)}!"
    assert bds[0]['status'] == 'PENDING_APPROVAL', "Initial status must be PENDING_APPROVAL"

    # Approve & Assign
    ok_app, _ = database.approve_ticket(ticket_no, manager_name="manager.jane@alpha.com")
    ok_ass, _ = database.assign_ticket(ticket_no, assigned_to_name="operator.sam@alpha.com")
    print(f"Approved: {ok_app}, Assigned to operator.sam@alpha.com: {ok_ass}")

    # Resolve Ticket
    resolved_rec, res_err = database.resolve_breakdown(
        ticket_number=ticket_no,
        resolution_notes="Replaced faulty bearing and lubricated motor",
        technician="operator.sam@alpha.com",
        company_id=comp_a_id
    )
    print(f"Resolve Result: Status={resolved_rec.get('status') if resolved_rec else None}, Error={res_err}")
    assert res_err is None, f"Resolution failed: {res_err}"
    assert resolved_rec['status'] == 'RESOLVED', "Ticket status should be RESOLVED"
    print("PASS: Full ticket lifecycle completed successfully.")

    # TEST 5: Verify Overview Analytics
    print("\n--- Test 5: Verify Overview Analytics ---")
    stats_a = database.get_statistics(company_id=comp_a_id)
    print(f"Company A Stats: Total BD={stats_a['total_breakdowns']}, Open={stats_a['open_breakdowns']}, Resolved={stats_a['resolved_breakdowns']}")
    assert stats_a['total_breakdowns'] == 1, "Total breakdowns count incorrect!"
    assert stats_a['open_breakdowns'] == 0, "Open breakdowns count incorrect!"
    assert stats_a['resolved_breakdowns'] == 1, "Resolved breakdowns count incorrect!"
    print("PASS: Overview Analytics matched expected counts.")

    # TEST 6: Register Company B and Verify Strict Multi-Tenant Data Isolation
    print("\n--- Test 6: Cross-Company Data Isolation Check ---")
    comp_b = database.get_or_create_company(comp_b_name)
    comp_b_id = comp_b["id"]
    print(f"Company B Created: ID={comp_b_id}, Name={comp_b['company_name']}")

    bds_b = database.get_all_breakdowns(company_id=comp_b_id)
    users_b = database.get_company_users(comp_b_id)
    stats_b = database.get_statistics(company_id=comp_b_id)

    print(f"Company B Breakdowns count: {len(bds_b)} (Expected: 0)")
    print(f"Company B Users count: {len(users_b)} (Expected: 0)")
    print(f"Company B Total BD Stats: {stats_b['total_breakdowns']} (Expected: 0)")

    assert len(bds_b) == 0, "Company B must NOT see Company A's breakdowns!"
    assert len(users_b) == 0, "Company B must NOT see Company A's users!"
    assert stats_b['total_breakdowns'] == 0, "Company B stats must be 0!"
    print("PASS: 100% Data Isolation verified between Company A and Company B.")

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
