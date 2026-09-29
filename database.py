import sqlite3
import datetime
from config import DB_PATH

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Breakdowns table
    cursor.execute('''
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

    # Preventive Maintenance table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS maintenance_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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

    # Scheduled Welding Work table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS welding_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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

def log_breakdown(department, equipment_id, issue_description, sender_phone="", sender_name="", assigned_to="Unassigned"):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    ticket = generate_ticket_number("BD")
    now_str = datetime.datetime.now().isoformat()
    
    cursor.execute('''
        INSERT INTO breakdowns 
        (ticket_number, department, sender_phone, sender_name, equipment_id, issue_description, start_time, status, assigned_to, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING_APPROVAL', ?, ?)
    ''', (ticket, department, sender_phone, sender_name, equipment_id, issue_description, now_str, assigned_to or 'Unassigned', now_str))
    
    conn.commit()
    breakdown_id = cursor.lastrowid
    conn.close()
    return ticket, breakdown_id

def resolve_breakdown(equipment_id=None, ticket_number=None, resolution_notes="", technician="", department="General"):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Check in breakdowns table
    if ticket_number:
        cursor.execute("SELECT * FROM breakdowns WHERE ticket_number = ? AND status != 'RESOLVED'", (ticket_number,))
    elif equipment_id:
        cursor.execute("SELECT * FROM breakdowns WHERE equipment_id LIKE ? AND status != 'RESOLVED' ORDER BY id DESC LIMIT 1", (f"%{equipment_id}%",))
    else:
        conn.close()
        return None, "No equipment or ticket provided."
        
    record = cursor.fetchone()
    
    # 2. Check in maintenance_logs table if ticket_number starts with PM-
    if not record and ticket_number and ticket_number.startswith("PM-"):
        cursor.execute("SELECT * FROM maintenance_logs WHERE ticket_number = ? AND status != 'RESOLVED'", (ticket_number,))
        record = cursor.fetchone()
        if record:
            cursor.execute('''
                UPDATE maintenance_logs 
                SET status = 'RESOLVED',
                    technician = ?
                WHERE id = ?
            ''', (technician or record['technician'], record['id']))
            conn.commit()
            cursor.execute("SELECT * FROM maintenance_logs WHERE id = ?", (record['id'],))
            updated = cursor.fetchone()
            conn.close()
            return dict(updated), None

    # 3. Check in welding_logs table if ticket_number starts with WD-
    if not record and ticket_number and ticket_number.startswith("WD-"):
        cursor.execute("SELECT * FROM welding_logs WHERE ticket_number = ? AND status != 'RESOLVED'", (ticket_number,))
        record = cursor.fetchone()
        if record:
            cursor.execute('''
                UPDATE welding_logs 
                SET status = 'RESOLVED',
                    technician = ?
                WHERE id = ?
            ''', (technician or record['sender_name'], record['id']))
            conn.commit()
            cursor.execute("SELECT * FROM welding_logs WHERE id = ?", (record['id'],))
            updated = cursor.fetchone()
            conn.close()
            return dict(updated), None

    if not record:
        conn.close()
        return None, "No active open order found for this equipment/ticket."
        
    start_dt = datetime.datetime.fromisoformat(record['start_time'])
    end_dt = datetime.datetime.now()
    duration_mins = max(1, int((end_dt - start_dt).total_seconds() / 60))
    
    cursor.execute('''
        UPDATE breakdowns 
        SET status = 'RESOLVED',
            end_time = ?,
            duration_minutes = ?,
            resolution_notes = ?,
            technician = ?,
            synced_to_sheets = 0
        WHERE id = ?
    ''', (end_dt.isoformat(), duration_mins, resolution_notes, technician or record['sender_name'], record['id']))
    
    conn.commit()
    
    cursor.execute("SELECT * FROM breakdowns WHERE id = ?", (record['id'],))
    updated = cursor.fetchone()
    conn.close()
    return dict(updated), None

def log_maintenance(department, equipment_id, activity_description, scheduled_time="", technician="", sender_phone="", sender_name="", assigned_to="Unassigned"):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    ticket = generate_ticket_number("PM")
    now_str = datetime.datetime.now().isoformat()
    
    cursor.execute('''
        INSERT INTO maintenance_logs
        (ticket_number, department, sender_phone, sender_name, equipment_id, activity_description, scheduled_time, status, assigned_to, technician, performed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING_APPROVAL', ?, ?, ?)
    ''', (ticket, department, sender_phone, sender_name, equipment_id, activity_description, scheduled_time, assigned_to or 'Unassigned', technician or sender_name, now_str))
    
    conn.commit()
    conn.close()
    return ticket

def log_welding(department, equipment_id, location, welding_details, scheduled_time="", technician="", sender_phone="", sender_name="", assigned_to="Unassigned"):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    ticket = generate_ticket_number("WD")
    now_str = datetime.datetime.now().isoformat()
    
    cursor.execute('''
        INSERT INTO welding_logs
        (ticket_number, department, sender_phone, sender_name, equipment_id, location, welding_details, scheduled_time, status, assigned_to, technician, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDING_APPROVAL', ?, ?, ?)
    ''', (ticket, department, sender_phone, sender_name, equipment_id, location, welding_details, scheduled_time, assigned_to or 'Unassigned', technician or sender_name, now_str))
    
    conn.commit()
    conn.close()
    return ticket

def assign_ticket(ticket_number, assigned_to_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if ticket_number.startswith("BD-"):
        cursor.execute("UPDATE breakdowns SET assigned_to = ? WHERE ticket_number = ?", (assigned_to_name, ticket_number))
    elif ticket_number.startswith("PM-"):
        cursor.execute("UPDATE maintenance_logs SET assigned_to = ? WHERE ticket_number = ?", (assigned_to_name, ticket_number))
    elif ticket_number.startswith("WD-"):
        cursor.execute("UPDATE welding_logs SET assigned_to = ? WHERE ticket_number = ?", (assigned_to_name, ticket_number))
        
    conn.commit()
    conn.close()
    return True, f"Ticket {ticket_number} assigned to {assigned_to_name}."

def approve_ticket(ticket_number, manager_name="Maintenance Manager"):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if ticket_number.startswith("BD-"):
        cursor.execute("UPDATE breakdowns SET status = 'APPROVED' WHERE ticket_number = ?", (ticket_number,))
    elif ticket_number.startswith("PM-"):
        cursor.execute("UPDATE maintenance_logs SET status = 'APPROVED' WHERE ticket_number = ?", (ticket_number,))
    elif ticket_number.startswith("WD-"):
        cursor.execute("UPDATE welding_logs SET status = 'APPROVED' WHERE ticket_number = ?", (ticket_number,))
        
    conn.commit()
    conn.close()
    return True, "Ticket approved successfully."

def reject_ticket(ticket_number, manager_name="Maintenance Manager", reason=""):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    note = f"Rejected by {manager_name}" + (f": {reason}" if reason else "")
    if ticket_number.startswith("BD-"):
        cursor.execute("UPDATE breakdowns SET status = 'REJECTED', resolution_notes = ? WHERE ticket_number = ?", (note, ticket_number))
    elif ticket_number.startswith("PM-"):
        cursor.execute("UPDATE maintenance_logs SET status = 'REJECTED', activity_description = activity_description || ? WHERE ticket_number = ?", (f" [{note}]", ticket_number))
    elif ticket_number.startswith("WD-"):
        cursor.execute("UPDATE welding_logs SET status = 'REJECTED', welding_details = welding_details || ? WHERE ticket_number = ?", (f" [{note}]", ticket_number))
        
    conn.commit()
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
    
    # 1. MTTR (Mean Time To Repair in Minutes): Total Downtime / Resolved Breakdowns
    mttr_minutes = round(sum_downtime / max(1, resolved_bd), 1) if resolved_bd > 0 else 0.0

    # 2. MTBF (Mean Time Between Failures): Total Operating Time / Total Failures
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
        conn.close()
        return row['id'] if row else True
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
        conn.close()
        return row['id'] if row else True
    except Exception as e:
        conn.close()
        return False

def delete_custom_equipment(equipment_id, company_id='default'):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM custom_equipment WHERE id = ? AND company_id = ?", (equipment_id, company_id))
    conn.commit()
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
        cursor.execute("INSERT INTO users (company_id, email_or_name, password, role, created_at) VALUES (?, ?, ?, ?, ?)",
                       (company_id, email_clean, pwd_clean, role, now_str))
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return {"id": user_id, "email_or_name": email_clean, "role": role}, None
    except sqlite3.IntegrityError:
        conn.close()
        return False, "User email/username already exists"
    except Exception as e:
        conn.close()
        return False, str(e)

def delete_user(user_id, company_id='default'):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ? AND company_id = ?", (user_id, company_id))
    conn.commit()
    conn.close()
    return True

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
