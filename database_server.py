"""
Persistent Python HTTP microservice wrapping all database.py functions.
Eliminates the need for child_process.spawn('python', ...) on every API call.
Uses ThreadingHTTPServer for concurrent request handling.
"""
import json
import os
import sys
import traceback
from http.server import BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from http.server import HTTPServer
from urllib.parse import urlparse, parse_qs

import database
from config import DEFAULT_CONFIG

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

class DatabaseHandler(BaseHTTPRequestHandler):
    """Handles all API routes by calling database.py functions directly."""

    def log_message(self, format, *args):
        """Suppress default access logs to reduce noise."""
        pass

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode('utf-8'))

    def do_OPTIONS(self):
        self._send_json({"status": "ok"})

    def _get_query_params(self):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        return parsed.path, query

    def _qp(self, query, name, default=None):
        """Get single query parameter value."""
        vals = query.get(name, [])
        return vals[0] if vals else default

    def _read_body(self):
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 0:
            raw = self.rfile.read(content_length).decode('utf-8')
            return json.loads(raw)
        return {}

    # ----------------------------------------------------------------
    # GET routes
    # ----------------------------------------------------------------
    def do_GET(self):
        try:
            path, query = self._get_query_params()
            cid = self._qp(query, 'company_id')  # company_id is a UUID string

            if path == '/health':
                return self._send_json({"status": "ok"})

            elif path == '/api/stats':
                result = database.get_statistics(company_id=cid)
                return self._send_json(result)

            elif path == '/api/breakdowns':
                result = database.get_all_breakdowns(company_id=cid)
                return self._send_json(result)

            elif path == '/api/maintenance':
                result = database.get_all_maintenance(company_id=cid)
                return self._send_json(result)

            elif path == '/api/welding':
                result = database.get_all_welding(company_id=cid)
                return self._send_json(result)

            elif path == '/api/config/departments':
                result = database.get_custom_departments(company_id=cid or 'default')
                return self._send_json(result)

            elif path == '/api/config/equipment':
                dept = self._qp(query, 'department')
                result = database.get_custom_equipment(department_name=dept or None, company_id=cid or 'default')
                return self._send_json(result)

            elif path == '/api/users':
                result = database.get_company_users(company_id=cid or 'default')
                return self._send_json(result)

            elif path == '/api/settings':
                has_creds = os.path.exists(os.path.join(os.path.dirname(__file__), 'service_account.json')) or bool(os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"))
                has_spreadsheet = bool(
                    os.getenv("GOOGLE_SPREADSHEET_ID")
                    or database.get_setting("GOOGLE_SPREADSHEET_ID")
                    or DEFAULT_CONFIG.get("GOOGLE_SPREADSHEET_ID")
                )
                result = {
                    "spreadsheet_id": os.getenv("GOOGLE_SPREADSHEET_ID") or database.get_setting("GOOGLE_SPREADSHEET_ID") or DEFAULT_CONFIG.get("GOOGLE_SPREADSHEET_ID", ""),
                    "sheet_name": os.getenv("GOOGLE_SHEET_NAME") or database.get_setting("GOOGLE_SHEET_NAME") or DEFAULT_CONFIG.get("GOOGLE_SHEET_NAME", "Maintenance_Logs"),
                    "has_google_credentials": has_creds,
                    "has_spreadsheet_configured": has_spreadsheet
                }
                return self._send_json(result)

            elif path == '/api/companies/check-admin':
                result = database.check_company_has_admin(company_id=cid or 'default')
                return self._send_json(result)

            else:
                return self._send_json({"error": "Not Found"}, 404)

        except Exception as e:
            sys.stderr.write(f"[DB-Server GET Error] {self.path}: {e}\n")
            traceback.print_exc(file=sys.stderr)
            return self._send_json({"error": str(e)}, 500)

    # ----------------------------------------------------------------
    # POST routes
    # ----------------------------------------------------------------
    def do_POST(self):
        try:
            path, _ = self._get_query_params()
            data = self._read_body()
            cid = data.get('company_id', 'default')

            if path == '/api/breakdowns/log':
                ticket, bd_id = database.log_breakdown(
                    department=data.get('department', 'General'),
                    equipment_id=data.get('equipment_id', ''),
                    issue_description=data.get('issue_description', ''),
                    sender_name=data.get('sender_name', 'Web Portal User'),
                    company_id=cid
                )
                return self._send_json({"ticket": ticket, "id": bd_id})

            elif path == '/api/pm/log':
                ticket = database.log_maintenance(
                    department=data.get('department', 'General'),
                    equipment_id=data.get('equipment_id', ''),
                    activity_description=data.get('activity_description', ''),
                    scheduled_time=data.get('scheduled_time', 'As Scheduled'),
                    technician=data.get('technician', 'Tech'),
                    company_id=cid
                )
                return self._send_json({"ticket": ticket})

            elif path == '/api/welding/log':
                ticket = database.log_welding(
                    department=data.get('department', 'General'),
                    equipment_id=data.get('equipment_id', ''),
                    location=data.get('department', 'General'),
                    welding_details=data.get('welding_details', ''),
                    scheduled_time=data.get('scheduled_time', 'Today'),
                    technician=data.get('technician', 'Welder'),
                    company_id=cid
                )
                return self._send_json({"ticket": ticket})

            elif path == '/api/ticket/approve':
                ok, msg = database.approve_ticket(
                    data.get('ticket_number', ''),
                    data.get('manager_name', 'Maintenance Manager')
                )
                return self._send_json({"ok": ok, "msg": msg})

            elif path == '/api/ticket/reject':
                ok, msg = database.reject_ticket(
                    data.get('ticket_number', ''),
                    data.get('manager_name', 'Maintenance Manager'),
                    data.get('reason', '')
                )
                return self._send_json({"ok": ok, "msg": msg})

            elif path == '/api/ticket/assign':
                ok, msg = database.assign_ticket(
                    data.get('ticket_number', ''),
                    data.get('assigned_to', 'Unassigned')
                )
                return self._send_json({"ok": ok, "msg": msg})

            elif path == '/api/breakdowns/resolve':
                updated, err = database.resolve_breakdown(
                    equipment_id=data.get('equipment_id'),
                    ticket_number=data.get('ticket_number'),
                    resolution_notes=data.get('resolution_notes', 'Fixed via dashboard'),
                    technician=data.get('technician', 'Technician'),
                    company_id=cid
                )
                if err:
                    return self._send_json({"updated": None, "err": err}, 400)
                return self._send_json({"updated": updated, "err": None})

            elif path == '/api/config/departments':
                result = database.add_custom_department(
                    data.get('department_name', ''),
                    company_id=cid
                )
                return self._send_json({"success": bool(result)})

            elif path == '/api/config/departments/delete':
                database.delete_custom_department(
                    int(data.get('id', 0)),
                    company_id=cid
                )
                return self._send_json({"success": True})

            elif path == '/api/config/equipment':
                result = database.add_custom_equipment(
                    data.get('department_name', ''),
                    data.get('equipment_name', ''),
                    company_id=cid
                )
                return self._send_json({"success": bool(result)})

            elif path == '/api/config/equipment/delete':
                database.delete_custom_equipment(
                    int(data.get('id', 0)),
                    company_id=cid
                )
                return self._send_json({"success": True})

            elif path == '/api/config/seed-template':
                database.seed_default_plant_config(company_id=cid)
                return self._send_json({"success": True})

            elif path == '/api/companies/register':
                result = database.get_or_create_company(
                    data.get('company_name', 'Default Workspace')
                )
                return self._send_json(result)

            elif path == '/api/auth/login':
                user, err = database.authenticate_user(
                    email_or_name=data.get('username', ''),
                    password=data.get('password', ''),
                    role=data.get('role', ''),
                    company_id=cid
                )
                if user:
                    return self._send_json({"success": True, "user": user})
                else:
                    return self._send_json({"success": False, "error": err or "Invalid credentials"})

            elif path == '/api/auth/register-admin':
                email_val = data.get('email_or_name') or data.get('username') or data.get('email') or ''
                pwd_val = data.get('password') or data.get('passcode') or ''
                user, err = database.add_user(
                    email_or_name=email_val,
                    password=pwd_val,
                    role='Admin',
                    company_id=cid
                )
                if user:
                    return self._send_json({"success": True, "user": user})
                else:
                    return self._send_json({"success": False, "error": err or "Registration failed"})

            elif path == '/api/users':
                email_val = data.get('email_or_name') or data.get('username') or data.get('email') or ''
                pwd_val = data.get('password') or data.get('passcode') or ''
                role_val = data.get('role', 'Operator')
                user, err = database.add_user(
                    email_or_name=email_val,
                    password=pwd_val,
                    role=role_val,
                    company_id=cid
                )
                if user:
                    return self._send_json({"success": True, "user": user})
                else:
                    return self._send_json({"success": False, "error": err or "Failed to create user"})

            elif path == '/api/users/delete':
                database.delete_user(
                    int(data.get('id', 0)),
                    company_id=cid
                )
                return self._send_json({"success": True})

            elif path == '/api/reset-database':
                database.clear_all_records()
                return self._send_json({"message": "Database cleared successfully"})

            elif path == '/api/supabase/sync-all':
                result = database.sync_all_to_supabase()
                return self._send_json(result)

            else:
                return self._send_json({"error": "Not Found"}, 404)

        except Exception as e:
            sys.stderr.write(f"[DB-Server POST Error] {self.path}: {e}\n")
            traceback.print_exc(file=sys.stderr)
            return self._send_json({"error": str(e)}, 500)

    # ----------------------------------------------------------------
    # DELETE routes (for departments/equipment/users)
    # ----------------------------------------------------------------
    def do_DELETE(self):
        try:
            path, query = self._get_query_params()
            cid = self._qp(query, 'company_id', 'default')

            # DELETE /api/config/departments/:id?company_id=X
            if path.startswith('/api/config/departments/'):
                dept_id = int(path.split('/')[-1])
                database.delete_custom_department(dept_id, company_id=cid)
                return self._send_json({"success": True})

            # DELETE /api/config/equipment/:id?company_id=X
            elif path.startswith('/api/config/equipment/'):
                eq_id = int(path.split('/')[-1])
                database.delete_custom_equipment(eq_id, company_id=cid)
                return self._send_json({"success": True})

            # DELETE /api/users/:id?company_id=X
            elif path.startswith('/api/users/'):
                user_id = int(path.split('/')[-1])
                database.delete_user(user_id, company_id=cid)
                return self._send_json({"success": True})

            else:
                return self._send_json({"error": "Not Found"}, 404)

        except Exception as e:
            sys.stderr.write(f"[DB-Server DELETE Error] {self.path}: {e}\n")
            traceback.print_exc(file=sys.stderr)
            return self._send_json({"error": str(e)}, 500)


def run():
    """Start the persistent Python database microservice."""
    # Initialize database tables ONCE
    database.init_db()

    port = 5555
    port_env = os.environ.get('PORT')
    if port_env:
        try:
            port = int(port_env) - 1000
            if port < 1024:
                port = 5555
        except ValueError:
            port = 5555

    server = ThreadingHTTPServer(('0.0.0.0', port), DatabaseHandler)
    print(f"🐍 Python Database Microservice running on port {port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
    print("🐍 Python Database Microservice stopped.")


if __name__ == '__main__':
    run()
