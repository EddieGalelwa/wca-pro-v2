# app.py - DEBUG VERSION
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from logic import triage
from models import get_db, Consultation
from config import CLINIC_NAME
from sqlalchemy import text
import logging
import traceback
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route("/whatsapp", methods=["POST"])
def whatsapp_webhook():
    """
    Main webhook endpoint for Twilio WhatsApp
    """
    try:
        # ======== AGGRESSIVE DEBUG PRINTS ========
        print(f"\n{'='*60}")
        print(f"📥 INCOMING WEBHOOK REQUEST")
        print(f"📥 Timestamp: {datetime.utcnow()}")
        print(f"📥 Form data: {dict(request.form)}")
        print(f"{'='*60}\n")
        
        # Get incoming message details
        incoming_msg = request.form.get("Body", "").strip()
        from_wa = request.form.get("From", "")
        
        print(f"📥 Message Body: '{incoming_msg}'")
        print(f"📥 From: {from_wa}")
        
        # Normalize phone number
        phone = from_wa.replace("whatsapp:", "").replace(" ", "").replace("-", "")
        print(f"📥 Normalized phone: {phone}")
        
        logger.info(f"Message from {phone}: {incoming_msg[:50]}...")
        
        # ======== PROCESS THROUGH LOGIC ========
        print(f"🚀 DEBUG: Calling triage() function...")
        
        reply_text = triage(incoming_msg, phone)
        print(f"✅ DEBUG: triage() succeeded, reply length: {len(reply_text)}")
        
        # Create Twilio response
        resp = MessagingResponse()
        resp.message(reply_text)
        
        logger.info(f"Replied to {phone}: {reply_text[:50]}...")
        
        print(f"📤 Response sent successfully")
        print(f"{'='*60}\n\n")
        
        return str(resp), 200, {'Content-Type': 'application/xml'}
        
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"💥 UNHANDLED EXCEPTION IN WEBHOOK")
        print(f"💥 Error: {str(e)}")
        print(f"💥 Traceback: {traceback.format_exc()}")
        print(f"{'='*60}\n\n")
        
        logger.error(f"Critical error in webhook: {traceback.format_exc()}")
        
        # Graceful error response
        resp = MessagingResponse()
        resp.message("I apologize, I'm having trouble processing your request. Please try again or type NEW to restart.")
        return str(resp), 200, {'Content-Type': 'application/xml'}

@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        db = get_db()
        db.execute(text("SELECT 1"))
        
        return {
            "status": "healthy",
            "service": "WCA Pro",
            "clinic": CLINIC_NAME