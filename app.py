# app.py - WCA Pro Main Application
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
        # Get incoming message details
        incoming_msg = request.form.get("Body", "").strip()
        from_wa = request.form.get("From", "")  # Format: whatsapp:+254724896761
        
        # Normalize phone number
        phone = from_wa.replace("whatsapp:", "").replace(" ", "").replace("-", "")
        
        logger.info(f"Message from {phone}: {incoming_msg[:50]}...")
        
        # Process through triage logic
        reply_text = triage(incoming_msg, phone)
        
        # Create Twilio response
        resp = MessagingResponse()
        resp.message(reply_text)
        
        logger.info(f"Replied to {phone}: {reply_text[:50]}...")
        
        return str(resp), 200, {'Content-Type': 'application/xml'}
        
    except Exception as e:
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
    
    app.run(host="0.0.0.0", port=5000, debug=True)