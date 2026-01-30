# logic.py - Multi-Clinic Version (PRODUCTION READY)
print("🚨 DEBUG MULTI-CLINIC LOGIC LOADED!")

from models import get_db, Clinic, Patient, Consultation, ConversationState, get_patient, get_or_create_state
from ai_service import analyze_symptoms
from config import CLINIC_NAME
from datetime import datetime
import json
import random

# ============ CLINIC IDENTIFICATION (CRITICAL) ============

def get_clinic_by_phone(incoming_phone):
    """
    Identify which clinic is being contacted based on Twilio phone number.
    For now, use the first active clinic in the database.
    """
    db = get_db()
    print(f"\n{'='*50}")
    print(f"🔍 DEBUG: get_clinic_by_phone() called")
    print(f"🔍 DEBUG: Querying database for active clinics...")
    
    # Query active clinics
    total_clinics = db.query(Clinic).count()
    active_clinics = db.query(Clinic).filter_by(is_active=True).count()
    
    print(f"🔍 DEBUG: Total clinics in DB: {total_clinics}")
    print(f"🔍 DEBUG: Active clinics in DB: {active_clinics}")
    
    clinic = db.query(Clinic).filter_by(is_active=True).first()
    
    print(f"🔍 DEBUG: Clinic query result: {clinic}")
    if clinic:
        print(f"✅ DEBUG: FOUND CLINIC!")
        print(f"✅ DEBUG:   ID: {clinic.id}")
        print(f"✅ DEBUG:   Name: {clinic.name}")
        print(f"✅ DEBUG:   Active: {clinic.is_active}")
    else:
        print(f"🚨 DEBUG: NO CLINIC FOUND IN DATABASE!")
        print(f"🚨 DEBUG: Falling back to config.CLINIC_NAME = '{CLINIC_NAME}'")
    
    if not clinic:
        print(f"🚨 DEBUG: Creating fallback clinic...")
        clinic = Clinic(
            id="default_clinic_001",
            name=CLINIC_NAME,
            phone="254700000000",
            plan="starter",
            is_active=True,
            created_at=datetime.utcnow()
        )
        db.add(clinic)
        db.commit()
        db.refresh(clinic)
        print(f"🚨 DEBUG: Created fallback clinic: {clinic.name}")
    
    print(f"{'='*50}\n")
    return clinic

def triage(incoming_msg, phone, twilio_phone=None):
    """
    Main triage function - NOW CLINIC-AWARE
    twilio_phone = The Twilio number the patient texted (used to identify clinic)
    """
    print(f"\n{'='*50}")
    print(f"🚀 DEBUG: triage() CALLED with phone: {phone}")

    # Normalize input
    msg = incoming_msg.strip()
    msg_upper = msg.upper()
    
    # Identify which clinic is being contacted
    clinic = get_clinic_by_phone(twilio_phone or phone)
    print(f"🚀 DEBUG: Using clinic: {clinic.name} (ID: {clinic.id})")
    
    # Get state and patient WITH CLINIC ISOLATION
    state = get_or_create_state(phone, clinic.id)
    patient = get_patient(phone, clinic.id)
    
    context = json.loads(state.data) if state.data else {}
    
    print(f"🚀 DEBUG: Current state: {state.state}")
    print(f"🚀 DEBUG: Patient: {patient.name or 'None'}")
    print(f"{'='*50}\n")
    
    # Handle RESET command anywhere
    if msg_upper == "NEW" or msg_upper == "RESET":
        print(f"🔄 DEBUG: RESET command detected")
        update_state(phone, "greeting", {}, clinic_id=clinic.id)
        return f"🏥 Welcome to {clinic.name}!\n\nI'm your AI health assistant. May I know your name please?"
    
    # STATE MACHINE
    if state.state == "greeting":
        return handle_greeting(msg, phone, patient, context, clinic)
    
    elif state.state == "awaiting_name":
        return handle_name(msg, phone, patient, context, clinic)
    
    elif state.state == "awaiting_symptoms":
        return handle_symptoms(msg, phone, patient, context, clinic)
    
    elif state.state == "triage_complete":
        return handle_triage_result(msg, phone, patient, context, clinic)
    
    elif state.state == "selecting_hospital":
        return handle_hospital_selection(msg, phone, patient, context, clinic)
    
    elif state.state == "confirmed":
        return handle_confirmed(msg, phone, patient, context, clinic)
    
    # Fallback
    return