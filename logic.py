# logic.py - PRODUCTION VERSION
from models import get_db, Clinic, Patient, Consultation, ConversationState, get_patient, get_or_create_state
from ai_service import analyze_symptoms
from config import CLINIC_NAME
from datetime import datetime
import json
import random

def get_clinic_by_phone(incoming_phone):
    """Identify clinic from Twilio phone number"""
    db = get_db()
    clinic = db.query(Clinic).filter_by(is_active=True).first()
    
    if not clinic:
        clinic = Clinic(id="default_clinic_001", name=CLINIC_NAME, phone="254700000000", plan="starter", is_active=True, created_at=datetime.utcnow())
        db.add(clinic)
        db.commit()
        db.refresh(clinic)
    
    return clinic

def update_state(phone, new_state, data=None, clinic_id=None):
    """Update conversation state with clinic isolation"""
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

def triage(incoming_msg, phone, twilio_phone=None):
    """Main triage function - clinic-aware"""
    msg = incoming_msg.strip()
    msg_upper = msg.upper()
    
    clinic = get_clinic_by_phone(twilio_phone or phone)
    state = get_or_create_state(phone, clinic.id)
    patient = get_patient(phone, clinic.id)
    context = json.loads(state.data) if state.data else {}
    
    if msg_upper == "NEW" or msg_upper == "RESET":
        update_state(phone, "greeting", {}, clinic_id=clinic.id)
        return f"🏥 Welcome to {clinic.name}!\n\nMay I know your name please?"
    
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
    
    return "Type NEW to start."

def handle_greeting(msg, phone, patient, context, clinic):
    update_state(phone, "awaiting_name", context, clinic_id=clinic.id)
    return f"🏥 Welcome to {clinic.name}!\n\nMay I know your name please?"

def handle_name(msg, phone, patient, context, clinic):
    try:
        db = get_db()
        patient = db.merge(patient)
        patient.name = msg.title()
        patient.last_visit = datetime.utcnow()
        context["name"] = msg.title()
        db.commit()
        db.refresh(patient)
        update_state(phone, "awaiting_symptoms", context, clinic_id=clinic.id)
        return f"Thank you, {patient.name}. 👋\n\nPlease describe your symptoms..."
    except Exception as e:
        db.rollback()
        return f"❌ Error saving name: {str(e)[:50]}"

def handle_symptoms(msg, phone, patient, context, clinic):
    context["symptoms"] = msg
    update_state(phone, "triage_processing", context, clinic_id=clinic.id)
    
    ai_result = analyze_symptoms(msg, patient.name or "Patient")
    context["ai_result"] = ai_result
    update_state(phone, "triage_complete", context, clinic_id=clinic.id)
    
    severity_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴", "emergency": "🚨"}.get(ai_result["severity"], "⚪")
    
    response = f"""{severity_emoji} *Assessment Complete*

*Symptoms:* {msg}
*Severity:* {ai_result['severity'].upper()}
*Recommendation:* {ai_result['recommended_action']}

Reply YES to book or MORE for details."""
    
    if ai_result["severity"] == "emergency":
        response = f"""🚨 *EMERGENCY DETECTED*

{ai_result['assessment']}

⚠️ Go to hospital IMMEDIATELY!"""
        context["is_emergency"] = True
    
    return response

def handle_triage_result(msg, phone, patient, context, clinic):
    msg_lower = msg.lower()
    
    if any(word in msg_lower for word in ["yes", "book", "hospital"]):
        from config import HOSPITALS
        hospital_list = "\n".join([f"*{k}. {v['name']}* ({v['specialty']})" for k, v in HOSPITALS.items()])
        update_state(phone, "selecting_hospital", context, clinic_id=clinic.id)
        return f"🏥 *Select Hospital*\n\n{hospital_list}\n\nReply with number (1-4):"
    
    elif "more" in msg_lower:
        ai_result = context.get("ai_result", {})
        return f"""📋 *Details*

*Specialist:* {ai_result.get('specialist_needed', 'General')}
*SHA Claim:* {'✅ Eligible' if ai_result.get('sha_claim_eligible') else '❌ Not eligible'}

Reply YES to book."""
    
    return "Reply YES, MORE, or NEW."

def handle_hospital_selection(msg, phone, patient, context, clinic):
    from config import HOSPITALS
    
    if msg.strip() in HOSPITALS:
        hospital = HOSPITALS[msg.strip()]
        context["selected_hospital"] = hospital
        context["hospital_id"] = msg.strip()
        
        ref = f"WCA{datetime.utcnow().strftime('%m%d%H%M')}{random.randint(10,99)}"
        context["reference"] = ref
        
        db = get_db()
        patient = db.merge(patient)
        
        consultation = Consultation(
            clinic_id=clinic.id,
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
        
        return f"""✅ *Booking Confirmed!*

*Clinic:* {clinic.name}
*Patient:* {patient.name}
*Reference:* `{ref}`
*Hospital:* {hospital['name']}

Type NEW for another consultation."""
    
    else:
        valid_options = ", ".join(HOSPITALS.keys())
        return f"❌ Invalid selection. Please reply: {valid_options}"

def handle_confirmed(msg, phone, patient, context, clinic):
    msg_upper = msg.upper()
    
    if msg_upper == "NEW":
        update_state(phone, "greeting", {}, clinic_id=clinic.id)
        return f"🏥 Welcome to {clinic.name}!\n\nMay I know your name please?"
    
    elif "status" in msg.lower():
        db = get_db()
        recent = db.query(Consultation).filter_by(patient_phone=phone, clinic_id=clinic.id).order_by(Consultation.created_at.desc()).first()
        
        if recent:
            return f"📋 *Last Consultation*\nReference: `{recent.reference_number}`\n\nType NEW for new consultation."
        else:
            return "No consultations found. Type NEW to start."
    
    return "Type NEW to start fresh."