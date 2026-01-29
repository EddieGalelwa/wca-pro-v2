# config.py - SECURE CONFIGURATION
import os
from dotenv import load_dotenv

load_dotenv()

# API Keys (NEVER commit this file to GitHub!)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_NUMBER = "whatsapp:+1415523886"

# Clinic Settings (Edit these for each hospital)
CLINIC_NAME = "AfyaCare Medical Center"
CLINIC_PHONE = "+254724896761"
CLINIC_ADDRESS = "Nairobi, Kenya"

# Hospital Database
HOSPITALS = {
    "1": {"name": "Kenyatta National Hospital", "specialty": "General/Multi-specialty"},
    "2": {"name": "Nairobi Hospital", "specialty": "Private/General"},
    "3": {"name": "Aga Khan University Hospital", "specialty": "Premium/Multi-specialty"},
    "4": {"name": "MP Shah Hospital", "specialty": "General/Cardiac"}
}

# AI Configuration
OPENAI_MODEL = "gpt-3.5-turbo"
MAX_TOKENS = 300
TEMPERATURE = 0.4

# Database
DATABASE_URL = "sqlite:///wca_pro.db"

# Feature Flags
ENABLE_SHA_CLAIMS = True
ENABLE_AI_TRIAGE = True