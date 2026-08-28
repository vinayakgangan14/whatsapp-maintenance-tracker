import os
import json
import logging
from config import CREDENTIALS_FILE, DEFAULT_CONFIG
import database

logger = logging.getLogger("google_sheets")

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def get_sheets_service():
    """Builds Google Sheets API service from env var JSON or local file."""
    env_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not env_json and not os.path.exists(CREDENTIALS_FILE):
        return None
    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build

        if env_json:
            info = json.loads(env_json)
            creds = Credentials.from_service_account_info(info, scopes=SCOPES)
        else:
            creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)

        service = build('sheets', 'v4', credentials=creds)
        return service
    except Exception as e:
        logger.error(f"Error initializing Google Sheets API: {e}")
        return None


def _get_spreadsheet_info():
    spreadsheet_id = (
        os.getenv("GOOGLE_SPREADSHEET_ID")
        or database.get_setting("GOOGLE_SPREADSHEET_ID")
        or DEFAULT_CONFIG.get("GOOGLE_SPREADSHEET_ID", "")
    )
    sheet_name = (
        os.getenv("GOOGLE_SHEET_NAME")
        or database.get_setting("GOOGLE_SHEET_NAME")
        or DEFAULT_CONFIG.get("GOOGLE_SHEET_NAME", "Maintenance_Logs")
    )
    return spreadsheet_id, sheet_name


def restore_database_from_sheets():
    """
    Restores SQLite database from Google Sheets every time the server starts.
    Uses INSERT OR REPLACE so existing rows are updated, not duplicated.
    """
    service = get_sheets_service()
    if not service:
        print("[Pure Bot Backup] No Google Sheets credentials - skipping restore.")
        return

    spreadsheet_id, sheet_name = _get_spreadsheet_info()
    if not spreadsheet_id:
        print("[Pure Bot Backup] No spreadsheet ID configured - skipping restore.")
        return

    try:
        range_name = f"{sheet_name}!A2:K"
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()

        rows = result.get('values', [])
        if not rows:
            print("[Pure Bot Backup] Google Sheets is empty - nothing to restore.")
            return

        conn = database.get_db_connection()
        cursor = conn.cursor()

        restored = 0
        for row in rows:
            # Pad to 11 columns
            while len(row) < 11:
                row.append('')

            ticket = row[0].strip()
            if not ticket:
                continue

            if ticket.startswith("BD-"):
                try:
                    duration = int(float(row[7])) if row[7] else 0
                except (ValueError, TypeError):
                    duration = 0

                end_time_val = row[6].strip() if row[6].strip() else None
                status_val = row[4].strip() if row[4].strip() else 'OPEN'

                cursor.execute('''
                    INSERT OR REPLACE INTO breakdowns
                    (ticket_number, department, equipment_id, issue_description,
                     status, start_time, end_time, duration_minutes,
                     resolution_notes, technician, created_at, synced_to_sheets)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                ''', (
                    ticket, row[1], row[2], row[3],
                    status_val, row[5], end_time_val, duration,
                    row[8], row[9], row[10]
                ))
                restored += 1

            elif ticket.startswith("PM-"):
                cursor.execute('''
                    INSERT OR REPLACE INTO maintenance_logs
                    (ticket_number, department, equipment_id, activity_description,
                     technician, performed_at, synced_to_sheets)
                    VALUES (?, ?, ?, ?, ?, ?, 1)
                ''', (ticket, row[1], row[2], row[3], row[9], row[10]))
                restored += 1

        conn.commit()
        conn.close()
        print(f"[Pure Bot Backup] ✅ Restored {restored} records from Google Sheets.")
    except Exception as e:
        logger.error(f"Error restoring database from Sheets: {e}")
        print(f"[Pure Bot Backup] Restore failed: {e}")


def sync_breakdown_to_sheet(breakdown_dict, spreadsheet_id=None, sheet_name=None):
    """
    Upsert a breakdown row in Google Sheets:
    - If a row with this ticket number exists, UPDATE it in-place.
    - Otherwise APPEND a new row.
    This ensures resolved status is reflected in the sheet immediately.
    """
    service = get_sheets_service()
    if not service:
        return False, "Google Sheets credentials not configured."

    sid, sname = _get_spreadsheet_info()
    spreadsheet_id = spreadsheet_id or sid
    sheet_name = sheet_name or sname

    if not spreadsheet_id:
        return False, "Google Spreadsheet ID not configured."

    ticket_number = breakdown_dict.get('ticket_number', '')

    # Build the row values
    row = [
        ticket_number,
        breakdown_dict.get('department', 'General'),
        breakdown_dict.get('equipment_id', ''),
        breakdown_dict.get('issue_description', ''),
        breakdown_dict.get('status', 'OPEN'),
        (breakdown_dict.get('start_time') or '')[:19].replace('T', ' '),
        (breakdown_dict.get('end_time') or '')[:19].replace('T', ' '),
        breakdown_dict.get('duration_minutes', 0),
        breakdown_dict.get('resolution_notes', ''),
        breakdown_dict.get('technician', '') or breakdown_dict.get('sender_name', ''),
        (breakdown_dict.get('created_at') or '')[:19].replace('T', ' ')
    ]

    try:
        # Find existing row in sheet by ticket number (column A)
        range_name = f"{sheet_name}!A:A"
        col_result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()

        col_values = col_result.get('values', [])
        existing_row_index = None  # 1-based row number in sheet
        for i, cell in enumerate(col_values):
            if cell and cell[0] == ticket_number:
                existing_row_index = i + 1  # Sheet rows are 1-indexed
                break

        if existing_row_index:
            # UPDATE existing row in-place
            update_range = f"{sheet_name}!A{existing_row_index}:K{existing_row_index}"
            service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=update_range,
                valueInputOption='USER_ENTERED',
                body={'values': [row]}
            ).execute()
        else:
            # APPEND new row
            service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=f"{sheet_name}!A:K",
                valueInputOption='USER_ENTERED',
                insertDataOption='INSERT_ROWS',
                body={'values': [row]}
            ).execute()

        # Mark as synced in local DB
        bd_id = breakdown_dict.get('id')
        if bd_id:
            conn = database.get_db_connection()
            conn.execute("UPDATE breakdowns SET synced_to_sheets = 1 WHERE id = ?", (bd_id,))
            conn.commit()
            conn.close()

        return True, "Synced to Google Sheets successfully."
    except Exception as e:
        logger.error(f"Google Sheets sync error: {e}")
        return False, str(e)


def sync_maintenance_to_sheet(maint_dict, spreadsheet_id=None, sheet_name=None):
    """Append a PM log row to Google Sheets."""
    service = get_sheets_service()
    if not service:
        return False, "Google Sheets credentials not configured."

    sid, sname = _get_spreadsheet_info()
    spreadsheet_id = spreadsheet_id or sid
    sheet_name = sheet_name or sname

    if not spreadsheet_id:
        return False, "Google Spreadsheet ID not configured."

    ticket = maint_dict.get('ticket_number', '')
    row = [
        ticket,
        maint_dict.get('department', 'General'),
        maint_dict.get('equipment_id', ''),
        maint_dict.get('activity_description', ''),
        'PM',
        (maint_dict.get('performed_at') or '')[:19].replace('T', ' '),
        '',  # end_time
        0,   # duration
        '',  # resolution_notes
        maint_dict.get('technician', '') or maint_dict.get('sender_name', ''),
        (maint_dict.get('performed_at') or '')[:19].replace('T', ' ')
    ]

    try:
        service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet_name}!A:K",
            valueInputOption='USER_ENTERED',
            insertDataOption='INSERT_ROWS',
            body={'values': [row]}
        ).execute()

        mid = maint_dict.get('id')
        if mid:
            conn = database.get_db_connection()
            conn.execute("UPDATE maintenance_logs SET synced_to_sheets = 1 WHERE id = ?", (mid,))
            conn.commit()
            conn.close()

        return True, "PM log synced to Google Sheets."
    except Exception as e:
        logger.error(f"PM sync error: {e}")
        return False, str(e)


def setup_sheet_headers(spreadsheet_id=None, sheet_name=None):
    """Ensures sheet headers exist (row 1)."""
    service = get_sheets_service()
    if not service:
        return False, "Credentials not configured."

    sid, sname = _get_spreadsheet_info()
    spreadsheet_id = spreadsheet_id or sid
    sheet_name = sheet_name or sname

    headers = [
        "Ticket Number", "Department", "Equipment ID", "Issue / Activity",
        "Status", "Start Time", "End Time", "Duration (Mins)",
        "Resolution Notes", "Technician / Reported By", "Logged At"
    ]

    try:
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet_name}!A1:K1",
            valueInputOption='USER_ENTERED',
            body={'values': [headers]}
        ).execute()
        return True, "Headers set up successfully."
    except Exception as e:
        return False, str(e)
