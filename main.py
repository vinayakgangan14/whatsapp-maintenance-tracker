import os
import json
from fastapi import FastAPI, Request, Response, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from pathlib import Path

import database
import whatsapp_engine
import google_sheets
import excel_generator
from config import BASE_DIR, CREDENTIALS_FILE, DEFAULT_CONFIG

# Initialize SQLite tables on startup
database.init_db()

app = FastAPI(
    title="WhatsApp Maintenance & Breakdown Tracking Agent",
    description="24/7 Automated WhatsApp Bot & Management Dashboard with Google Sheets & Excel Sync",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ---------------------------------------------------------
# META WHATSAPP WEBHOOK ENDPOINTS
# ---------------------------------------------------------
@app.get("/webhook")
async def verify_meta_webhook(request: Request):
    """Meta WhatsApp Webhook verification endpoint."""
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    expected_token = database.get_setting("META_VERIFY_TOKEN") or DEFAULT_CONFIG["META_VERIFY_TOKEN"]

    if mode == "subscribe" and token == expected_token:
        return Response(content=challenge, media_type="text/plain")
    raise HTTPException(status_code=403, detail="Verification token mismatch")

@app.post("/webhook")
async def receive_meta_webhook(request: Request):
    """Meta WhatsApp Cloud API incoming message handler."""
    data = await request.json()
    try:
        entry = data.get("entry", [])[0]
        changes = entry.get("changes", [])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])

        if messages:
            msg = messages[0]
            from_phone = msg.get("from", "")
            contacts = value.get("contacts", [])
            sender_name = contacts[0].get("profile", {}).get("name", "WhatsApp User") if contacts else "User"

            if msg.get("type") == "text":
                text_body = msg.get("text", {}).get("body", "")
                reply_text, _ = whatsapp_engine.process_incoming_message(
                    message_text=text_body,
                    sender_phone=from_phone,
                    sender_name=sender_name
                )
                # Send reply back to WhatsApp user
                whatsapp_engine.send_meta_whatsapp_message(from_phone, reply_text)
    except Exception as e:
        print(f"Meta webhook processing error: {e}")
        return {"status": "EVENT_RECEIVED"}

# ---------------------------------------------------------
# TWILIO WHATSAPP WEBHOOK ENDPOINT (NO META ACCOUNT NEEDED)
# ---------------------------------------------------------
@app.post("/api/twilio/webhook")
async def receive_twilio_webhook(request: Request):
    """Twilio WhatsApp incoming message handler (No Meta Account or OTP required)."""
    form_data = await request.form()
    message_text = form_data.get("Body", "")
    from_phone = form_data.get("From", "").replace("whatsapp:", "")
    sender_name = form_data.get("ProfileName", "WhatsApp User")

    reply_text, _ = whatsapp_engine.process_incoming_message(
        message_text=message_text,
        sender_phone=from_phone,
        sender_name=sender_name
    )

    # Return TwiML XML response for instant WhatsApp reply via Twilio
    twiml_response = f'<?xml version="1.0" encoding="UTF-8"?><Response><Message>{reply_text}</Message></Response>'
    return Response(content=twiml_response, media_type="application/xml")

# ---------------------------------------------------------
# WEB DASHBOARD & SIMULATOR ENDPOINTS
# ---------------------------------------------------------
class SimulatorMessage(BaseModel):
    message: str
    sender_name: Optional[str] = "Production Tech"
    department: Optional[str] = "Production Line A"

@app.post("/api/simulator/send")
async def simulate_whatsapp_message(payload: SimulatorMessage):
    """Endpoint for the Web Dashboard WhatsApp simulator."""
    full_msg = payload.message
    # Inject department tag if not present
    if payload.department and "[" not in full_msg and "dept" not in full_msg.lower():
        full_msg = f"[{payload.department}] {full_msg}"
        
    reply, action_type = whatsapp_engine.process_incoming_message(
        message_text=full_msg,
        sender_phone="+1234567890",
        sender_name=payload.sender_name or "Web Simulator Tech"
    )
    return {
        "reply": reply,
        "action_type": action_type,
        "stats": database.get_statistics()
    }

@app.get("/api/stats")
async def get_stats():
    """Returns maintenance KPIs and statistics."""
    return database.get_statistics()

@app.get("/api/breakdowns")
async def list_breakdowns(limit: int = 100):
    """Returns breakdown logs."""
    return database.get_all_breakdowns(limit=limit)

@app.get("/api/maintenance")
async def list_maintenance(limit: int = 100):
    """Returns preventive maintenance logs."""
    return database.get_all_maintenance(limit=limit)

class CreateBreakdownRequest(BaseModel):
    department: str
    equipment_id: str
    issue_description: str
    sender_name: Optional[str] = "Web Admin"

@app.post("/api/breakdowns/log")
async def create_breakdown(req: CreateBreakdownRequest):
    ticket, bd_id = database.log_breakdown(
        department=req.department,
        equipment_id=req.equipment_id,
        issue_description=req.issue_description,
        sender_name=req.sender_name
    )
    open_bds = database.get_open_breakdowns()
    matching = [b for b in open_bds if b['ticket_number'] == ticket]
    if matching:
        google_sheets.sync_breakdown_to_sheet(matching[0])
    return {"ticket": ticket, "id": bd_id, "message": "Breakdown logged successfully"}

class ResolveBreakdownRequest(BaseModel):
    ticket_number: Optional[str] = None
    equipment_id: Optional[str] = None
    resolution_notes: str
    technician: Optional[str] = "Technician"

@app.post("/api/breakdowns/resolve")
async def resolve_breakdown_endpoint(req: ResolveBreakdownRequest):
    updated, err = database.resolve_breakdown(
        ticket_number=req.ticket_number,
        equipment_id=req.equipment_id,
        resolution_notes=req.resolution_notes,
        technician=req.technician
    )
    if err:
        raise HTTPException(status_code=400, detail=err)
    google_sheets.sync_breakdown_to_sheet(updated)
    return {"message": "Breakdown resolved successfully", "record": updated}

@app.get("/api/export/excel")
async def export_excel():
    """Generates and downloads styled Excel report."""
    filepath, filename = excel_generator.generate_excel_report()
    return FileResponse(
        path=filepath,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ---------------------------------------------------------
# BAILEYS REAL WHATSAPP WEBSOCKET QR CODE ENDPOINTS
# ---------------------------------------------------------
import subprocess
import requests as http_req

node_baileys_proc = None

def start_node_baileys():
    global node_baileys_proc
    if node_baileys_proc is None or node_baileys_proc.poll() is not None:
        try:
            node_baileys_proc = subprocess.Popen(
                ["node", "server.js"],
                cwd=str(BASE_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            print("[Python] Spawned Node.js Baileys WebSocket engine.")
        except Exception as e:
            print("[Python] Could not spawn node server:", e)

@app.get("/api/baileys/status")
async def get_baileys_status():
    start_node_baileys()
    # Try fetching real Baileys QR status from local Node process
    try:
        res = http_req.get("http://127.0.0.1:3000/api/baileys/status", timeout=2)
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return {"status": "CONNECTING", "qrCode": None}

@app.post("/api/baileys/start")
async def start_baileys():
    start_node_baileys()
    try:
        res = http_req.post("http://127.0.0.1:3000/api/baileys/start", timeout=2)
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return {"message": "Baileys engine starting...", "status": "CONNECTING"}

# ---------------------------------------------------------
# SETTINGS & CREDENTIALS ENDPOINTS
# ---------------------------------------------------------
@app.get("/api/settings")
async def get_settings():
    return {
        "spreadsheet_id": database.get_setting("GOOGLE_SPREADSHEET_ID") or DEFAULT_CONFIG["GOOGLE_SPREADSHEET_ID"],
        "sheet_name": database.get_setting("GOOGLE_SHEET_NAME") or DEFAULT_CONFIG["GOOGLE_SHEET_NAME"],
        "meta_token": database.get_setting("META_WHATSAPP_TOKEN") or DEFAULT_CONFIG["META_WHATSAPP_TOKEN"],
        "phone_number_id": database.get_setting("META_PHONE_NUMBER_ID") or DEFAULT_CONFIG["META_PHONE_NUMBER_ID"],
        "verify_token": database.get_setting("META_VERIFY_TOKEN") or DEFAULT_CONFIG["META_VERIFY_TOKEN"],
        "has_google_credentials": os.path.exists(CREDENTIALS_FILE)
    }

class SaveSettingsRequest(BaseModel):
    spreadsheet_id: Optional[str] = None
    sheet_name: Optional[str] = None
    meta_token: Optional[str] = None
    phone_number_id: Optional[str] = None
    verify_token: Optional[str] = None

@app.post("/api/settings")
async def save_settings(req: SaveSettingsRequest):
    if req.spreadsheet_id is not None:
        database.set_setting("GOOGLE_SPREADSHEET_ID", req.spreadsheet_id)
    if req.sheet_name is not None:
        database.set_setting("GOOGLE_SHEET_NAME", req.sheet_name)
    if req.meta_token is not None:
        database.set_setting("META_WHATSAPP_TOKEN", req.meta_token)
    if req.phone_number_id is not None:
        database.set_setting("META_PHONE_NUMBER_ID", req.phone_number_id)
    if req.verify_token is not None:
        database.set_setting("META_VERIFY_TOKEN", req.verify_token)
    return {"message": "Settings saved successfully"}

@app.post("/api/credentials/upload")
async def upload_credentials(file: UploadFile = File(...)):
    content = await file.read()
    try:
        # Validate json
        json.loads(content.decode("utf-8"))
        with open(CREDENTIALS_FILE, "wb") as f:
            f.write(content)
        return {"message": "Service account JSON saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid JSON credentials file")

@app.get("/", response_class=HTMLResponse)
async def root():
    index_path = BASE_DIR / "static" / "index.html"
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h2>WhatsApp Maintenance Tracker Backend Running</h2>")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=3000, reload=True)
