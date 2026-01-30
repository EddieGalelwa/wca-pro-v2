# app.py - WCA Pro Main Application (DEBUG VERSION)
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from logic import triage
from models import get_db, Consultation
from config import CLINIC_NAME
from sqlalchemy import text
import logging
import traceback
from datetime import datetime
import os  # CRITICAL for Railway PORT

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
            "clinic": CLINIC_NAME,
            "database": "connected"
        }, 200
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }, 500

@app.route("/stats", methods=["GET"])
def get_stats():
    """Get basic statistics (add auth in production)"""
    try:
        db = get_db()
        
        total_consultations = db.query(Consultation).count()
        today_consultations = db.query(Consultation).filter(
            Consultation.created_at >= datetime.now().replace(hour=0, minute=0, second=0)
        ).count()
        
        return {
            "total_consultations": total_consultations,
            "today_consultations": today_consultations,
            "service": "WCA Pro"
        }, 200
        
    except Exception as e:
        return {"error": str(e)}, 500

if __name__ == "__main__":
    # Initialize database
    from models import Base, engine
    Base.metadata.create_all(engine)
    logger.info("WCA Pro started successfully")
    
    # Use Railway's PORT environment variable or default to 5000
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)