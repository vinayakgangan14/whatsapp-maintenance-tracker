import re
import database

def parse_whatsapp_message(text, sender_phone="", sender_name=""):
    """
    Super-simplified parser for Pure Bot for Maintenance and Repair.
    Supports single-digit shortcuts (1, 2, 3, 4, 5) and simple phrases.
    Always syncs to Google Sheets after every log/resolve action.
    """
    cleaned_text = text.strip()
    lower_text = cleaned_text.lower()

    # 1. HELP / MENU / GREETINGS
    if lower_text in ["help", "commands", "hi", "hello", "menu", "?", "0", "/help"]:
        return get_help_message(), "HELP", {}

    # 2. STATUS / OPEN BREAKDOWNS (Shortcut: 4 or "open" or "status")
    if lower_text in ["4", "open", "status", "active", "list", "/status"]:
        open_list = database.get_open_breakdowns()
        if not open_list:
            return "🟢 *Pure Bot*: All equipment is operating normally! Zero active breakdowns reported.", "STATUS", {"count": 0}

        reply = f"🚨 *PURE BOT: ACTIVE BREAKDOWNS ({len(open_list)})*\n"
        reply += "-----------------------------------\n"
        for idx, item in enumerate(open_list, 1):
            dept_str = f"[{item['department']}] " if item.get('department') else ""
            reply += f"{idx}. *{item['ticket_number']}* | {dept_str}*{item['equipment_id']}*\n"
            reply += f"   ⚠️ Issue: {item['issue_description']}\n"
            reply += f"   🕒 Reported: {item['start_time'][:16].replace('T', ' ')}\n\n"
        reply += "💡 Reply `2 <Equipment> Fixed` to close a breakdown."
        return reply, "STATUS", {"count": len(open_list)}

    # 3. SUMMARY / METRICS (Shortcut: 5 or "stats" or "summary")
    if lower_text in ["5", "stats", "summary", "metrics", "/summary"]:
        stats = database.get_statistics()
        reply = (
            "📊 *PURE BOT: MAINTENANCE SUMMARY*\n"
            "-----------------------------------\n"
            f"🔴 Open Breakdowns: *{stats['open_breakdowns']}*\n"
            f"✅ Resolved Tickets: *{stats['resolved_breakdowns']}*\n"
            f"⏳ Total Downtime: *{stats['total_downtime_hours']} hrs* ({stats['total_downtime_minutes']} mins)\n"
            f"⏱️ MTTR (Avg Repair Time): *{stats['mttr_minutes']} mins*\n"
            f"🔧 PM Service Logs: *{stats['total_pm_logs']}*\n"
        )
        return reply, "SUMMARY", stats

    # 4. RESOLUTION / FIX COMMANDS (Shortcut: 2 <Equipment> <Notes> or "Fixed <Equipment>")
    shortcut_fix = re.search(r'^(?:2|fix|fixed|resolved|resolve|ok|repaired|done)\s+(.+)', cleaned_text, re.IGNORECASE)
    natural_fix = re.search(r'(.+?)\s+(?:fixed|repaired|resolved|ok|working now)$', cleaned_text, re.IGNORECASE)

    if shortcut_fix or natural_fix:
        content = shortcut_fix.group(1).strip() if shortcut_fix else natural_fix.group(1).strip()
        dept, content_no_dept = extract_department(content)

        parts = re.split(r'[-:]', content_no_dept, maxsplit=1)
        target = parts[0].strip()
        resolution = parts[1].strip() if len(parts) > 1 else "Repaired & verified operational"

        record, err = database.resolve_breakdown(
            ticket_number=target if target.upper().startswith("BD-") else None,
            equipment_id=target if not target.upper().startswith("BD-") else None,
            resolution_notes=resolution,
            technician=sender_name or "Technician",
            department=dept
        )

        if err:
            return f"⚠️ {err}\n\nType `4` or `OPEN` to view open breakdown tickets.", "FIX_ERROR", {}

        # ✅ Sync to Google Sheets immediately
        _sync_breakdown(record)

        hrs = record['duration_minutes'] // 60
        mins = record['duration_minutes'] % 60
        duration_str = f"{hrs}h {mins}m" if hrs > 0 else f"{mins} mins"

        reply = (
            f"✅ *PURE BOT: REPAIR COMPLETED*\n"
            f"-----------------------------------\n"
            f"🎫 *Ticket*: {record['ticket_number']}\n"
            f"🛠️ *Equipment*: {record['equipment_id']}\n"
            f"⏱️ *Downtime*: *{duration_str}*\n"
            f"🔧 *Action*: {record['resolution_notes']}\n"
            f"👨‍🔧 *Resolved By*: {record['technician']}\n\n"
            f"✅ Google Sheet & Dashboard updated!"
        )
        return reply, "FIX_SUCCESS", record

    # 5. PREVENTIVE MAINTENANCE LOG (Shortcut: 3 <Equipment> <Service>)
    pm_match = re.search(r'^(?:3|maint|maintenance|pm|service|serviced)\s+(.+)', cleaned_text, re.IGNORECASE)
    if pm_match:
        content = pm_match.group(1).strip()
        dept, content_no_dept = extract_department(content)

        parts = re.split(r'[-:]', content_no_dept, maxsplit=1)
        eq_id = parts[0].strip()
        activity = parts[1].strip() if len(parts) > 1 else "Routine maintenance completed"

        ticket = database.log_maintenance(
            department=dept,
            equipment_id=eq_id,
            activity_description=activity,
            technician=sender_name or "Maintenance Tech",
            sender_phone=sender_phone,
            sender_name=sender_name
        )

        # ✅ Sync PM log to Google Sheets immediately
        _sync_maintenance(ticket)

        reply = (
            f"🛠️ *PURE BOT: SERVICE LOGGED*\n"
            f"-----------------------------------\n"
            f"🎫 *Ticket*: {ticket}\n"
            f"⚙️ *Equipment*: {eq_id}\n"
            f"📋 *Service*: {activity}\n"
            f"👨‍🔧 *Tech*: {sender_name or 'Tech'}\n\n"
            f"✅ Google Sheet updated!"
        )
        return reply, "PM_SUCCESS", {"ticket": ticket, "equipment": eq_id}

    # 6. BREAKDOWN REPORT (Shortcut: 1 <Equipment> <Issue>)
    bd_match = re.search(r'^(?:1|breakdown|bd|down|fault|stop|error|issue)\s+(.+)', cleaned_text, re.IGNORECASE)
    natural_bd = re.search(r'(.+?)\s+(?:not working|down|broken|stopped|faulty|overheating|leaking)$', cleaned_text, re.IGNORECASE)

    if bd_match or natural_bd or any(k in lower_text for k in ["breakdown", "not working", "fault", "stopped", "leak"]):
        body = bd_match.group(1).strip() if bd_match else (natural_bd.group(1).strip() if natural_bd else cleaned_text)
        dept, body_no_dept = extract_department(body)

        parts = re.split(r'[-:]', body_no_dept, maxsplit=1)
        eq_id = parts[0].strip()
        issue = parts[1].strip() if len(parts) > 1 else body_no_dept

        ticket, bd_id = database.log_breakdown(
            department=dept,
            equipment_id=eq_id,
            issue_description=issue,
            sender_phone=sender_phone,
            sender_name=sender_name
        )

        # ✅ Sync breakdown to Google Sheets immediately
        open_bds = database.get_open_breakdowns()
        matching = [b for b in open_bds if b['ticket_number'] == ticket]
        if matching:
            _sync_breakdown(matching[0])

        start_time_str = open_bds[0]['start_time'][:16].replace('T', ' ') if open_bds else ""

        reply = (
            f"🚨 *PURE BOT: BREAKDOWN LOGGED*\n"
            f"-----------------------------------\n"
            f"🎫 *Ticket*: *{ticket}*\n"
            f"⚙️ *Equipment*: *{eq_id}*\n"
            f"⚠️ *Issue*: {issue}\n"
            f"🕒 *Started*: {start_time_str}\n\n"
            f"Reply `2 {eq_id} Fixed` when repair is complete."
        )
        return reply, "BD_SUCCESS", {"ticket": ticket, "equipment": eq_id}

    # Fallback
    return (
        f"❓ *Pure Bot: Unrecognized Format*\n\n"
        f"Send `1` to report breakdown:\n"
        f"👉 `1 Press 3 Oil leak`\n\n"
        f"Send `2` to report repair done:\n"
        f"👉 `2 Press 3 Fixed`\n\n"
        f"Type `HELP` for all options."
    ), "UNKNOWN", {}


def _sync_breakdown(record):
    """Sync a breakdown record to Google Sheets silently (no crash on failure)."""
    try:
        import google_sheets
        google_sheets.sync_breakdown_to_sheet(record)
    except Exception as e:
        print(f"[Pure Bot] Google Sheets sync skipped: {e}")


def _sync_maintenance(ticket):
    """Fetch latest PM log by ticket and sync to Google Sheets."""
    try:
        import google_sheets
        import database as db
        conn = db.get_db_connection()
        row = conn.execute(
            "SELECT * FROM maintenance_logs WHERE ticket_number = ?", (ticket,)
        ).fetchone()
        conn.close()
        if row:
            google_sheets.sync_maintenance_to_sheet(dict(row))
    except Exception as e:
        print(f"[Pure Bot] PM Google Sheets sync skipped: {e}")


def extract_department(text):
    bracket_match = re.search(r'\[(?:dept:\s*)?([^\]]+)\]', text, re.IGNORECASE)
    if bracket_match:
        dept = bracket_match.group(1).strip()
        remaining = text.replace(bracket_match.group(0), '').strip()
        return dept, remaining

    prefix_match = re.search(r'^(?:dept|department):\s*([^-:]+)[-:]', text, re.IGNORECASE)
    if prefix_match:
        dept = prefix_match.group(1).strip()
        remaining = text[prefix_match.end():].strip()
        return dept, remaining

    return "General", text


def get_help_message():
    return (
        "🤖 *PURE BOT FOR MAINTENANCE AND REPAIR*\n"
        "=======================================\n"
        "Simple 1-Touch Commands for All Departments:\n\n"
        "1️⃣ *Report Breakdown*:\n"
        "   `1 Press 3 Leak`  (or: `Down Press 3`)\n\n"
        "2️⃣ *Report Repair Fixed*:\n"
        "   `2 Press 3 Fixed` (or: `Fixed Press 3`)\n\n"
        "3️⃣ *Log Routine Service*:\n"
        "   `3 Press 3 Oil Change`\n\n"
        "4️⃣ *View Open Tickets*:\n"
        "   Type `4` or `OPEN`\n\n"
        "5️⃣ *View Downtime Stats*:\n"
        "   Type `5` or `STATS`\n"
    )
