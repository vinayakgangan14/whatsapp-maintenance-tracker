import requests
import logging
from config import DEFAULT_CONFIG
import database
import parser
import google_sheets

logger = logging.getLogger("whatsapp_engine")

def process_incoming_message(message_text, sender_phone="", sender_name=""):
    """
    Core pipeline: receives raw message, parses it, updates SQLite DB,
    attempts live Google Sheets sync, and returns WhatsApp reply text.
    """
    reply_text, action_type, details = parser.parse_whatsapp_message(
        text=message_text,
        sender_phone=sender_phone,
        sender_name=sender_name
    )

    # Attempt Google Sheets sync in background/inline for new or resolved breakdowns
    if action_type in ["BD_SUCCESS", "FIX_SUCCESS"]:
        try:
            if action_type == "BD_SUCCESS" and details.get('ticket'):
                open_bds = database.get_open_breakdowns()
                matching = [b for b in open_bds if b['ticket_number'] == details['ticket']]
                if matching:
                    google_sheets.sync_breakdown_to_sheet(matching[0])
            elif action_type == "FIX_SUCCESS" and isinstance(details, dict) and details.get('ticket_number'):
                google_sheets.sync_breakdown_to_sheet(details)
        except Exception as e:
            logger.error(f"Google Sheets async sync warning: {e}")

    return reply_text, action_type

def send_meta_whatsapp_message(to_phone, message_text):
    """Sends message using Meta WhatsApp Business Cloud API."""
    token = database.get_setting("META_WHATSAPP_TOKEN") or DEFAULT_CONFIG["META_WHATSAPP_TOKEN"]
    phone_id = database.get_setting("META_PHONE_NUMBER_ID") or DEFAULT_CONFIG["META_PHONE_NUMBER_ID"]

    if not token or not phone_id:
        logger.warning("Meta WhatsApp credentials not set. Message not sent via HTTP API.")
        return False, "Meta API credentials not configured."

    url = f"https://graph.facebook.com/v18.0/{phone_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_phone,
        "type": "text",
        "text": {"body": message_text}
    }

    try:
        res = requests.post(url, json=payload, headers=headers, timeout=10)
        res.raise_for_status()
        return True, "Message sent via Meta API."
    except Exception as e:
        logger.error(f"Meta WhatsApp API error: {e}")
        return False, str(e)
