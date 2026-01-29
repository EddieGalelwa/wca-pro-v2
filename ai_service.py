# ai_service.py - AI Triage Service
from openai import OpenAI
from config import OPENAI_API_KEY, OPENAI_MODEL, MAX_TOKENS, TEMPERATURE
import json
import re

client = OpenAI(api_key=OPENAI_API_KEY)

def analyze_symptoms(symptom_text, patient_name="Patient"):
    """
    Real AI triage using OpenAI GPT-3.5
    Returns: dict with severity, assessment, recommendation, hospital_needed
    """
    
    prompt = f"""You are a medical triage assistant for a Kenyan clinic. Analyze the patient's symptoms and provide a structured assessment.

Patient Name: {patient_name}
Symptoms: "{symptom_text}"

Provide your response in this exact JSON format:
{{
    "severity": "low|medium|high|emergency",
    "confidence": 0.0-1.0,
    "assessment": "Brief medical assessment (2-3 sentences)",
    "recommended_action": "What patient should do next",
    "specialist_needed": "General|Cardiologist|Pediatrician|Dermatologist|Orthopedic|Other",
    "hospital_urgency": "routine|same-day|emergency",
    "sha_claim_eligible": true|false,
    "disclaimer": "This is not a medical diagnosis. Please consult a doctor for proper evaluation."
}}

Rules:
- Severity "emergency" only for: chest pain, severe bleeding, unconsciousness, severe breathing difficulty, poisoning
- SHA claim eligible for: consultations, lab tests, medications (not cosmetic procedures)
- Be empathetic but professional
- Use simple language patients can understand"""

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a professional medical triage assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        
        # Validate required fields
        required = ["severity", "assessment", "recommended_action", "hospital_urgency"]
        for field in required:
            if field not in result:
                result[field] = "unknown"
        
        return result
        
    except Exception as e:
        print(f"AI Service Error: {e}")
        # Fallback response
        return {
            "severity": "medium",
            "confidence": 0.5,
            "assessment": "Unable to fully analyze symptoms due to technical issue.",
            "recommended_action": "Please visit the nearest hospital for proper evaluation.",
            "specialist_needed": "General",
            "hospital_urgency": "same-day",
            "sha_claim_eligible": True,
            "disclaimer": "This is not a medical diagnosis. Please consult a doctor."
        }

def generate_response(message_history, current_state, context=None):
    """
    Generate contextual response based on conversation state
    """
    context = context or {}
    
    system_prompt = f"""You are WCA Pro, a WhatsApp clinic assistant for {context.get('clinic_name', 'AfyaCare Medical Center')} in Kenya.
    
Current conversation state: {current_state}
Patient context: {json.dumps(context)}

Guidelines:
- Be warm, professional, and concise (WhatsApp-friendly)
- Always guide patients toward the next step
- For emergencies, insist on immediate hospital visit
- Mention SHA (Social Health Authority) claims when relevant
- Use emojis sparingly for clarity

Respond in 2-3 short sentences maximum."""

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                *message_history[-3:],  # Last 3 messages for context
            ],
            max_tokens=200,
            temperature=0.4
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"Response Generation Error: {e}")
        return "I'm here to help. Could you please tell me your symptoms so I can assist you better?"