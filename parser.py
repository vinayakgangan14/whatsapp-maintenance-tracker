import re
import database

def parse_whatsapp_message(text, sender_phone="", sender_name=""):
    """
    Parses incoming WhatsApp text and executes database operations.
    Returns: (response_text, action_type, details_dict)
    """
    cleaned_text = text.strip()
    lower_text = cleaned_text.lower()

    # 1. HELP / GREETING
    if lower_text in ["help", "commands", "hi", "hello", "?"] or lower_text.startswith("/help"):
        return get_help_message(), "HELP", {}

    # 2. STATUS / OPEN BREAKDOWNS
    if lower_text in ["status", "open", "active", "list", "/status"]:
        open_list = database.get_open_breakdowns()
        if not open_list:
            return "🟢 *System Status*: All equipment is operating normally! Zero active breakdowns reported.", "STATUS", {"count": 0}
        
        reply = f"🚨 *ACTIVE BREAKDOWNS ({len(open_list)})*:\n\n"
        for idx, item in enumerate(open_list, 1):
            dept_str = f"[{item['department']}] " if item.get('department') else ""
            reply += f"{idx}. *{item['ticket_number']}* | {dept_str}*{item['equipment_id']}*\n"
            reply += f"   ⚠️ Issue: {item['issue_description']}\n"
            reply += f"   🕒 Reported: {item['start_time'][:16].replace('T', ' ')}\n\n"
        reply += "💡 Reply with `FIX <Ticket or Equipment> - <Resolution details>` to close a breakdown."
        return reply, "STATUS", {"count": len(open_list)}

    # 3. SUMMARY / METRICS
    if lower_text in ["summary", "stats", "metrics", "dashboard", "/summary"]:
        stats = database.get_statistics()
        reply = (
            "📊 *MAINTENANCE PERFORMANCE SUMMARY*\n"
            "-----------------------------------\n"
            f"🔴 Open Breakdowns: *{stats['open_breakdowns']}*\n"
            f"✅ Resolved Breakdowns: *{stats['resolved_breakdowns']}*\n"
            f"⏳ Total Downtime: *{stats['total_downtime_hours']} hrs* ({stats['total_downtime_minutes']} mins)\n"
            f"⏱️ MTTR (Avg Repair Time): *{stats['mttr_minutes']} mins*\n"
            f"🔧 Preventive Maintenance Logs: *{stats['total_pm_logs']}*\n\n"
            "🏬 *Department Breakdown*:\n"
        )
        for dept, count in stats['department_distribution'].items():
            reply += f" • {dept}: {count} incident(s)\n"
        return reply, "SUMMARY", stats

    # 4. RESOLUTION / FIX COMMANDS
    # Matches: "FIX Machine #3 - replaced oil seal", "RESOLVED BD-202608-001 fixed pipe", "Machine 3 OK"
    fix_match = re.search(r'^(?:fix|fixed|resolved|resolve|ok|repaired|done)\s+(.+)', cleaned_text, re.IGNORECASE)
    if fix_match:
        content = fix_match.group(1).strip()
        # Check if department is specified like [Dept: Production] or Dept: Production
        dept, content_no_dept = extract_department(content)
        
        # Split equipment/ticket and resolution details by '-' or ':'
        parts = re.split(r'[-:]', content_no_dept, maxsplit=1)
        target = parts[0].strip()
        resolution = parts[1].strip() if len(parts) > 1 else "Repaired & verified operational"
        
        # If target looks like a ticket number or equipment name
        record, err = database.resolve_breakdown(
            ticket_number=target if target.upper().startswith("BD-") else None,
            equipment_id=target if not target.upper().startswith("BD-") else None,
            resolution_notes=resolution,
            technician=sender_name or "Technician",
            department=dept
        )
        
        if err:
            return f"⚠️ {err}\n\nType `STATUS` to list currently open breakdown ticket IDs.", "FIX_ERROR", {}
            
        hrs = record['duration_minutes'] // 60
        mins = record['duration_minutes'] % 60
        duration_str = f"{hrs}h {mins}m" if hrs > 0 else f"{mins} mins"
        
        reply = (
            f"✅ *BREAKDOWN RESOLVED & CLOSED*\n"
            f"-----------------------------------\n"
            f"🎫 *Ticket*: {record['ticket_number']}\n"
            f"🏬 *Department*: {record['department']}\n"
            f"🛠️ *Equipment*: {record['equipment_id']}\n"
            f"⏱️ *Total Downtime*: *{duration_str}*\n"
            f"🔧 *Resolution*: {record['resolution_notes']}\n"
            f"👨‍🔧 *Resolved By*: {record['technician']}\n\n"
            f"Logs updated in database & synced to Sheets!"
        )
        return reply, "FIX_SUCCESS", record

    # 5. PREVENTIVE MAINTENANCE LOG
    # Matches: "MAINT Pump 1 oil change", "PM [Production] Conveyor alignment done"
    pm_match = re.search(r'^(?:maint|maintenance|pm|service|serviced)\s+(.+)', cleaned_text, re.IGNORECASE)
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
        
        reply = (
            f"🛠️ *PREVENTIVE MAINTENANCE LOGGED*\n"
            f"-----------------------------------\n"
            f"🎫 *Ticket*: {ticket}\n"
            f"🏬 *Department*: {dept}\n"
            f"⚙️ *Equipment*: {eq_id}\n"
            f"📋 *Activity*: {activity}\n"
            f"👨‍🔧 *Logged By*: {sender_name or 'Tech'}"
        )
        return reply, "PM_SUCCESS", {"ticket": ticket, "equipment": eq_id}

    # 6. BREAKDOWN REPORT (DEFAULT IF INCLUDES BREAKDOWN KEYWORDS OR IS DIRECT REPORT)
    # Matches: "BREAKDOWN Compressor 2 leak", "BD Machine 1 stopped working", "Down HVAC Line 3"
    bd_match = re.search(r'^(?:breakdown|bd|down|fault|stop|error|issue)\s+(.+)', cleaned_text, re.IGNORECASE)
    if bd_match or any(k in lower_text for k in ["breakdown", "not working", "fault", "stopped", "overheating", "leak"]):
        body = bd_match.group(1).strip() if bd_match else cleaned_text
        dept, body_no_dept = extract_department(body)
        
        parts = re.split(r'[-:]', body_no_dept, maxsplit=1)
        eq_id = parts[0].strip()
        issue = parts[1].strip() if len(parts) > 1 else body_no_dept
        
        ticket, _ = database.log_breakdown(
            department=dept,
            equipment_id=eq_id,
            issue_description=issue,
            sender_phone=sender_phone,
            sender_name=sender_name
        )
        
        reply = (
            f"🚨 *BREAKDOWN REPORTED & LOGGED*\n"
            f"-----------------------------------\n"
            f"🎫 *Ticket ID*: *{ticket}*\n"
            f"🏬 *Department*: {dept}\n"
            f"⚙️ *Equipment*: *{eq_id}*\n"
            f"⚠️ *Issue*: {issue}\n"
            f"🕒 *Time Started*: {database.get_open_breakdowns()[0]['start_time'][:16].replace('T', ' ')}\n\n"
            f"📢 *Notification sent to Maintenance Team.* \n"
            f"Reply `FIX {eq_id} - <action>` when repair is complete."
        )
        return reply, "BD_SUCCESS", {"ticket": ticket, "equipment": eq_id}

    # Fallback response for unformatted text
    return (
        f"❓ *Unrecognized Message Format*\n\n"
        f"To report a breakdown, try:\n"
        f"👉 `BREAKDOWN [Dept] Equipment - Issue description`\n\n"
        f"To mark repaired, try:\n"
        f"👉 `FIX Equipment - Resolution details`\n\n"
        f"Send `HELP` for all available commands."
    ), "UNKNOWN", {}

def extract_department(text):
    """
    Extracts department tag if present, e.g. "[Dept: Production]" or "[Production]" or "Dept: Logistics"
    Returns (department_name, remaining_text)
    """
    # Check [Dept: XYZ] or [XYZ]
    bracket_match = re.search(r'\[(?:dept:\s*)?([^\]]+)\]', text, re.IGNORECASE)
    if bracket_match:
        dept = bracket_match.group(1).strip()
        remaining = text.replace(bracket_match.group(0), '').strip()
        return dept, remaining
        
    # Check Dept: XYZ -
    prefix_match = re.search(r'^(?:dept|department):\s*([^-:]+)[-:]', text, re.IGNORECASE)
    if prefix_match:
        dept = prefix_match.group(1).strip()
        remaining = text[prefix_match.end():].strip()
        return dept, remaining
        
    return "General", text

def get_help_message():
    return (
        "🤖 *WHATSAPP MAINTENANCE & BREAKDOWN AGENT*\n"
        "=========================================\n"
        "Send messages from any department to log & track repairs 24/7.\n\n"
        "📌 *COMMAND EXAMPLES*:\n\n"
        "1️⃣ *Report Breakdown*:\n"
        "   `BREAKDOWN [Production] CNC Machine #2 - Hydraulic oil leak`\n"
        "   `BD Boiler 1 - Overheating trip`\n\n"
        "2️⃣ *Mark Repaired & Log Duration*:\n"
        "   `FIX CNC Machine #2 - Replaced O-ring seal`\n"
        "   `RESOLVE BD-202608-001 - Reset thermal switch`\n\n"
        "3️⃣ *Log Routine Maintenance (PM)*:\n"
        "   `MAINT [Utilities] Air Compressor #3 - Filter change done`\n\n"
        "4️⃣ *Check Active Status*:\n"
        "   `STATUS` (Lists open breakdown tickets)\n\n"
        "5️⃣ *View Statistics & Downtime*:\n"
        "   `SUMMARY` (Shows total downtime & MTTR)\n"
    )
