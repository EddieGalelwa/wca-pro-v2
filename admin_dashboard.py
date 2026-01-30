# admin_dashboard.py - Master Control Center
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from models import get_db, Clinic, Patient, ConversationState, Consultation
from datetime import datetime
import os
import secrets

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "afyacare-super-secret-key-change-in-production")

# ==================== ADMIN ROUTES ====================

@app.route("/admin")
def admin_panel():
    """Main dashboard - show all clinics"""
    db = get_db()
    clinics = db.query(Clinic).order_by(Clinic.created_at.desc()).all()
    
    # Calculate stats for each clinic
    clinic_data = []
    for clinic in clinics:
        patient_count = db.query(Patient).filter_by(clinic_id=clinic.id).count()
        msg_count = db.query(ConversationState).filter(
            ConversationState.clinic_id == clinic.id,
            ConversationState.updated_at >= datetime.utcnow().date()
        ).count()
        
        clinic_data.append({
            "clinic": clinic,
            "patients": patient_count,
            "today_messages": msg_count
        })
    
    return render_template("admin_panel.html", clinic_data=clinic_data)

@app.route("/admin/create", methods=["GET", "POST"])
def create_clinic():
    """Create new clinic"""
    if request.method == "POST":
        try:
            db = get_db()
            
            # Generate unique clinic ID
            clinic_id = f"clinic_{secrets.token_hex(4)}"
            
            clinic = Clinic(
                id=clinic_id,
                name=request.form.get("name"),
                phone=request.form.get("phone"),
                contact_person=request.form.get("contact_person"),
                contact_email=request.form.get("contact_email"),
                plan=request.form.get("plan", "starter"),
                is_active=True,
                created_at=datetime.utcnow()
            )
            
            db.add(clinic)
            db.commit()
            
            flash(f"✅ Clinic '{clinic.name}' created successfully! ID: {clinic_id}", "success")
            return redirect(url_for("admin_panel"))
            
        except Exception as e:
            flash(f"❌ Error creating clinic: {str(e)}", "error")
            return redirect(url_for("create_clinic"))
    
    return render_template("create_clinic.html")

@app.route("/admin/clinic/<clinic_id>")
def view_clinic(clinic_id):
    """View single clinic details"""
    db = get_db()
    clinic = db.query(Clinic).get(clinic_id)
    
    if not clinic:
        flash("Clinic not found", "error")
        return redirect(url_for("admin_panel"))
    
    # Get stats
    patients = db.query(Patient).filter_by(clinic_id=clinic_id).count()
    consultations = db.query(Consultation).filter_by(clinic_id=clinic_id).count()
    active_conversations = db.query(ConversationState).filter_by(
        clinic_id=clinic_id
    ).count()
    
    return render_template("clinic_details.html", 
                         clinic=clinic,
                         patients=patients,
                         consultations=consultations,
                         active_conversations=active_conversations)

@app.route("/admin/clinic/<clinic_id>/toggle")
def toggle_clinic(clinic_id):
    """Activate/deactivate clinic"""
    db = get_db()
    clinic = db.query(Clinic).get(clinic_id)
    
    if clinic:
        clinic.is_active = not clinic.is_active
        db.commit()
        status = "activated" if clinic.is_active else "deactivated"
        flash(f"Clinic {clinic.name} {status}", "success")
    
    return redirect(url_for("admin_panel"))

@app.route("/admin/clinic/<clinic_id>/reset")
def reset_clinic(clinic_id):
    """Clear all data for a clinic (dangerous - for testing only)"""
    db = get_db()
    
    # Delete all patient data for this clinic
    db.query(Patient).filter_by(clinic_id=clinic_id).delete()
    db.query(ConversationState).filter_by(clinic_id=clinic_id).delete()
    db.query(Consultation).filter_by(clinic_id=clinic_id).delete()
    db.commit()
    
    flash(f"🚨 All data cleared for clinic {clinic_id}", "warning")
    return redirect(url_for("admin_panel"))

# ==================== RUN THE APP ====================
if __name__ == "__main__":
    app.run(debug=True, port=5001)  # Run on port 5001 to avoid conflicts