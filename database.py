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

    conn.commit()
    conn.close()

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
    
    # 2. Check in welding_logs table if ticket_number starts with WD-
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
    
    mttr = round(sum_downtime / max(1, resolved_bd), 1) if resolved_bd > 0 else 0
    
    operating_hours = max(1, (30 * 24) - (sum_downtime / 60))
    mtbf_hours = round(operating_hours / max(1, total_bd), 1) if total_bd > 0 else round(30 * 24, 1)
    
    cursor.execute("SELECT department, COUNT(*) as count FROM breakdowns GROUP BY department")
    dept_counts = {row['department']: row['count'] for row in cursor.fetchall()}
    
    conn.close()
    return {
        "total_breakdowns": total_bd,
        "open_breakdowns": open_bd,
        "pending_breakdowns": pending_bd,
        "resolved_breakdowns": resolved_bd,
        "total_downtime_minutes": sum_downtime,
        "total_downtime_hours": round(sum_downtime / 60, 2),
        "mttr_minutes": mttr,
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

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
