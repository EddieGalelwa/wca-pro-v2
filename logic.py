# logic.py - Multi-Clinic Version (RESOLVED)
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
        print(f"✅ DEBUG:   Phone: {clinic.phone}")
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

    # ADD THIS DEBUG LINE
    print(f"🚀 NEW LOGIC.PY IS RUNNING! Clinic detection active.")

    # Normalize input
    msg = incoming_msg.strip()
    msg_upper = msg.upper()
    
    # Identify which clinic is being contacted
    clinic = get_clinic_by_phone(twilio_phone or phone)
    print(f"🚀 DEBUG: triage() will use clinic: {clinic.name} (ID: {clinic.id})")

    # Get state and patient WITH CLINIC ISOLATION
    state = get_or_create_state(phone, clinic.id)
    patient = get_patient(phone, clinic.id)
    
    context = json.loads(state.data) if state.data else {}
    
    # Handle RESET command anywhere
    if msg_upper == "NEW" or msg_upper == "RESET":
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
    return "I'm not sure I understand. Type NEW to start a fresh consultation."

# ============ ALL HANDLERS NOW CLINIC-AWARE ============

def update_state(phone, new_state, data=None, clinic_id=None):
    """Update conversation state WITH CLINIC ISOLATION"""
    db = get_db()
    state = db.query(ConversationState).filter_by(phone=phone, clinic_id=clinic_id).first()
    
    if state:
        state.state = new_state
        if data:
            state.data = json.dumps(data)
        state.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(state)
    
    return state

def handle_greeting(msg, phone, patient, context, clinic):
    """Initial greeting"""
    update_state(phone, "awaiting_name", context, clinic_id=clinic.id)
    return f"🏥 Welcome to {clinic.name}!\n\nI'm your AI health assistant. I'll help you with symptom assessment and hospital booking.\n\nMay I know your name please?"

def handle_name(msg, phone, patient, context, clinic):
    """Process name and move to symptoms"""
    try:
        db = get_db()
        
        # Merge patient into current session
        patient = db.merge(patient)
        
        patient.name = msg.title()
        patient.last_visit = datetime.utcnow()
        
        context["name"] = msg.title()
        
        # Commit patient changes
        db.commit()
        db.refresh(patient)
        
        # Update state
        update_state(phone, "awaiting_symptoms", context, clinic_id=clinic.id)
        
        return f"Thank you, {patient.name}. 👋\n\nPlease describe what brings you here today. You can say something like:\n• 'I have headache and fever'\n• 'Stomach pain for 3 days'\n• 'Chest pain when breathing'"
    except Exception as e:
        db.rollback()
        return f"❌ Sorry, there was an error saving your name. Please try again. Error: {str(e)[:50]}"

def handle_symptoms(msg, phone, patient, context, clinic):
    """Process symptoms with AI triage"""
    context["symptoms"] = msg
    update_state(phone, "triage_processing", context, clinic_id=clinic.id)
    
    # AI Analysis
    ai_result = analyze_symptoms(msg, patient.name or "Patient")
    context["ai_result"] = ai_result
    update_state(phone, "triage_complete", context, clinic_id=clinic.id)
    
    # Build response
    severity_emoji = {
        "low": "🟢",
        "medium": "🟡", 
        "high": "🔴",
        "emergency": "🚨"
    }.get(ai_result["severity"], "⚪")
    
    response = f"""{severity_emoji} *Assessment Complete*

*Symptoms:* {msg}
*Severity:* {ai_result['severity'].upper()}
*Assessment:* {ai_result['assessment']}

*Recommendation:* {ai_result['recommended_action']}

Would you like me to book you at a hospital? Reply YES to continue or MORE for details."""
    
    # Emergency override
    if ai_result["severity"] == "emergency":
        response = f"""🚨 *EMERGENCY DETECTED*

{ai_result['assessment']}

⚠️ Please go to the nearest hospital IMMEDIATELY or call emergency services!

Do you need help finding the closest emergency facility? Reply YES for options."""
        context["is_emergency"] = True
        update_state(phone, "triage_complete", context, clinic_id=clinic.id)
    
    return response

def handle_triage_result(msg, phone, patient, context, clinic):
    """Handle post-triage response"""
    msg_lower = msg.lower()
    
    if any(word in msg_lower for word in ["yes", "book", "hospital", "continue"]):
        from config import HOSPITALS
        hospital_list = "\n".join([
            f"*{k}. {v['name']}* ({v['specialty']})"
            for k, v in HOSPITALS.items()
        ])
        
        update_state(phone, "selecting_hospital", context, clinic_id=clinic.id)
        return f"🏥 *Select Hospital*\n\n{hospital_list}\n\nReply with the number (1-4):"
    
    elif "more" in msg_lower or "detail" in msg_lower:
        ai_result = context.get("ai_result", {})
        return f"""📋 *Detailed Information*

*Specialist Needed:* {ai_result.get('specialist_needed', 'General')}
*Urgency:* {ai_result.get('hospital_urgency', 'routine')}
*SHA Claim:* {'✅ Eligible' if ai_result.get('sha_claim_eligible') else '❌ Not eligible'}

{ai_result.get('disclaimer', '')}

Reply YES to book or NEW to start over."""
    
    else:
        return "Please reply YES to book a hospital, MORE for details, or NEW to start over."

def handle_hospital_selection(msg, phone, patient, context, clinic):
    """Process hospital selection"""
    from config import HOSPITALS
    
    if msg.strip() in HOSPITALS:
        hospital = HOSPITALS[msg.strip()]
        context["selected_hospital"] = hospital
        context["hospital_id"] = msg.strip()
        
        ref = f"WCA{datetime.utcnow().strftime('%m%d%H%M')}{random.randint(10,99)}"
        context["reference"] = ref
        
        # Save consultation to DB
        try:
            db = get_db()
            patient = db.merge(patient)
            
            consultation = Consultation(
                clinic_id=clinic.id,  # NEW: Clinic isolation
                patient_phone=phone,
                symptoms=context.get("symptoms", ""),
                ai_assessment=json.dumps(context.get("ai_result", {})),
                severity=context.get("ai_result", {}).get("severity", "unknown"),
                hospital_id=msg.strip(),
                reference_number=ref,
                sha_claim_submitted=context.get("ai_result", {}).get("sha_claim_eligible", False)
            )
            db.add(consultation)
            db.commit()
            
            update_state(phone, "confirmed", context, clinic_id=clinic.id)
            
            ai_result = context.get("ai_result", {})
            
            return f"""✅ *Booking Confirmed!*

*Clinic:* {clinic.name}
*Patient:* {patient.name}
*Reference:* `{ref}`
*Hospital:* {hospital['name']}
*Specialty:* {hospital['specialty']}

*Next Steps:*
1. Present this reference at the hospital
2. Mention SHA claim eligibility: {'Yes' if ai_result.get('sha_claim_eligible') else 'Check at reception'}
3. Bring ID and any previous medical records

*Estimated wait time:* 15-30 minutes

Type NEW for another consultation."""
        except Exception as e:
            db.rollback()
            return f"❌ Sorry, there was an error saving your booking. Please try again. Error: {str(e)[:50]}"
    
    else:
        valid_options = ", ".join(HOSPITALS.keys())
        return f"❌ Invalid selection. Please reply with a number: {valid_options}"

def handle_confirmed(msg, phone, patient, context, clinic):
    """Handle post-confirmation"""
    msg_upper = msg.upper()
    
    if msg_upper == "NEW":
        update_state(phone, "greeting", {}, clinic_id=clinic.id)
        return f"🏥 Welcome to {clinic.name}!\n\nMay I know your name please?"
    
    elif "status" in msg.lower():
        db = get_db()
        recent = db.query(Consultation).filter_by(
            patient_phone=phone, 
            clinic_id=clinic.id
        ).order_by(Consultation.created_at.desc()).first()
        
        if recent:
            from config import HOSPITALS
            return f"📋 *Your Last Consultation*\nReference: `{recent.reference_number}`\nStatus: {recent.status.upper()}\nHospital: {HOSPITALS.get(recent.hospital_id, {}).get('name', 'Unknown')}\n\nType NEW for a new consultation."
        else:
            return "No recent consultations found. Type NEW to start."
    
    else:
        return "Type NEW to start a fresh consultation or STATUS to check your last booking."

# Add this at the bottom of logic.py
print(f"🚨 LOADING LOGIC.PY FROM: {__file__}")