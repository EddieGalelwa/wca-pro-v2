# app.py - Meta WhatsApp Business API Integration (PRODUCTION)
from flask import Flask, request, jsonify
import requests
import logging
import os
from sqlalchemy import text  # FIXED: Added text import
from logic import triage
from models import get_db, Consultation
from config_meta import (
    PHONE_NUMBER_ID, 
    ACCESS_TOKEN, 
    TEST_PHONE_NUMBER,
    WEBHOOK_VERIFY_TOKEN
)
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Meta API Endpoint
META_API_URL = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"

@app.route("/whatsapp", methods=["GET", "POST"])
def whatsapp_webhook():
    """
    Handle Meta WhatsApp webhooks
    GET: Verification
    POST: Incoming messages
    """
    if request.method == "GET":
        # Verification request from Meta
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        
        if mode and token:
            if mode == "subscribe" and token == WEBHOOK_VERIFY_TOKEN:
                logger.info("✅ Webhook verified successfully")
                return challenge, 200
            else:
                logger.error("❌ Webhook verification failed")
                return "Verification failed", 403
        return "Missing parameters", 400
    
    elif request.method == "POST":
        # Incoming message from Meta
        try:
            data = request.get_json()
            logger.info(f"📥 Incoming webhook: {data}")
            
            # Extract message details
            if "entry" in data and data["entry"]:
                for entry in data["entry"]:
                    if "changes" in entry:
                        for change in entry["changes"]:
                            if "value" in change:
                                value = change["value"]
                                if "messages" in value and value["messages"]:
                                    message = value["messages"][0]
                                    from_number = message["from"]
                                    msg_body = message["text"]["body"]
                                    
                                    logger.info(f"📱 Message from {from_number}: {msg_body}")
                                    
                                    # Process through your triage logic
                                    reply_text = triage(msg_body, from_number)
                                    
                                    # Send reply back via Meta API
                                    send_whatsapp_message(from_number, reply_text)
                                    
                                    return jsonify({"status": "success"}), 200
            
            return jsonify({"status": "success"}), 200
            
        except Exception as e:
            logger.error(f"💥 Error processing webhook: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

def send_whatsapp_message(to_number, message_text):
    """Send message via Meta WhatsApp API"""
    try:
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "text",
            "text": {"body": message_text}
        }
        
        response = requests.post(META_API_URL, headers=headers, json=payload)
        
        if response.status_code == 200:
            logger.info(f"✅ Message sent to {to_number}")
        else:
            logger.error(f"❌ Failed to send message: {response.text}")
            
    except Exception as e:
        logger.error(f"💥 Error sending message: {str(e)}")

@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint - FIXED with text() wrapper"""
    try:
        # Test database connection
        db = get_db()
        db.execute(text("SELECT 1"))  # FIXED: Added text() wrapper
        
        return {
            "status": "healthy",
            "service": "WCA Pro - Meta Edition",
            "database": "connected"
        }, 200
        
    except Exception as e:
        logger.error(f"💥 Health check failed: {str(e)}")
        return {
            "status": "unhealthy", 
            "error": str(e)
        }, 500

if __name__ == "__main__":
    from models import Base, engine
    Base.metadata.create_all(engine)
    logger.info("WCA Pro (Meta Edition) started successfully")
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)