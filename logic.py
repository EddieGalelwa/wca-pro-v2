# logic.py - Conversation State Machine
from models import get_db, Patient, Consultation, ConversationState
from ai_service import analyze_symptoms, generate_response
from config import HOSPITALS, CLINIC_NAME
from datetime import datetime
import json
import random

def get_or_create_state(phone):
    """Get or create conversation state for a phone number"""
    db = get_db()
    state = db.query(ConversationState).filter_by(phone=phone).first()
    
    if not state:
        state = ConversationState(phone=phone, state="greeting", data="{}")
        db.add(state)
        db.commit()
    
    return state

def update_state(phone, new_state, data=None):
    """Update conversation state"""
    db = get_db()
    state = db.query(ConversationState).filter_by(phone=phone).first()
    
    if state:
        state.state = new_state
        if data:
            state.data = json.dumps(data)
        state.updated_at = datetime.utcnow()
        db.commit()
    
    return state

def get_patient(phone):
    """Get or create patient record"""
    db = get_db()
    patient = db.query(Patient).filter_by(phone=phone).first()
    
    if not patient:
        patient = Patient(phone=phone)
        db.add(patient)
        db.commit()
        db.refresh(patient)
    
    return patient

def triage(incoming_msg, phone):
    """
    Main triage function - handles all conversation states
    """
    # Normalize input
    msg = incoming_msg.strip()
    msg_lower = msg.lower()
    
    # Get state and patient
    state = get_or_create_state(phone)
    patient = get_patient(phone)
    context = json.loads(state.data) if state.data else {}
    
    # Handle RESET command anywhere
    if msg_upper == "NEW" or msg_upper == "RESET":
        update_state(phone, "greeting", {})
        return f"🏥 Welcome to {CLINIC_NAME}!\n\nI'm your AI health assistant. May I know your name please?"
    
    # STATE MACHINE
    if state.state == "greeting":
        return handle_greeting(msg, phone, patient, context)
    
    elif state.state == "awaiting_name":
        return handle_name(msg, phone, patient, context)
    
    elif state.state == "awaiting_symptoms":
        return handle_symptoms(msg, phone, patient, context)
    
    elif state.state == "triage_complete":
        return handle_triage_result(msg, phone, patient, context)
    
    elif state.state == "selecting_hospital":
        return handle_hospital_selection(msg, phone, patient, context)
    
    elif state.state == "confirmed":
        return handle_confirmed(msg, phone, patient, context)
    
    # Fallback
    return "I'm not sure I understand. Type NEW to start a fresh consultation."

def handle_greeting(msg, phone, patient, context):
    """Initial greeting"""
    update_state(phone, "awaiting_name", context)
    return f"🏥 Welcome to {CLINIC_NAME}!\n\nI'm your AI health assistant. I'll help you with symptom assessment and hospital booking.\n\nMay I know your name please?"

def handle_name(msg, phone, patient, context):
    """Process name and move to symptoms"""
    # Update patient name
    db = get_db()
    patient.name = msg.title()
    patient.last_visit = datetime.utcnow()
    db.commit()
    
    context["name"] = msg.title()
    update_state(phone, "awaiting_symptoms", context)
    
    return f"Thank you, {msg.title()}. 👋\n\nPlease describe what brings you here today. You can say something like:\n• 'I have headache and fever'\n• 'Stomach pain for 3 days'\n• 'Chest pain when breathing'"

def handle_symptoms(msg, phone, patient, context):
    """Process symptoms with AI triage"""
    context["symptoms"] = msg
    update_state(phone, "triage_processing", context)
    
    # AI Analysis
    ai_result = analyze_symptoms(msg, patient.name or "Patient")
    context["ai_result"] = ai_result
    update_state(phone, "triage_complete", context)
    
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
        update_state(phone, "triage_complete", context)
    
    return response

def handle_triage_result(msg, phone, patient, context):
    """Handle post-triage response"""
    msg_lower = msg.lower()
    
    if any(word in msg_lower for word in ["yes", "book", "hospital", "continue"]):
        # Show hospital options
        hospital_list = "\n".join([
            f"*{k}. {v['name']}* ({v['specialty']})"
            for k, v in HOSPITALS.items()
        ])
        
        update_state(phone, "selecting_hospital", context)
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

def handle_hospital_selection(msg, phone, patient, context):
    """Process hospital selection"""
    if msg.strip() in HOSPITALS:
        hospital = HOSPITALS[msg.strip()]
        context["selected_hospital"] = hospital
        context["hospital_id"] = msg.strip()
        
        # Generate reference number
        ref = f"WCA{datetime.now().strftime('%m%d%H%M')}{random.randint(10,99)}"
        context["reference"] = ref
        
        # Save consultation to DB
        db = get_db()
        consultation = Consultation(
            patient_phone=phone,
            name=patient.name,
            symptoms=context.get("symptoms", ""),
            ai_assessment=json.dumps(context.get("ai_result", {})),
            severity=context.get("ai_result", {}).get("severity", "unknown"),
            hospital_id=msg.strip(),
            reference_number=ref,
            sha_claim_submitted=context.get("ai_result", {}).get("sha_claim_eligible", False)
        )
        db.add(consultation)
        db.commit()
        
        update_state(phone, "confirmed", context)
        
        ai_result = context.get("ai_result", {})
        
        return f"""✅ *Booking Confirmed!*

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
    
    else:
        valid_options = ", ".join(HOSPITALS.keys())
        return f"❌ Invalid selection. Please reply with a number: {valid_options}"

def handle_confirmed(msg, phone, patient, context):
    """Handle post-confirmation"""
    msg_upper = msg.upper()
    
    if msg_upper == "NEW":
        update_state(phone, "greeting", {})
        return f"🏥 Welcome to {CLINIC_NAME}!\n\nMay I know your name please?"
    
    elif "status" in msg_lower:
        # Check recent consultation
        db = get_db()
        recent = db.query(Consultation).filter_by(patient_phone=phone).order_by(Consultation.created_at.desc()).first()
        
        if recent:
            return f"📋 *Your Last Consultation*\nReference: `{recent.reference_number}`\nStatus: {recent.status.upper()}\nHospital: {HOSPITALS.get(recent.hospital_id, {}).get('name', 'Unknown')}\n\nType NEW for a new consultation."
        else:
            return "No recent consultations found. Type NEW to start."
    
    else:
        return "Type NEW to start a fresh consultation or STATUS to check your last booking."