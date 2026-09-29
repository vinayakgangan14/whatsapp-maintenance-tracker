import sqlite3
import datetime
import os
import json
import urllib.request
import urllib.parse
from config import DB_PATH

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# --------------------------------------------------------------------
# REAL-TIME SUPABASE SYNC HELPERS (HTTP REST API via urllib)
# --------------------------------------------------------------------

def sync_to_supabase(table_name, record_dict):
    """
    Pushes/upserts a record into Supabase REST API if SUPABASE_URL & key are configured.
    """
    supabase_url = (os.getenv("SUPABASE_URL") or get_setting("SUPABASE_URL", "")).rstrip("/")
    supabase_key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY") or
        os.getenv("SUPABASE_ANON_KEY") or
        os.getenv("SUPABASE_KEY") or
        get_setting("SUPABASE_ANON_KEY", "")
    )
    
    if not supabase_url or not supabase_key:
        return False, "Supabase environment variables not configured"

    try:
        endpoint = f"{supabase_url}/rest/v1/{table_name}"
        payload = dict(record_dict)
        
        # Strip local SQLite internal flags if needed
        payload.pop("synced_to_sheets", None)
        
        # Ensure company_id is present
        if "company_id" not in payload:
            payload["company_id"] = "default"
            
        data_bytes = json.dumps(payload).encode("utf-8")
        
        req = urllib.request.Request(endpoint, data=data_bytes, method="POST")
        req.add_header("apikey", supabase_key)
        req.add_header("Authorization", f"Bearer {supabase_key}")
        req.add_header("Content-Type", "application/json")
        req.add_header("Prefer", "resolution=merge-duplicates,return=representation")
        
        with urllib.request.urlopen(req, timeout=5) as response:
            res_body = response.read().decode("utf-8")
            return True, res_body
    except Exception as e:
        print(f"[Supabase Sync Error] Table '{table_name}': {e}")
        return False, str(e)


def delete_from_supabase(table_name, query_params):
    """
    Deletes record(s) from Supabase REST API matching query_params dict.
    """
    supabase_url = (os.getenv("SUPABASE_URL") or get_setting("SUPABASE_URL", "")).rstrip("/")
    supabase_key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY") or
        os.getenv("SUPABASE_ANON_KEY") or
        os.getenv("SUPABASE_KEY") or
        get_setting("SUPABASE_ANON_KEY", "")
    )
    
    if not supabase_url or not supabase_key:
        return False, "Supabase environment variables not configured"

    try:
        qs = urllib.parse.urlencode(query_params)
        endpoint = f"{supabase_url}/rest/v1/{table_name}?{qs}"
        req = urllib.request.Request(endpoint, method="DELETE")
        req.add_header("apikey", supabase_key)
        req.add_header("Authorization", f"Bearer {supabase_key}")
        
        with urllib.request.urlopen(req, timeout=5) as response:
            res_body = response.read().decode("utf-8")
            return True, res_body
    except Exception as e:
        print(f"[Supabase Delete Error] Table '{table_name}': {e}")
        return False, str(e)


def sync_all_to_supabase():
    """
    Batch pushes all local SQLite records to Supabase REST API.
    """
    results = {}
    tables = ["breakdowns", "maintenance_logs", "welding_logs", "custom_departments", "custom_equipment", "users"]
    conn = get_db_connection()
    cursor = conn.cursor()
    
    for tbl in tables:
        try:
            cursor.execute(f"SELECT * FROM {tbl}")
            rows = [dict(row) for row in cursor.fetchall()]
            synced_count = 0
            for r in rows:
                ok, _ = sync_to_supabase(tbl, r)
                if ok:
                    synced_count += 1
            results[tbl] = synced_count
        except Exception as e:
            results[tbl] = f"Error: {e}"
            
    conn.close()
    return results


# --------------------------------------------------------------------
# DATABASE INITIALIZATION
# --------------------------------------------------------------------

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Breakdowns table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS breakdowns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id TEXT NOT NULL DEFAULT 'default',
            ticket_number TEXT UNIQUE NOT NULL,
            department TEXT NOT NULL DEFAULT 'General',
            sender_phone TEXT,
            sender_name TEXT,
            equipment_id TEXT NOT NULL,
            issue_description TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT,
            status TEXT NOT NULL DEFAULT 'PENDING_APPROVAL',
            assigned_to TEXT DEFAULT 'Unassigned',
            duration_minutes INTEGER DEFAULT 0,
            resolution_notes TEXT,
            technician TEXT,
            synced_to_sheets INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    ''')
    try:
        cursor.execute("ALTER TABLE breakdowns ADD COLUMN assigned_to TEXT DEFAULT 'Unassigned'")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE breakdowns ADD COLUMN company_id TEXT DEFAULT 'default'")
    except sqlite3.OperationalError:
        pass

    # Preventive Maintenance table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS maintenance_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id TEXT NOT NULL DEFAULT 'default',
            ticket_number TEXT UNIQUE NOT NULL,
            department TEXT NOT NULL DEFAULT 'General',
            sender_phone TEXT,
            sender_name TEXT,
            equipment_id TEXT NOT NULL,
            activity_description TEXT NOT NULL,
            scheduled_time TEXT,
            status TEXT NOT NULL DEFAULT 'PENDING_APPROVAL',
            assigned_to TEXT DEFAULT 'Unassigned',
            technician TEXT,
            performed_at TEXT NOT NULL,
            synced_to_sheets INTEGER DEFAULT 0
        )
    ''')
    try:
        cursor.execute("ALTER TABLE maintenance_logs ADD COLUMN scheduled_time TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE maintenance_logs ADD COLUMN status TEXT DEFAULT 'PENDING_APPROVAL'")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE maintenance_logs ADD COLUMN assigned_to TEXT DEFAULT 'Unassigned'")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE maintenance_logs ADD COLUMN company_id TEXT DEFAULT 'default'")
    except sqlite3.OperationalError:
        pass

    # Scheduled Welding Work table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS welding_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id TEXT NOT NULL DEFAULT 'default',
            ticket_number TEXT UNIQUE NOT NULL,
            department TEXT NOT NULL DEFAULT 'General',
            sender_phone TEXT,
            sender_name TEXT,
            equipment_id TEXT NOT NULL,
            location TEXT,
            welding_details TEXT NOT NULL,
            scheduled_time TEXT,
            status TEXT NOT NULL DEFAULT 'PENDING_APPROVAL',
            assigned_to TEXT DEFAULT 'Unassigned',
            technician TEXT,
            created_at TEXT NOT NULL,
            synced_to_sheets INTEGER DEFAULT 0
        )
    ''')
    try:
        cursor.execute("ALTER TABLE welding_logs ADD COLUMN assigned_to TEXT DEFAULT 'Unassigned'")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE welding_logs ADD COLUMN company_id TEXT DEFAULT 'default'")
    except sqlite3.OperationalError:
        pass

    # System Settings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')

    # Custom Departments Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS custom_departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id TEXT NOT NULL DEFAULT 'default',
            department_name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(company_id, department_name)
        )
    ''')

    # Custom Equipment Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS custom_equipment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id TEXT NOT NULL DEFAULT 'default',
            department_name TEXT NOT NULL,
            equipment_name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(company_id, department_name, equipment_name)
        )
    ''')

    # Users & Access Control Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id TEXT NOT NULL DEFAULT 'default',
            email_or_name TEXT NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('Operator', 'Manager', 'Admin')),
            created_at TEXT NOT NULL,
            UNIQUE(company_id, email_or_name)
        )
    ''')

    conn.commit()
    conn.close()
    seed_default_plant_config()
    seed_default_users()

def generate_ticket_number(prefix="BD"):
    conn = get_db_connection()
    cursor = conn.cursor()
    now_year = datetime.datetime.now().strftime("%Y%m")
    
    if prefix == "BD":
        cursor.execute("SELECT COUNT(*) as cnt FROM breakdowns WHERE ticket_number LIKE ?", (f"BD-{now_year}-%",))
    elif prefix == "PM":
        cursor.execute("SELECT COUNT(*) as cnt FROM maintenance_logs WHERE ticket_number LIKE ?", (f"PM-{now_year}-%",))
    elif prefix == "WD":
        cursor.execute("SELECT COUNT(*) as cnt FROM welding_logs WHERE ticket_number LIKE ?", (f"WD-{now_year}-%",))
    else:
        cursor.execute("SELECT COUNT(*) as cnt FROM breakdowns WHERE ticket_number LIKE ?", (f"{prefix}-{now_year}-%",))
        
    cnt = cursor.fetchone()['cnt'] + 1
    conn.close()
    return f"{prefix}-{now_year}-{cnt:03d}"

def log_breakdown(department, equipment_id, issue_description, sender_phone="", sender_name="", assigned_to="Unassigned", company_id="default"):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    ticket = generate_ticket_number("BD")
    now_str = datetime.datetime.now().isoformat()
    
    cursor.execute('''
        INSERT INTO breakdowns 
        (company_id, ticket_number, department, sender_phone, sender_name, equipment_id, issue_description, start_time, status, assigned_to, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDING_APPROVAL', ?, ?)
    ''', (company_id, ticket, department, sender_phone, sender_name, equipment_id, issue_description, now_str, assigned_to or 'Unassigned', now_str))
    
    conn.commit()
    breakdown_id = cursor.lastrowid
    
    cursor.execute("SELECT * FROM breakdowns WHERE id = ?", (breakdown_id,))
    row_dict = dict(cursor.fetchone())
    conn.close()
    
    sync_to_supabase("breakdowns", row_dict)
    return ticket, breakdown_id

def resolve_breakdown(equipment_id=None, ticket_number=None, resolution_notes="", technician="", department="General"):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    record = None
    target_table = "breakdowns"
    
    # 1. Search by exact ticket_number first across all tables if provided
    if ticket_number and str(ticket_number).strip():
        tn = str(ticket_number).strip()
        # Search breakdowns
        cursor.execute("SELECT * FROM breakdowns WHERE ticket_number = ? AND status != 'RESOLVED'", (tn,))
        record = cursor.fetchone()
        if record:
            target_table = "breakdowns"
        else:
            # Search maintenance_logs
            cursor.execute("SELECT * FROM maintenance_logs WHERE ticket_number = ? AND status != 'RESOLVED'", (tn,))
            record = cursor.fetchone()
            if record:
                target_table = "maintenance_logs"
            else:
                # Search welding_logs
                cursor.execute("SELECT * FROM welding_logs WHERE ticket_number = ? AND status != 'RESOLVED'", (tn,))
                record = cursor.fetchone()
                if record:
                    target_table = "welding_logs"
                    
    # 2. Fallback to searching by equipment_id in breakdowns if no record found yet by ticket_number
    if not record and equipment_id and str(equipment_id).strip():
        eq = str(equipment_id).strip()
        cursor.execute("SELECT * FROM breakdowns WHERE equipment_id LIKE ? AND status != 'RESOLVED' ORDER BY id DESC LIMIT 1", (f"%{eq}%",))
        record = cursor.fetchone()
        if record:
            target_table = "breakdowns"

    if not record:
        conn.close()
        return None, f"No active open ticket found for ticket '{ticket_number or equipment_id}'."

    end_dt = datetime.datetime.now()
    end_iso = end_dt.isoformat()
    rec_dict = dict(record)

    if target_table == "breakdowns":
        try:
            start_str = str(rec_dict.get('start_time', '')).strip().replace(' ', 'T')
            if len(start_str) > 19 and '.' not in start_str and '+' not in start_str and 'Z' not in start_str:
                start_str = start_str[:19]
            start_dt = datetime.datetime.fromisoformat(start_str)
            duration_mins = max(1, int((end_dt - start_dt).total_seconds() / 60))
        except Exception:
            duration_mins = 1

        cursor.execute('''
            UPDATE breakdowns 
            SET status = 'RESOLVED',
                end_time = ?,
                duration_minutes = ?,
                resolution_notes = ?,
                technician = ?,
                synced_to_sheets = 0
            WHERE id = ?
        ''', (end_iso, duration_mins, resolution_notes, technician or rec_dict.get('sender_name') or 'Technician', rec_dict['id']))
        conn.commit()
        cursor.execute("SELECT * FROM breakdowns WHERE id = ?", (rec_dict['id'],))
        updated = dict(cursor.fetchone())
        conn.close()
        sync_to_supabase("breakdowns", updated)
        return updated, None

    elif target_table == "maintenance_logs":
        cursor.execute('''
            UPDATE maintenance_logs 
            SET status = 'RESOLVED',
                technician = ?
            WHERE id = ?
        ''', (technician or rec_dict.get('technician') or 'Technician', rec_dict['id']))
        conn.commit()
        cursor.execute("SELECT * FROM maintenance_logs WHERE id = ?", (rec_dict['id'],))
        updated = dict(cursor.fetchone())
        conn.close()
        sync_to_supabase("maintenance_logs", updated)
        return updated, None

    elif target_table == "welding_logs":
        cursor.execute('''
            UPDATE welding_logs 
            SET status = 'RESOLVED',
                technician = ?
            WHERE id = ?
        ''', (technician or rec_dict.get('sender_name') or 'Welder', rec_dict['id']))
        conn.commit()
        cursor.execute("SELECT * FROM welding_logs WHERE id = ?", (rec_dict['id'],))
        updated = dict(cursor.fetchone())
        conn.close()
        sync_to_supabase("welding_logs", updated)
        return updated, None

def log_maintenance(department, equipment_id, activity_description, scheduled_time="", technician="", sender_phone="", sender_name="", assigned_to="Unassigned", company_id="default"):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    ticket = generate_ticket_number("PM")
    now_str = datetime.datetime.now().isoformat()
    
    cursor.execute('''
        INSERT INTO maintenance_logs
        (company_id, ticket_number, department, sender_phone, sender_name, equipment_id, activity_description, scheduled_time, status, assigned_to, technician, performed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDING_APPROVAL', ?, ?, ?)
    ''', (company_id, ticket, department, sender_phone, sender_name, equipment_id, activity_description, scheduled_time, assigned_to or 'Unassigned', technician or sender_name, now_str))
    
    conn.commit()
    pm_id = cursor.lastrowid
    cursor.execute("SELECT * FROM maintenance_logs WHERE id = ?", (pm_id,))
    row_dict = dict(cursor.fetchone())
    conn.close()
    
    sync_to_supabase("maintenance_logs", row_dict)
    return ticket

def log_welding(department, equipment_id, location, welding_details, scheduled_time="", technician="", sender_phone="", sender_name="", assigned_to="Unassigned", company_id="default"):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    ticket = generate_ticket_number("WD")
    now_str = datetime.datetime.now().isoformat()
    
    cursor.execute('''
        INSERT INTO welding_logs
        (company_id, ticket_number, department, sender_phone, sender_name, equipment_id, location, welding_details, scheduled_time, status, assigned_to, technician, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDING_APPROVAL', ?, ?, ?)
    ''', (company_id, ticket, department, sender_phone, sender_name, equipment_id, location, welding_details, scheduled_time, assigned_to or 'Unassigned', technician or sender_name, now_str))
    
    conn.commit()
    wd_id = cursor.lastrowid
    cursor.execute("SELECT * FROM welding_logs WHERE id = ?", (wd_id,))
    row_dict = dict(cursor.fetchone())
    conn.close()
    
    sync_to_supabase("welding_logs", row_dict)
    return ticket

def assign_ticket(ticket_number, assigned_to_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    table = None
    if ticket_number.startswith("BD-"):
        cursor.execute("UPDATE breakdowns SET assigned_to = ? WHERE ticket_number = ?", (assigned_to_name, ticket_number))
        table = "breakdowns"
    elif ticket_number.startswith("PM-"):
        cursor.execute("UPDATE maintenance_logs SET assigned_to = ? WHERE ticket_number = ?", (assigned_to_name, ticket_number))
        table = "maintenance_logs"
    elif ticket_number.startswith("WD-"):
        cursor.execute("UPDATE welding_logs SET assigned_to = ? WHERE ticket_number = ?", (assigned_to_name, ticket_number))
        table = "welding_logs"
        
    conn.commit()
    if table:
        cursor.execute(f"SELECT * FROM {table} WHERE ticket_number = ?", (ticket_number,))
        row = cursor.fetchone()
        if row:
            sync_to_supabase(table, dict(row))
    conn.close()
    return True, f"Ticket {ticket_number} assigned to {assigned_to_name}."

def approve_ticket(ticket_number, manager_name="Maintenance Manager"):
    conn = get_db_connection()
    cursor = conn.cursor()
    table = None
    if ticket_number.startswith("BD-"):
        cursor.execute("UPDATE breakdowns SET status = 'APPROVED' WHERE ticket_number = ?", (ticket_number,))
        table = "breakdowns"
    elif ticket_number.startswith("PM-"):
        cursor.execute("UPDATE maintenance_logs SET status = 'APPROVED' WHERE ticket_number = ?", (ticket_number,))
        table = "maintenance_logs"
    elif ticket_number.startswith("WD-"):
        cursor.execute("UPDATE welding_logs SET status = 'APPROVED' WHERE ticket_number = ?", (ticket_number,))
        table = "welding_logs"
        
    conn.commit()
    if table:
        cursor.execute(f"SELECT * FROM {table} WHERE ticket_number = ?", (ticket_number,))
        row = cursor.fetchone()
        if row:
            sync_to_supabase(table, dict(row))
    conn.close()
    return True, "Ticket approved successfully."

def reject_ticket(ticket_number, manager_name="Maintenance Manager", reason=""):
    conn = get_db_connection()
    cursor = conn.cursor()
    table = None
    note = f"Rejected by {manager_name}" + (f": {reason}" if reason else "")
    if ticket_number.startswith("BD-"):
        cursor.execute("UPDATE breakdowns SET status = 'REJECTED', resolution_notes = ? WHERE ticket_number = ?", (note, ticket_number))
        table = "breakdowns"
    elif ticket_number.startswith("PM-"):
        cursor.execute("UPDATE maintenance_logs SET status = 'REJECTED', activity_description = activity_description || ? WHERE ticket_number = ?", (f" [{note}]", ticket_number))
        table = "maintenance_logs"
    elif ticket_number.startswith("WD-"):
        cursor.execute("UPDATE welding_logs SET status = 'REJECTED', welding_details = welding_details || ? WHERE ticket_number = ?", (f" [{note}]", ticket_number))
        table = "welding_logs"
        
    conn.commit()
    if table:
        cursor.execute(f"SELECT * FROM {table} WHERE ticket_number = ?", (ticket_number,))
        row = cursor.fetchone()
        if row:
            sync_to_supabase(table, dict(row))
    conn.close()
    return True, "Ticket rejected."

def get_open_breakdowns():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM breakdowns WHERE status != 'RESOLVED' AND status != 'REJECTED' ORDER BY id DESC")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def get_open_welding():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM welding_logs WHERE status != 'RESOLVED' AND status != 'REJECTED' ORDER BY id DESC")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def get_all_breakdowns(limit=100):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM breakdowns ORDER BY id DESC LIMIT ?", (limit,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def get_all_maintenance(limit=100):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM maintenance_logs ORDER BY id DESC LIMIT ?", (limit,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def get_all_welding(limit=100):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM welding_logs ORDER BY id DESC LIMIT ?", (limit,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def get_statistics():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as total_bd FROM breakdowns")
    total_bd = cursor.fetchone()['total_bd']
    
    cursor.execute("SELECT COUNT(*) as open_bd FROM breakdowns WHERE status != 'RESOLVED' AND status != 'REJECTED'")
    open_bd = cursor.fetchone()['open_bd']

    cursor.execute("SELECT COUNT(*) as pending_bd FROM breakdowns WHERE status = 'PENDING_APPROVAL'")
    pending_bd = cursor.fetchone()['pending_bd']
    
    cursor.execute("SELECT COUNT(*) as resolved_bd FROM breakdowns WHERE status = 'RESOLVED'")
    resolved_bd = cursor.fetchone()['resolved_bd']
    
    cursor.execute("SELECT SUM(duration_minutes) as total_downtime FROM breakdowns WHERE status = 'RESOLVED'")
    sum_downtime = cursor.fetchone()['total_downtime'] or 0

    cursor.execute("SELECT COUNT(*) as total_pm FROM maintenance_logs")
    total_pm = cursor.fetchone()['total_pm']
    
    cursor.execute("SELECT COUNT(*) as total_wd FROM welding_logs")
    total_wd = cursor.fetchone()['total_wd']
    
    cursor.execute("SELECT COUNT(*) as open_wd FROM welding_logs WHERE status != 'RESOLVED' AND status != 'REJECTED'")
    open_wd = cursor.fetchone()['open_wd']
    
    # MTTR (Mean Time To Repair in Minutes): Total Downtime / Resolved Breakdowns
    mttr_minutes = round(sum_downtime / max(1, resolved_bd), 1) if resolved_bd > 0 else 0.0

    # MTBF (Mean Time Between Failures): Total Operating Time / Total Failures
    if total_bd == 0:
        mtbf_minutes = 0.0
        mtbf_hours = 0.0
    else:
        cursor.execute("SELECT MIN(created_at), MIN(start_time) FROM breakdowns")
        row = cursor.fetchone()
        earliest_str = row[0] or row[1] if row else None
        
        now = datetime.datetime.now()
        if earliest_str:
            try:
                clean_str = str(earliest_str).strip().replace(' ', 'T')
                if len(clean_str) > 19 and '.' not in clean_str and '+' not in clean_str and 'Z' not in clean_str:
                    clean_str = clean_str[:19]
                earliest_dt = datetime.datetime.fromisoformat(clean_str)
                elapsed_mins = (now - earliest_dt).total_seconds() / 60.0
                tracking_window_mins = max(30 * 24 * 60.0, elapsed_mins)
                operating_mins = max(1.0, tracking_window_mins - sum_downtime)
            except Exception:
                operating_mins = float(30 * 24 * 60 - sum_downtime)
        else:
            operating_mins = float(30 * 24 * 60)

        mtbf_minutes = round(operating_mins / total_bd, 1)
        mtbf_hours = round(mtbf_minutes / 60.0, 1)
    
    cursor.execute("SELECT department, COUNT(*) as count FROM breakdowns GROUP BY department")
    dept_counts = {row['department']: row['count'] for row in cursor.fetchall()}
    
    conn.close()
    return {
        "total_breakdowns": total_bd,
        "open_breakdowns": open_bd,
        "pending_breakdowns": pending_bd,
        "resolved_breakdowns": resolved_bd,
        "total_downtime_minutes": sum_downtime,
        "total_downtime_hours": round(sum_downtime / 60.0, 2),
        "mttr_minutes": mttr_minutes,
        "mtbf_minutes": mtbf_minutes,
        "mtbf_hours": mtbf_hours,
        "total_pm_logs": total_pm,
        "total_welding_logs": total_wd,
        "open_welding_logs": open_wd,
        "department_distribution": dept_counts
    }

def get_setting(key, default=""):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row['value'] if row else default

def set_setting(key, value):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

def clear_all_records():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM breakdowns")
    cursor.execute("DELETE FROM maintenance_logs")
    cursor.execute("DELETE FROM welding_logs")
    conn.commit()
    conn.close()
    return True

# --------------------------------------------------------------------
# DYNAMIC PLANT & EQUIPMENT MANAGEMENT FUNCTIONS
# --------------------------------------------------------------------

def get_custom_departments(company_id='default'):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, department_name FROM custom_departments WHERE company_id = ? ORDER BY department_name ASC", (company_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def add_custom_department(department_name, company_id='default'):
    if not department_name or not department_name.strip():
        return False
    dept_name = department_name.strip()
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.datetime.now().isoformat()
    try:
        cursor.execute("INSERT OR IGNORE INTO custom_departments (company_id, department_name, created_at) VALUES (?, ?, ?)",
                       (company_id, dept_name, now_str))
        conn.commit()
        cursor.execute("SELECT id FROM custom_departments WHERE company_id = ? AND department_name = ?", (company_id, dept_name))
        row = cursor.fetchone()
        dept_id = row['id'] if row else True
        conn.close()
        sync_to_supabase("custom_departments", {"company_id": company_id, "department_name": dept_name, "created_at": now_str})
        return dept_id
    except Exception as e:
        conn.close()
        return False

def delete_custom_department(dept_id, company_id='default'):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT department_name FROM custom_departments WHERE id = ? AND company_id = ?", (dept_id, company_id))
    row = cursor.fetchone()
    if row:
        dept_name = row['department_name']
        cursor.execute("DELETE FROM custom_equipment WHERE department_name = ? AND company_id = ?", (dept_name, company_id))
        cursor.execute("DELETE FROM custom_departments WHERE id = ? AND company_id = ?", (dept_id, company_id))
        conn.commit()
        delete_from_supabase("custom_departments", {"department_name": f"eq.{dept_name}", "company_id": f"eq.{company_id}"})
    conn.close()
    return True

def get_custom_equipment(department_name=None, company_id='default'):
    conn = get_db_connection()
    cursor = conn.cursor()
    if department_name:
        cursor.execute("SELECT id, department_name, equipment_name FROM custom_equipment WHERE company_id = ? AND department_name = ? ORDER BY equipment_name ASC", (company_id, department_name))
    else:
        cursor.execute("SELECT id, department_name, equipment_name FROM custom_equipment WHERE company_id = ? ORDER BY department_name, equipment_name ASC", (company_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def add_custom_equipment(department_name, equipment_name, company_id='default'):
    if not department_name or not equipment_name or not equipment_name.strip():
        return False
    dept_name = department_name.strip()
    eq_name = equipment_name.strip()
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.datetime.now().isoformat()
    try:
        cursor.execute("INSERT OR IGNORE INTO custom_equipment (company_id, department_name, equipment_name, created_at) VALUES (?, ?, ?, ?)",
                       (company_id, dept_name, eq_name, now_str))
        conn.commit()
        cursor.execute("SELECT id FROM custom_equipment WHERE company_id = ? AND department_name = ? AND equipment_name = ?", (company_id, dept_name, eq_name))
        row = cursor.fetchone()
        eq_id = row['id'] if row else True
        conn.close()
        sync_to_supabase("custom_equipment", {"company_id": company_id, "department_name": dept_name, "equipment_name": eq_name, "created_at": now_str})
        return eq_id
    except Exception as e:
        conn.close()
        return False

def delete_custom_equipment(equipment_id, company_id='default'):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT department_name, equipment_name FROM custom_equipment WHERE id = ? AND company_id = ?", (equipment_id, company_id))
    row = cursor.fetchone()
    if row:
        dept_name = row['department_name']
        eq_name = row['equipment_name']
        cursor.execute("DELETE FROM custom_equipment WHERE id = ? AND company_id = ?", (equipment_id, company_id))
        conn.commit()
        delete_from_supabase("custom_equipment", {"department_name": f"eq.{dept_name}", "equipment_name": f"eq.{eq_name}", "company_id": f"eq.{company_id}"})
    conn.close()
    return True

def seed_default_plant_config(company_id='default'):
    """Seeds starter standard industry departments and equipment if empty."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM custom_departments WHERE company_id = ?", (company_id,))
    if cursor.fetchone()['cnt'] == 0:
        now_str = datetime.datetime.now().isoformat()
        defaults = {
            "Utility & Power": ["Main Transformer 33kVA", "Diesel Generator 500kVA", "Steam Boiler #1", "Air Compressor #1", "DM Water Treatment"],
            "Processing & Production": ["Reactor Vessel #1", "Mixing Blender #1", "Holding Tank #2", "Homogenizer Pump"],
            "Packaging & Bottling": ["Filling & Capping Machine", "Labeling Line #1", "Carton Sealer #2", "Conveyor Line #3"],
            "Plastics & Molding": ["Injection Molding Machine #1", "Blow Molding Machine", "UV Printing Line"],
            "General Facilities": ["HVAC Chiller", "Fire Hydrant Pump", "Effluent Treatment Plant (ETP)"]
        }
        for dept, items in defaults.items():
            cursor.execute("INSERT OR IGNORE INTO custom_departments (company_id, department_name, created_at) VALUES (?, ?, ?)", (company_id, dept, now_str))
            for eq in items:
                cursor.execute("INSERT OR IGNORE INTO custom_equipment (company_id, department_name, equipment_name, created_at) VALUES (?, ?, ?, ?)", (company_id, dept, eq, now_str))
        conn.commit()
    conn.close()

# --------------------------------------------------------------------
# USER AUTHENTICATION & ACCESS CONTROL FUNCTIONS
# --------------------------------------------------------------------

def seed_default_users(company_id='default'):
    """Seeds default demo Admin, Manager, and Operator credentials if empty."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM users WHERE company_id = ?", (company_id,))
    if cursor.fetchone()['cnt'] == 0:
        now_str = datetime.datetime.now().isoformat()
        default_users = [
            ("vinayak.gangan14@gmail.com", "Vinayak@123", "Admin"),
            ("admin@maintenance.com", "Admin@123", "Admin"),
            ("manager@maintenance.com", "Manager@123", "Manager"),
            ("john.operator@maintenance.com", "Operator@123", "Operator")
        ]
        for email, pwd, role in default_users:
            cursor.execute("INSERT OR IGNORE INTO users (company_id, email_or_name, password, role, created_at) VALUES (?, ?, ?, ?, ?)",
                           (company_id, email, pwd, role, now_str))
        conn.commit()
    conn.close()

def authenticate_user(email_or_name, password, role=None, company_id='default'):
    if not email_or_name or not password:
        return False, "Missing credentials"
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT id, email_or_name, role FROM users WHERE company_id = ? AND (LOWER(email_or_name) = LOWER(?) OR email_or_name = ?) AND password = ?"
    params = [company_id, email_or_name.strip(), email_or_name.strip(), password.strip()]
    if role:
        query += " AND role = ?"
        params.append(role)
        
    cursor.execute(query, tuple(params))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return dict(user), None
    return False, "Invalid email/username or password"

def get_company_users(company_id='default'):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, email_or_name, role, created_at FROM users WHERE company_id = ? ORDER BY role ASC, email_or_name ASC", (company_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def add_user(email_or_name, password, role, company_id='default'):
    if not email_or_name or not password or not role:
        return False, "Missing required user fields"
    if role not in ['Operator', 'Manager', 'Admin']:
        return False, "Invalid user role"
        
    email_clean = email_or_name.strip()
    pwd_clean = password.strip()
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.datetime.now().isoformat()
    try:
        cursor.execute("INSERT OR REPLACE INTO users (company_id, email_or_name, password, role, created_at) VALUES (?, ?, ?, ?, ?)",
                       (company_id, email_clean, pwd_clean, role, now_str))
        conn.commit()
        cursor.execute("SELECT id FROM users WHERE company_id = ? AND email_or_name = ?", (company_id, email_clean))
        row = cursor.fetchone()
        user_id = row['id'] if row else 1
        conn.close()
        user_dict = {"id": user_id, "company_id": company_id, "email_or_name": email_clean, "password": pwd_clean, "role": role, "created_at": now_str}
        sync_to_supabase("users", user_dict)
        return user_dict, None
    except Exception as e:
        conn.close()
        return False, str(e)

def delete_user(user_id, company_id='default'):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT email_or_name FROM users WHERE id = ? AND company_id = ?", (user_id, company_id))
    row = cursor.fetchone()
    if row:
        email = row['email_or_name']
        cursor.execute("DELETE FROM users WHERE id = ? AND company_id = ?", (user_id, company_id))
        conn.commit()
        delete_from_supabase("users", {"email_or_name": f"eq.{email}", "company_id": f"eq.{company_id}"})
    conn.close()
    return True

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
