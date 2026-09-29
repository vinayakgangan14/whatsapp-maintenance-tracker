import sqlite3
import datetime
import os
import json
import urllib.request
import urllib.parse
from config import DB_PATH, DEFAULT_CONFIG

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# --------------------------------------------------------------------
import uuid

def format_supabase_company_id(company_id):
    if not company_id or str(company_id).strip().lower() in ("default", "none", ""):
        return "00000000-0000-0000-0000-000000000000"
    clean_id = str(company_id).strip()
    try:
        uuid.UUID(clean_id)
        return clean_id
    except Exception:
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, clean_id))

def sync_to_supabase(table_name, record_dict):
    """
    Pushes/upserts a record into Supabase REST API if SUPABASE_URL & key are configured.
    Tries POST (insert) first; on HTTP 409 Conflict (duplicate record), executes PATCH (update).
    """
    supabase_url = (
        os.getenv("SUPABASE_URL") or
        get_setting("SUPABASE_URL", "") or
        DEFAULT_CONFIG.get("SUPABASE_URL", "")
    ).rstrip("/")
    supabase_key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY") or
        os.getenv("SUPABASE_ANON_KEY") or
        os.getenv("SUPABASE_KEY") or
        get_setting("SUPABASE_ANON_KEY", "") or
        DEFAULT_CONFIG.get("SUPABASE_ANON_KEY", "")
    )
    
    if not supabase_url or not supabase_key:
        return False, "Supabase environment variables not configured"

    try:
        payload = dict(record_dict)
        payload.pop("synced_to_sheets", None)
        payload.pop("id", None)
        
        comp = payload.get("company_id")
        payload["company_id"] = format_supabase_company_id(comp)
            
        data_bytes = json.dumps(payload).encode("utf-8")
        
        # Build query criteria for update (PATCH) check
        patch_query = None
        if "ticket_number" in payload and payload["ticket_number"]:
            patch_query = f"ticket_number=eq.{payload['ticket_number']}"
        elif table_name == "custom_departments" and "department_name" in payload:
            patch_query = f"department_name=eq.{urllib.parse.quote(str(payload['department_name']))}&company_id=eq.{payload['company_id']}"
        elif table_name == "custom_equipment" and "equipment_name" in payload:
            patch_query = f"equipment_name=eq.{urllib.parse.quote(str(payload['equipment_name']))}&company_id=eq.{payload['company_id']}"
        elif table_name == "users" and "email_or_name" in payload:
            patch_query = f"email_or_name=eq.{urllib.parse.quote(str(payload['email_or_name']))}&company_id=eq.{payload['company_id']}"
        elif table_name == "companies" and "company_name" in payload:
            patch_query = f"company_name=eq.{urllib.parse.quote(str(payload['company_name']))}"

        # 1. Try POST (insert)
        endpoint = f"{supabase_url}/rest/v1/{table_name}"
        req = urllib.request.Request(endpoint, data=data_bytes, method="POST")
        req.add_header("apikey", supabase_key)
        req.add_header("Authorization", f"Bearer {supabase_key}")
        req.add_header("Content-Type", "application/json")
        req.add_header("Prefer", "return=representation")
        
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                res_body = response.read().decode("utf-8")
                return True, res_body
        except urllib.error.HTTPError as err:
            # 2. If 409 Conflict (duplicate record), fall back to PATCH update
            if err.code == 409 and patch_query:
                patch_url = f"{supabase_url}/rest/v1/{table_name}?{patch_query}"
                p_req = urllib.request.Request(patch_url, data=data_bytes, method="PATCH")
                p_req.add_header("apikey", supabase_key)
                p_req.add_header("Authorization", f"Bearer {supabase_key}")
                p_req.add_header("Content-Type", "application/json")
                p_req.add_header("Prefer", "return=representation")
                with urllib.request.urlopen(p_req, timeout=5) as p_res:
                    return True, p_res.read().decode("utf-8")
            raise err
    except Exception as e:
        print(f"[Supabase Sync Error] Table '{table_name}': {e}")
        return False, str(e)


def delete_from_supabase(table_name, query_params):
    """
    Deletes record(s) from Supabase REST API matching query_params dict.
    """
    supabase_url = (
        os.getenv("SUPABASE_URL") or
        get_setting("SUPABASE_URL", "") or
        DEFAULT_CONFIG.get("SUPABASE_URL", "")
    ).rstrip("/")
    supabase_key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY") or
        os.getenv("SUPABASE_ANON_KEY") or
        os.getenv("SUPABASE_KEY") or
        get_setting("SUPABASE_ANON_KEY", "") or
        DEFAULT_CONFIG.get("SUPABASE_ANON_KEY", "")
    )
    
    if not supabase_url or not supabase_key:
        return False, "Supabase environment variables not configured"

    try:
        if "company_id" in query_params:
            comp_raw = query_params["company_id"]
            if comp_raw.startswith("eq."):
                cid = format_supabase_company_id(comp_raw[3:])
                query_params["company_id"] = f"eq.{cid}"

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


def fetch_from_supabase(table_name, select="*", order="id.desc", limit=100, company_id=None):
    """
    Fetches records directly from Supabase REST API as primary source of truth.
    """
    supabase_url = (
        os.getenv("SUPABASE_URL") or
        get_setting("SUPABASE_URL", "") or
        DEFAULT_CONFIG.get("SUPABASE_URL", "")
    ).rstrip("/")
    supabase_key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY") or
        os.getenv("SUPABASE_ANON_KEY") or
        os.getenv("SUPABASE_KEY") or
        get_setting("SUPABASE_ANON_KEY", "") or
        DEFAULT_CONFIG.get("SUPABASE_ANON_KEY", "")
    )
    
    if not supabase_url or not supabase_key:
        return None

    try:
        params = [f"select={select}"]
        if order:
            params.append(f"order={order}")
        if limit:
            params.append(f"limit={limit}")
        if company_id:
            cid = format_supabase_company_id(company_id)
            params.append(f"company_id=eq.{cid}")
            
        qs = "&".join(params)
        endpoint = f"{supabase_url}/rest/v1/{table_name}?{qs}"
        req = urllib.request.Request(endpoint, method="GET")
        req.add_header("apikey", supabase_key)
        req.add_header("Authorization", f"Bearer {supabase_key}")
        
        with urllib.request.urlopen(req, timeout=5) as response:
            res_body = response.read().decode("utf-8")
            data = json.loads(res_body)
            if isinstance(data, list):
                return data
            return None
    except Exception as e:
        print(f"[Supabase Fetch Error] Table '{table_name}': {e}")
        return None


import uuid

def get_or_create_company(company_name):
    if not company_name or not company_name.strip():
        company_name = "Default Workspace"
    clean_name = company_name.strip()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS companies (
            id TEXT PRIMARY KEY,
            company_name TEXT UNIQUE NOT NULL,
            industry TEXT DEFAULT 'Manufacturing',
            created_at TEXT NOT NULL
        )
    ''')
    conn.commit()
    
    cursor.execute("SELECT id, company_name FROM companies WHERE LOWER(company_name) = LOWER(?)", (clean_name,))
    row = cursor.fetchone()
    if row:
        conn.close()
        comp_id = row["id"]
        seed_default_users(comp_id)
        return {"id": comp_id, "company_name": row["company_name"]}
        
    comp_id = str(uuid.uuid4())
    now_str = datetime.datetime.now().isoformat()
    
    try:
        cursor.execute("INSERT INTO companies (id, company_name, industry, created_at) VALUES (?, ?, 'Manufacturing', ?)",
                       (comp_id, clean_name, now_str))
        conn.commit()
        conn.close()
        seed_default_users(comp_id)
        comp_dict = {"id": comp_id, "company_name": clean_name, "industry": "Manufacturing", "created_at": now_str}
        sync_to_supabase("companies", comp_dict)
        return comp_dict
    except Exception as e:
        conn.close()
        return {"id": "00000000-0000-0000-0000-000000000000", "company_name": clean_name}


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
                    
    # 2. If ticket_number was provided but not found in local SQLite, try searching Supabase
    if not record and ticket_number and str(ticket_number).strip():
        tn = str(ticket_number).strip()
        for tbl in ["breakdowns", "maintenance_logs", "welding_logs"]:
            sp_res = fetch_from_supabase(tbl, limit=50)
            if sp_res:
                matching = [r for r in sp_res if r.get('ticket_number') == tn and r.get('status') != 'RESOLVED']
                if matching:
                    record = matching[0]
                    target_table = tbl
                    break

    # 3. Fallback to searching by equipment_id ONLY if NO ticket_number was provided at all
    if not record and not ticket_number and equipment_id and str(equipment_id).strip():
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

        rec_id = rec_dict.get('id')
        rec_tn = rec_dict.get('ticket_number')
        if rec_id:
            cursor.execute('''
                UPDATE breakdowns 
                SET status = 'RESOLVED',
                    end_time = ?,
                    duration_minutes = ?,
                    resolution_notes = ?,
                    technician = ?,
                    synced_to_sheets = 0
                WHERE id = ? OR ticket_number = ?
            ''', (end_iso, duration_mins, resolution_notes, technician or rec_dict.get('sender_name') or 'Technician', rec_id, rec_tn))
        else:
            cursor.execute('''
                UPDATE breakdowns 
                SET status = 'RESOLVED',
                    end_time = ?,
                    duration_minutes = ?,
                    resolution_notes = ?,
                    technician = ?,
                    synced_to_sheets = 0
                WHERE ticket_number = ?
            ''', (end_iso, duration_mins, resolution_notes, technician or rec_dict.get('sender_name') or 'Technician', rec_tn))
        conn.commit()
        conn.close()
        rec_dict['status'] = 'RESOLVED'
        rec_dict['end_time'] = end_iso
        rec_dict['duration_minutes'] = duration_mins
        rec_dict['resolution_notes'] = resolution_notes
        rec_dict['technician'] = technician or rec_dict.get('sender_name') or 'Technician'
        sync_to_supabase("breakdowns", rec_dict)
        return rec_dict, None

    elif target_table == "maintenance_logs":
        rec_id = rec_dict.get('id')
        rec_tn = rec_dict.get('ticket_number')
        if rec_id:
            cursor.execute('''
                UPDATE maintenance_logs 
                SET status = 'RESOLVED',
                    technician = ?
                WHERE id = ? OR ticket_number = ?
            ''', (technician or rec_dict.get('technician') or 'Technician', rec_id, rec_tn))
        else:
            cursor.execute('''
                UPDATE maintenance_logs 
                SET status = 'RESOLVED',
                    technician = ?
                WHERE ticket_number = ?
            ''', (technician or rec_dict.get('technician') or 'Technician', rec_tn))
        conn.commit()
        conn.close()
        rec_dict['status'] = 'RESOLVED'
        rec_dict['technician'] = technician or rec_dict.get('technician') or 'Technician'
        sync_to_supabase("maintenance_logs", rec_dict)
        return rec_dict, None

    elif target_table == "welding_logs":
        rec_id = rec_dict.get('id')
        rec_tn = rec_dict.get('ticket_number')
        if rec_id:
            cursor.execute('''
                UPDATE welding_logs 
                SET status = 'RESOLVED',
                    technician = ?
                WHERE id = ? OR ticket_number = ?
            ''', (technician or rec_dict.get('sender_name') or 'Welder', rec_id, rec_tn))
        else:
            cursor.execute('''
                UPDATE welding_logs 
                SET status = 'RESOLVED',
                    technician = ?
                WHERE ticket_number = ?
            ''', (technician or rec_dict.get('sender_name') or 'Welder', rec_tn))
        conn.commit()
        conn.close()
        rec_dict['status'] = 'RESOLVED'
        rec_dict['technician'] = technician or rec_dict.get('sender_name') or 'Welder'
        sync_to_supabase("welding_logs", rec_dict)
        return rec_dict, None

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
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING_APPROVAL', ?, ?, ?)
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

def get_all_breakdowns(limit=100, company_id=None):
    sp_data = fetch_from_supabase("breakdowns", limit=limit, company_id=company_id)
    if sp_data is not None:
        return sp_data
    conn = get_db_connection()
    cursor = conn.cursor()
    if company_id:
        cid = "00000000-0000-0000-0000-000000000000" if company_id == "default" else company_id
        cursor.execute("SELECT * FROM breakdowns WHERE company_id = ? ORDER BY id DESC LIMIT ?", (cid, limit))
    else:
        cursor.execute("SELECT * FROM breakdowns ORDER BY id DESC LIMIT ?", (limit,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def get_all_maintenance(limit=100, company_id=None):
    sp_data = fetch_from_supabase("maintenance_logs", limit=limit, company_id=company_id)
    if sp_data is not None:
        return sp_data
    conn = get_db_connection()
    cursor = conn.cursor()
    if company_id:
        cid = "00000000-0000-0000-0000-000000000000" if company_id == "default" else company_id
        cursor.execute("SELECT * FROM maintenance_logs WHERE company_id = ? ORDER BY id DESC LIMIT ?", (cid, limit))
    else:
        cursor.execute("SELECT * FROM maintenance_logs ORDER BY id DESC LIMIT ?", (limit,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def get_all_welding(limit=100, company_id=None):
    sp_data = fetch_from_supabase("welding_logs", limit=limit, company_id=company_id)
    if sp_data is not None:
        return sp_data
    conn = get_db_connection()
    cursor = conn.cursor()
    if company_id:
        cid = "00000000-0000-0000-0000-000000000000" if company_id == "default" else company_id
        cursor.execute("SELECT * FROM welding_logs WHERE company_id = ? ORDER BY id DESC LIMIT ?", (cid, limit))
    else:
        cursor.execute("SELECT * FROM welding_logs ORDER BY id DESC LIMIT ?", (limit,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def get_statistics(company_id=None):
    bds = get_all_breakdowns(limit=500, company_id=company_id)
    pms = get_all_maintenance(limit=500, company_id=company_id)
    wds = get_all_welding(limit=500, company_id=company_id)

    total_bd = len(bds)
    open_bd = len([b for b in bds if b.get('status') not in ('RESOLVED', 'REJECTED')])
    pending_bd = len([b for b in bds if b.get('status') == 'PENDING_APPROVAL'])
    resolved_bd = len([b for b in bds if b.get('status') == 'RESOLVED'])
    
    sum_downtime = sum([int(b.get('duration_minutes') or 0) for b in bds if b.get('status') == 'RESOLVED'])
    
    total_pm = len(pms)
    total_wd = len(wds)
    open_wd = len([w for w in wds if w.get('status') not in ('RESOLVED', 'REJECTED')])
    
    mttr_minutes = round(sum_downtime / max(1, resolved_bd), 1) if resolved_bd > 0 else 0.0

    if total_bd == 0:
        mtbf_minutes = 0.0
        mtbf_hours = 0.0
    else:
        tracking_window_mins = 30 * 24 * 60.0
        operating_mins = max(1.0, tracking_window_mins - sum_downtime)
        mtbf_minutes = round(operating_mins / total_bd, 1)
        mtbf_hours = round(mtbf_minutes / 60.0, 1)

    dept_counts = {}
    for b in bds:
        dept = b.get('department') or 'General'
        dept_counts[dept] = dept_counts.get(dept, 0) + 1

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
