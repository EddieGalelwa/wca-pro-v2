# whatsapp.py - Twilio WhatsApp Service
from twilio.rest import Client
from twilio.request_validator import RequestValidator
from config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER
import logging

logger = logging.getLogger(__name__)

class WhatsAppService:
    def __init__(self):
        self.client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        self.from_number = TWILIO_WHATSAPP_NUMBER
    
    def send_message(self, to_number, message):
        """
        Send WhatsApp message via Twilio
        to_number: should be in format 'whatsapp:+254724896761'
        """
        try:
            # Ensure proper format
            if not to_number.startswith("whatsapp:"):
                to_number = f"whatsapp:{to_number}"
            
            # Remove any spaces
            to_number = to_number.replace(" ", "").replace("-", "")
            
            message = self.client.messages.create(
                from_=self.from_number,
                body=message[:1600],  # Twilio limit
                to=to_number
            )
            
            logger.info(f"Message sent: {message.sid} to {to_number}")
            return message.sid
            
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            raise
    
    def validate_request(self, request):
        """Validate incoming webhook from Twilio"""
        validator = RequestValidator(TWILIO_AUTH_TOKEN)
        url = str(request.url)
        signature = request.headers.get('X-Twilio-Signature', '')
        
        return validator.validate(url, request.form, signature)

# Singleton instance
whatsapp_service = WhatsAppService()

def reply(message_body, to_number):
    """
    Convenience function for sending replies
    """
    return whatsapp_service.send_message(to_number, message_body)