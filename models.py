# models.py - Database Models
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import json

Base = declarative_base()

class Patient(Base):
    __tablename__ = "patients"
    
    id = Column(Integer, primary_key=True)
    phone = Column(String, unique=True, index=True)
    name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_visit = Column(DateTime)
    
    def to_dict(self):
        return {
            "id": self.id,
            "phone": self.phone,
            "name": self.name,
            "last_visit": self.last_visit.isoformat() if self.last_visit else None
        }

class Consultation(Base):
    __tablename__ = "consultations"
    
    id = Column(Integer, primary_key=True)
    patient_phone = Column(String, index=True)
    symptoms = Column(Text)
    ai_assessment = Column(Text)
    severity = Column(String)  # low, medium, high, emergency
    hospital_id = Column(String)
    status = Column(String, default="active")  # active, completed, referred
    reference_number = Column(String, unique=True)
    sha_claim_submitted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "reference": self.reference_number,
            "symptoms": self.symptoms,
            "severity": self.severity,
            "status": self.status,
            "created_at": self.created_at.isoformat()
        }

class ConversationState(Base):
    __tablename__ = "conversation_states"
    
    id = Column(Integer, primary_key=True)
    phone = Column(String, unique=True, index=True)
    state = Column(String, default="greeting")  # greeting, name, symptoms, triage, hospital, confirm
    data = Column(Text, default="{}")  # JSON storage
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Database setup
engine = create_engine("sqlite:///wca_pro.db", echo=False)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

def get_db():
    return Session()