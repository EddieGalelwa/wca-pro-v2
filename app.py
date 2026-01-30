# app.py - PRODUCTION VERSION
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from logic import triage
from models import get_db, Consultation
from config import CLINIC_NAME
from sqlalchemy import text
import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route("/whatsapp", methods=["POST"])
def whatsapp_webhook():
    """Main webhook endpoint for Twilio WhatsApp"""
    try:
        incoming_msg = request.form.get("Body", "").strip()
        from_wa = request.form.get("From", "")
        phone = from_wa.replace("whatsapp:", "").replace(" ", "").replace("-", "")
        
        logger.info(f"📱 Message from {phone}: {incoming_msg[:50]}...")
        
        reply_text = triage(incoming_msg, phone)
        
        resp = MessagingResponse()
        resp.message(reply_text)
        
        logger.info(f"✅ Replied to {phone}: {reply_text[:50]}...")
        return str(resp), 200, {'Content-Type': 'application/xml'}
        
    except Exception as e:
        logger.error(f"💥 Error: {str(e)}")
        resp = MessagingResponse()
        resp.message("Sorry, I'm having trouble. Please type NEW to restart.")
        return str(resp), 200, {'Content-Type': 'application/xml'}

@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    try:
        db = get_db()
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "service": "WCA Pro", "clinic": CLINIC_NAME}, 200
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}, 500

if __name__ == "__main__":
    from models import Base, engine
    Base.metadata.create_all(engine)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)