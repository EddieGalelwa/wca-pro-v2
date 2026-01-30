# models.py - Multi-Clinic Database Models
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import json

Base = declarative_base()

# ==================== NEW CLINIC MODEL ====================
class Clinic(Base):
    __tablename__ = "clinics"
    
    id = Column(String(50), primary_key=True)
    name = Column(String(200), nullable=False)
    phone = Column(String(20))  # Official WhatsApp number
    contact_person = Column(String(100))
    contact_email = Column(String(100))
    plan = Column(String(20), default="starter")  # starter, professional, enterprise
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    patients = relationship("Patient", back_populates="clinic", cascade="all, delete-orphan")
    consultations = relationship("Consultation", back_populates="clinic", cascade="all, delete-orphan")

# ==================== UPDATED PATIENT MODEL ====================
class Patient(Base):
    __tablename__ = "patients"
    
    id = Column(Integer, primary_key=True)
    clinic_id = Column(String(50), ForeignKey("clinics.id"), nullable=False)  # NEW: Clinic isolation
    phone = Column(String, index=True)  # REMOVED: unique constraint (patients can exist in multiple clinics)
    name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_visit = Column(DateTime)
    
    # Relationships
    clinic = relationship("Clinic", back_populates="patients")
    
    def to_dict(self):
        return {
            "id": self.id,
            "clinic_id": self.clinic_id,
            "phone": self.phone,
            "name": self.name,
            "last_visit": self.last_visit.isoformat() if self.last_visit else None
        }

# ==================== UPDATED CONSULTATION MODEL ====================
class Consultation(Base):
    __tablename__ = "consultations"
    
    id = Column(Integer, primary_key=True)
    clinic_id = Column(String(50), ForeignKey("clinics.id"), nullable=False)  # NEW: Clinic isolation
    patient_phone = Column(String, index=True)
    symptoms = Column(Text)
    ai_assessment = Column(Text)
    severity = Column(String)  # low, medium, high, emergency
    hospital_id = Column(String)
    status = Column(String, default="active")  # active, completed, referred
    reference_number = Column(String, unique=True)
    sha_claim_submitted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    clinic = relationship("Clinic", back_populates="consultations")
    
    def to_dict(self):
        return {
            "id": self.id,
            "clinic_id": self.clinic_id,
            "reference": self.reference_number,
            "symptoms": self.symptoms,
            "severity": self.severity,
            "status": self.status,
            "created_at": self.created_at.isoformat()
        }

# ==================== UPDATED CONVERSATION STATE ====================
class ConversationState(Base):
    __tablename__ = "conversation_states"
    
    id = Column(Integer, primary_key=True)
    clinic_id = Column(String(50), ForeignKey("clinics.id"), nullable=False)  # NEW: Clinic isolation
    phone = Column(String, index=True)  # REMOVED: unique constraint (conversations per clinic)
    state = Column(String, default="greeting")  # greeting, name, symptoms, triage, hospital, confirm
    data = Column(Text, default="{}")  # JSON storage
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# ==================== DATABASE SETUP ====================
engine = create_engine("sqlite:///wca_pro.db", echo=False)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

def get_db():
    """Get database session"""
    return Session()

def init_db():
    """Initialize database tables"""
    engine = create_engine("sqlite:///wca_pro.db", echo=False)
    Base.metadata.create_all(engine)
    print("✅ Database initialized with multi-clinic support!")

def get_patient(phone, clinic_id):
    """Get or create patient for specific clinic"""
    db = get_db()
    patient = db.query(Patient).filter_by(phone=phone, clinic_id=clinic_id).first()
    
    if not patient:
        patient = Patient(phone=phone, clinic_id=clinic_id)
        db.add(patient)
        db.commit()
        db.refresh(patient)
    
    return patient

def get_or_create_state(phone, clinic_id):
    """Get or create conversation state for specific clinic"""
    db = get_db()
    state = db.query(ConversationState).filter_by(phone=phone, clinic_id=clinic_id).first()
    
    if not state:
        state = ConversationState(phone=phone, clinic_id=clinic_id, state="greeting", data="{}")
        db.add(state)
        db.commit()
        db.refresh(state)
    
    return state