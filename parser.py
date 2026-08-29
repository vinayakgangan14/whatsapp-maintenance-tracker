import re
import database

# Memory state to track interactive multi-step WhatsApp conversations per user phone
USER_STATES = {}

def parse_whatsapp_message(text, sender_phone="", sender_name=""):
    """
    Simplified & Interactive 1-6 Menu Parser for Pure Bot.
    
    1. Report Breakdown (BD-xxx)
    2. Schedule Preventive Maintenance (PM-xxx)
    3. Scheduled Welding Work (WD-xxx)
    4. Open Maintenance Orders
    5. Status & Downtime / MTTR / MTBF Stats
    6. Close Order (BD-xxx / PM-xxx / WD-xxx Fixed)
    """
    cleaned_text = text.strip()
    lower_text = cleaned_text.lower()
    user_key = sender_phone or "default_user"

    # Check if user has an active pending step in state
    current_state = USER_STATES.get(user_key)

    # 0. RESET / CANCEL STATE
    if lower_text in ["cancel", "reset", "stop", "0"]:
        if user_key in USER_STATES:
            del USER_STATES[user_key]
        return "🔄 Conversation reset. Send `MENU` or `1-6` to start.", "RESET", {}

    # 1. HELP / MENU / GREETINGS
    if lower_text in ["help", "commands", "hi", "hello", "menu", "?", "/help", "start"] and not current_state:
        return get_help_message(), "HELP", {}

    # ------------------------------------------------------------------
    # OPTION 4: OPEN MAINTENANCE ORDERS
    # ------------------------------------------------------------------
    if lower_text in ["4", "open", "orders", "active", "list", "/orders"]:
        if user_key in USER_STATES: del USER_STATES[user_key]
        open_bds = database.get_open_breakdowns()
        open_wds = database.get_open_welding()

        if not open_bds and not open_wds:
            return "🟢 *Pure Bot*: All equipment is operating normally! Zero active maintenance orders.", "STATUS", {"count": 0}

        reply = f"📌 *PURE BOT: OPEN MAINTENANCE ORDERS ({len(open_bds) + len(open_wds)})*\n"
        reply += "===================================\n"

        if open_bds:
            reply += "🚨 *ACTIVE BREAKDOWNS*:\n"
            for item in open_bds:
                dept_str = f"[{item['department']}] " if item.get('department') else ""
                reply += f"• *{item['ticket_number']}* | {dept_str}*{item['equipment_id']}*\n"
                reply += f"  ⚠️ Issue: {item['issue_description']}\n"
                reply += f"  🕒 Reported: {item['start_time'][:16].replace('T', ' ')}\n\n"

        if open_wds:
            reply += "🔥 *SCHEDULED WELDING JOBS*:\n"
            for item in open_wds:
                dept_str = f"[{item['department']}] " if item.get('department') else ""
                reply += f"• *{item['ticket_number']}* | {dept_str}*{item['equipment_id']}*\n"
                reply += f"  🔧 Welding: {item['welding_details']}\n"
                reply += f"  📍 Location: {item['location'] or 'Factory'}\n\n"

        reply += "💡 *To close an order*, reply:\n`BD-202608-001 Fixed` or `6 BD-202608-001 Fixed`"
        return reply, "OPEN_ORDERS", {"open_bds": len(open_bds), "open_wds": len(open_wds)}

    # ------------------------------------------------------------------
    # OPTION 5: SUMMARY & MTTR / MTBF STATS
    # ------------------------------------------------------------------
    if lower_text in ["5", "stats", "summary", "metrics", "mtbf", "mttr", "/stats"]:
        if user_key in USER_STATES: del USER_STATES[user_key]
        stats = database.get_statistics()
        reply = (
            "📊 *PURE BOT: MAINTENANCE METRICS*\n"
            "===================================\n"
            f"🔴 Open Breakdowns: *{stats['open_breakdowns']}*\n"
            f"✅ Resolved Tickets: *{stats['resolved_breakdowns']}*\n"
            f"⏳ Total Downtime: *{stats['total_downtime_hours']} hrs* ({stats['total_downtime_minutes']} mins)\n"
            f"⏱️ MTTR (Avg Repair Time): *{stats['mttr_minutes']} mins*\n"
            f"📈 MTBF (Mean Time Between Failures): *{stats['mtbf_hours']} hrs*\n"
            f"🔧 PM Service Logs: *{stats['total_pm_logs']}*\n"
            f"🔥 Welding Jobs: *{stats['total_welding_logs']}* (Open: {stats['open_welding_logs']})\n"
        )
        return reply, "SUMMARY", stats

    # ------------------------------------------------------------------
    # OPTION 6: CLOSE ORDER PROMPT OR DIRECT COMMAND
    # ------------------------------------------------------------------
    if lower_text == "6":
        USER_STATES[user_key] = "WAITING_CLOSE"
        return (
            "✅ *CLOSE OPEN MAINTENANCE ORDER*\n"
            "-----------------------------------\n"
            "Please reply with the Ticket Number or Equipment to close:\n\n"
            "Format: `BD-202608-001 Fixed` or `Press 3 Fixed`"
        ), "PROMPT_CLOSE", {}

    shortcut_fix = re.search(r'^(?:6|fix|fixed|resolved|resolve|ok|repaired|done)\s+(.+)', cleaned_text, re.IGNORECASE)
    natural_fix = re.search(r'(.+?)\s+(?:fixed|repaired|resolved|ok|working now)$', cleaned_text, re.IGNORECASE)
    
    if shortcut_fix or natural_fix or current_state == "WAITING_CLOSE":
        if user_key in USER_STATES: del USER_STATES[user_key]
        content = shortcut_fix.group(1).strip() if shortcut_fix else (natural_fix.group(1).strip() if natural_fix else cleaned_text)
        dept, content_no_dept = extract_department(content)
        
        parts = re.split(r'[-:]', content_no_dept, maxsplit=1)
        target = parts[0].strip()
        resolution = parts[1].strip() if len(parts) > 1 else "Fixed & verified operational"
        
        record, err = database.resolve_breakdown(
            ticket_number=target if (target.upper().startswith("BD-") or target.upper().startswith("WD-") or target.upper().startswith("PM-")) else None,
            equipment_id=target if not (target.upper().startswith("BD-") or target.upper().startswith("WD-") or target.upper().startswith("PM-")) else None,
            resolution_notes=resolution,
            technician=sender_name or "Maintenance Department",
            department=dept
        )
        
        if err:
            return f"⚠️ {err}\n\nSend `4` to view open maintenance order numbers.", "FIX_ERROR", {}
            
        _sync_breakdown(record)
        
        duration_str = f"{record.get('duration_minutes', 0)} mins"
        if record.get('duration_minutes', 0) >= 60:
            hrs = record['duration_minutes'] // 60
            mins = record['duration_minutes'] % 60
            duration_str = f"{hrs}h {mins}m"

        reply = (
            f"✅ *PURE BOT: ORDER CLOSED*\n"
            f"-----------------------------------\n"
            f"🎫 *Ticket*: {record['ticket_number']}\n"
            f"🛠️ *Equipment*: {record['equipment_id']}\n"
            f"⏱️ *Downtime*: *{duration_str}*\n"
            f"🔧 *Resolution*: {record.get('resolution_notes', 'Resolved')}\n"
            f"👨‍🔧 *Closed By*: {record.get('technician', sender_name or 'Tech')}\n\n"
            f"✅ Google Sheet & Dashboard updated!"
        )
        return reply, "FIX_SUCCESS", record

    # ------------------------------------------------------------------
    # OPTION 1: REPORT BREAKDOWN
    # ------------------------------------------------------------------
    if lower_text == "1":
        USER_STATES[user_key] = "WAITING_BD"
        return (
            "🚨 *REPORT BREAKDOWN*\n"
            "-----------------------------------\n"
            "Please reply with breakdown details in format:\n"
            "`Equipment Details | Location | Issue Description`\n\n"
            "Example:\n`Press 3 | Production Line A | Hydraulic Oil Leak`"
        ), "PROMPT_BD", {}

    bd_match = re.search(r'^(?:1|breakdown|bd|down|fault)\s+(.+)', cleaned_text, re.IGNORECASE)
    if bd_match or current_state == "WAITING_BD":
        if user_key in USER_STATES: del USER_STATES[user_key]
        body = bd_match.group(1).strip() if bd_match else cleaned_text
        
        parts = [p.strip() for p in body.split('|')]
        if len(parts) >= 3:
            eq_id, location, issue = parts[0], parts[1], parts[2]
            dept = location
        elif len(parts) == 2:
            eq_id, issue = parts[0], parts[1]
            dept = "General"
        else:
            dept, body_no_dept = extract_department(body)
            sub_parts = re.split(r'[-:]', body_no_dept, maxsplit=1)
            eq_id = sub_parts[0].strip()
            issue = sub_parts[1].strip() if len(sub_parts) > 1 else body_no_dept

        ticket, bd_id = database.log_breakdown(
            department=dept,
            equipment_id=eq_id,
            issue_description=issue,
            sender_phone=sender_phone,
            sender_name=sender_name
        )

        open_bds = database.get_open_breakdowns()
        matching = [b for b in open_bds if b['ticket_number'] == ticket]
        if matching: _sync_breakdown(matching[0])

        reply = (
            f"🚨 *PURE BOT: BREAKDOWN LOGGED*\n"
            f"-----------------------------------\n"
            f"🎫 *Ticket*: *{ticket}*\n"
            f"⚙️ *Equipment*: *{eq_id}*\n"
            f"📍 *Location/Dept*: {dept}\n"
            f"⚠️ *Issue*: {issue}\n"
            f"🕒 *Started*: {datetime_now_str()}\n\n"
            f"To close when repaired, reply:\n`{ticket} Fixed` or `2 {eq_id} Fixed`"
        )
        return reply, "BD_SUCCESS", {"ticket": ticket, "equipment": eq_id}

    # ------------------------------------------------------------------
    # OPTION 2: SCHEDULE PREVENTIVE MAINTENANCE
    # ------------------------------------------------------------------
    if lower_text == "2":
        USER_STATES[user_key] = "WAITING_PM"
        return (
            "📅 *SCHEDULE PREVENTIVE MAINTENANCE*\n"
            "-----------------------------------\n"
            "Please reply with PM details in format:\n"
            "`Equipment | Location | Description | Scheduled Time`\n\n"
            "Example:\n`Air Compressor #2 | Utilities | Filter Change | Tomorrow 10 AM`"
        ), "PROMPT_PM", {}

    pm_match = re.search(r'^(?:2|maint|pm|service)\s+(.+)', cleaned_text, re.IGNORECASE)
    if pm_match or current_state == "WAITING_PM":
        if user_key in USER_STATES: del USER_STATES[user_key]
        body = pm_match.group(1).strip() if pm_match else cleaned_text
        
        parts = [p.strip() for p in body.split('|')]
        if len(parts) >= 4:
            eq_id, location, activity, sched_time = parts[0], parts[1], parts[2], parts[3]
            dept = location
        elif len(parts) >= 3:
            eq_id, location, activity = parts[0], parts[1], parts[2]
            sched_time = "As Scheduled"
            dept = location
        else:
            dept, body_no_dept = extract_department(body)
            sub_parts = re.split(r'[-:]', body_no_dept, maxsplit=1)
            eq_id = sub_parts[0].strip()
            activity = sub_parts[1].strip() if len(sub_parts) > 1 else body_no_dept
            sched_time = "Routine"

        ticket = database.log_maintenance(
            department=dept,
            equipment_id=eq_id,
            activity_description=activity,
            scheduled_time=sched_time,
            technician=sender_name or "Maintenance Tech",
            sender_phone=sender_phone,
            sender_name=sender_name
        )

        _sync_maintenance(ticket)

        reply = (
            f"📅 *PURE BOT: PREVENTIVE MAINTENANCE LOGGED*\n"
            f"-----------------------------------\n"
            f"🎫 *Ticket*: *{ticket}*\n"
            f"⚙️ *Equipment*: {eq_id}\n"
            f"📍 *Location*: {dept}\n"
            f"📋 *Service*: {activity}\n"
            f"🕒 *Scheduled*: {sched_time}\n"
            f"👨‍🔧 *Logged By*: {sender_name or 'Tech'}"
        )
        return reply, "PM_SUCCESS", {"ticket": ticket, "equipment": eq_id}

    # ------------------------------------------------------------------
    # OPTION 3: SCHEDULED WELDING WORK
    # ------------------------------------------------------------------
    if lower_text == "3":
        USER_STATES[user_key] = "WAITING_WD"
        return (
            "🔥 *SCHEDULED WELDING WORK*\n"
            "-----------------------------------\n"
            "Please reply with Welding Work details in format:\n"
            "`Equipment/Structure | Location | Welding Details | Scheduled Time`\n\n"
            "Example:\n`Conveyor Belt Frame | Line B | Guard Rail Welding | 3 PM Today`"
        ), "PROMPT_WD", {}

    wd_match = re.search(r'^(?:3|weld|welding|wd)\s+(.+)', cleaned_text, re.IGNORECASE)
    if wd_match or current_state == "WAITING_WD":
        if user_key in USER_STATES: del USER_STATES[user_key]
        body = wd_match.group(1).strip() if wd_match else cleaned_text
        
        parts = [p.strip() for p in body.split('|')]
        if len(parts) >= 4:
            eq_id, location, details, sched_time = parts[0], parts[1], parts[2], parts[3]
            dept = location
        elif len(parts) >= 3:
            eq_id, location, details = parts[0], parts[1], parts[2]
            sched_time = "As Scheduled"
            dept = location
        else:
            dept, body_no_dept = extract_department(body)
            sub_parts = re.split(r'[-:]', body_no_dept, maxsplit=1)
            eq_id = sub_parts[0].strip()
            details = sub_parts[1].strip() if len(sub_parts) > 1 else body_no_dept
            location = dept
            sched_time = "Today"

        ticket = database.log_welding(
            department=dept,
            equipment_id=eq_id,
            location=location,
            welding_details=details,
            scheduled_time=sched_time,
            technician=sender_name or "Welding Team",
            sender_phone=sender_phone,
            sender_name=sender_name
        )

        reply = (
            f"🔥 *PURE BOT: WELDING WORK SCHEDULED*\n"
            f"-----------------------------------\n"
            f"🎫 *Ticket*: *{ticket}*\n"
            f"🏗️ *Structure/Equipment*: {eq_id}\n"
            f"📍 *Location*: {location}\n"
            f"⚡ *Welding Task*: {details}\n"
            f"🕒 *Scheduled Time*: {sched_time}\n"
            f"👨‍🔧 *Scheduled By*: {sender_name or 'Tech'}"
        )
        return reply, "WD_SUCCESS", {"ticket": ticket, "equipment": eq_id}

    # Fallback to Menu
    return get_help_message(), "UNKNOWN", {}

def datetime_now_str():
    import datetime
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

def _sync_breakdown(record):
    try:
        import google_sheets
        google_sheets.sync_breakdown_to_sheet(record)
    except Exception as e:
        print(f"[Pure Bot] Sheets sync error: {e}")

def _sync_maintenance(ticket):
    try:
        import google_sheets
        import database as db
        conn = db.get_db_connection()
        row = conn.execute("SELECT * FROM maintenance_logs WHERE ticket_number = ?", (ticket,)).fetchone()
        conn.close()
        if row: google_sheets.sync_maintenance_to_sheet(dict(row))
    except Exception as e:
        print(f"[Pure Bot] PM Sheets sync error: {e}")

def extract_department(text):
    bracket_match = re.search(r'\[(?:dept:\s*)?([^\]]+)\]', text, re.IGNORECASE)
    if bracket_match:
        dept = bracket_match.group(1).strip()
        remaining = text.replace(bracket_match.group(0), '').strip()
        return dept, remaining
    return "General", text

def get_help_message():
    return (
        "🤖 *PURE BOT FOR MAINTENANCE & REPAIR*\n"
        "===================================\n"
        "Please reply with a number (1-6):\n\n"
        "1️⃣ *Report Breakdown*\n"
        "2️⃣ *Schedule Preventive Maintenance*\n"
        "3️⃣ *Scheduled Welding Work*\n"
        "4️⃣ *Open Maintenance Orders*\n"
        "5️⃣ *Status & MTTR / MTBF Stats*\n"
        "6️⃣ *Close Order (e.g. BD-202608-001 Fixed)*"
    )
