import os
import json
import logging
from config import CREDENTIALS_FILE, DEFAULT_CONFIG
import database

logger = logging.getLogger("google_sheets")

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def get_sheets_service():
    """Builds Google Sheets API service if credentials exist in env var or file."""
    env_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not env_json and not os.path.exists(CREDENTIALS_FILE):
        return None
    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
        
        if env_json:
            # Parse service account JSON from environment variable
            info = json.loads(env_json)
            creds = Credentials.from_service_account_info(info, scopes=SCOPES)
        else:
            creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
            
        service = build('sheets', 'v4', credentials=creds)
        return service
    except Exception as e:
        logger.error(f"Error initializing Google Sheets API: {e}")
        return None

def restore_database_from_sheets():
    """Restores SQLite database entries from Google Sheets on startup if DB is empty."""
    service = get_sheets_service()
    if not service:
        return
        
    spreadsheet_id = database.get_setting("GOOGLE_SPREADSHEET_ID") or DEFAULT_CONFIG["GOOGLE_SPREADSHEET_ID"]
    sheet_name = database.get_setting("GOOGLE_SHEET_NAME") or DEFAULT_CONFIG["GOOGLE_SHEET_NAME"]
    
    if not spreadsheet_id:
        return
        
    try:
        range_name = f"{sheet_name}!A2:K"
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        
        rows = result.get('values', [])
        if not rows:
            return
            
        conn = database.get_db_connection()
        cursor = conn.cursor()
        
        # Only restore if database is empty
        cursor.execute("SELECT COUNT(*) as count FROM breakdowns")
        if cursor.fetchone()['count'] > 0:
            conn.close()
            return
            
        for row in rows:
            # Ensure row has at least 11 columns
            while len(row) < 11:
                row.append('')
                
            ticket = row[0]
            if not ticket:
                continue
                
            if ticket.startswith("BD-"):
                try:
                    duration = int(row[7])
                except ValueError:
                    duration = 0
                cursor.execute('''
                    INSERT OR REPLACE INTO breakdowns 
                    (ticket_number, department, equipment_id, issue_description, status, start_time, end_time, duration_minutes, resolution_notes, technician, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (row[0], row[1], row[2], row[3], row[4], row[5], row[6], duration, row[8], row[9], row[10]))
            elif ticket.startswith("PM-"):
                cursor.execute('''
                    INSERT OR REPLACE INTO maintenance_logs
                    (ticket_number, department, equipment_id, activity_description, technician, performed_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (row[0], row[1], row[2], row[3], row[9], row[10]))
                
        conn.commit()
        conn.close()
        print(f"[Pure Bot Backup] Successfully restored {len(rows)} entries from Google Sheets.")
    except Exception as e:
        logger.error(f"Error restoring database from Sheets: {e}")

def sync_breakdown_to_sheet(breakdown_dict, spreadsheet_id=None, sheet_name=None):
    """Appends a breakdown log row to Google Sheets."""
    service = get_sheets_service()
    if not service:
        return False, "Google Sheets Credentials file (service_account.json) missing or invalid."

    spreadsheet_id = spreadsheet_id or database.get_setting("GOOGLE_SPREADSHEET_ID") or DEFAULT_CONFIG["GOOGLE_SPREADSHEET_ID"]
    sheet_name = sheet_name or database.get_setting("GOOGLE_SHEET_NAME") or DEFAULT_CONFIG["GOOGLE_SHEET_NAME"]

    if not spreadsheet_id:
        return False, "Google Spreadsheet ID not configured."

    try:
        # Prepare row data
        row = [
            breakdown_dict.get('ticket_number', ''),
            breakdown_dict.get('department', 'General'),
            breakdown_dict.get('equipment_id', ''),
            breakdown_dict.get('issue_description', ''),
            breakdown_dict.get('status', 'OPEN'),
            breakdown_dict.get('start_time', '')[:19].replace('T', ' '),
            (breakdown_dict.get('end_time') or '')[:19].replace('T', ' '),
            breakdown_dict.get('duration_minutes', 0),
            breakdown_dict.get('resolution_notes', ''),
            breakdown_dict.get('technician', '') or breakdown_dict.get('sender_name', ''),
            breakdown_dict.get('created_at', '')[:19].replace('T', ' ')
        ]

        range_name = f"{sheet_name}!A:K"
        body = {'values': [row]}

        result = service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption='USER_ENTERED',
            insertDataOption='INSERT_ROWS',
            body=body
        ).execute()

        # Update DB sync flag
        if breakdown_dict.get('id'):
            conn = database.get_db_connection()
            conn.execute("UPDATE breakdowns SET synced_to_sheets = 1 WHERE id = ?", (breakdown_dict['id'],))
            conn.commit()
            conn.close()

        return True, "Synced to Google Sheets successfully."
    except Exception as e:
        logger.error(f"Google Sheets sync error: {e}")
        return False, str(e)

def setup_sheet_headers(spreadsheet_id, sheet_name="Maintenance_Logs"):
    """Ensures sheet headers exist."""
    service = get_sheets_service()
    if not service:
        return False, "Credentials not configured."

    headers = [
        "Ticket Number", "Department", "Equipment ID", "Issue / Activity", 
        "Status", "Start Time", "End Time", "Duration (Mins)", 
        "Resolution Notes", "Technician / Reported By", "Logged At"
    ]

    try:
        range_name = f"{sheet_name}!A1:K1"
        body = {'values': [headers]}
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption='USER_ENTERED',
            body=body
        ).execute()
        return True, "Headers set up successfully."
    except Exception as e:
        return False, str(e)
