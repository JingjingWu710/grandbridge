from flask import render_template, url_for, flash, redirect, Blueprint, abort, request
from GrandBridge.models import db, Staff
from flask_login import login_required, current_user
from GrandBridge.community.forms import StaffForm

community = Blueprint('community', __name__)

@community.route("/support/add_staff", methods=['GET', 'POST'])
@login_required
def add_staff():
    if not current_user.is_admin:
        flash('You cannot add new staff', 'danger')
        return redirect(url_for('community.all_staffs'))
    
    form = StaffForm()
    
    if form.validate_on_submit():
        # Create new staff with all fields
        staff = Staff(
            name=form.name.data,
            organisation=form.organisation.data,
            role_type=form.role_type.data,  # This was missing!
            tel=form.tel.data,
            email=form.email.data,
            intro=form.intro.data,
            specializations=form.specializations.data or '',
            languages_spoken=form.languages_spoken.data or 'English',
            availability_hours=form.availability_hours.data or '',
            emergency_contact=form.emergency_contact.data,
            age_groups=form.age_groups.data or '',
            service_areas=form.service_areas.data or '',
            training_certifications=form.training_certifications.data or ''
        )
        
        db.session.add(staff)
        db.session.commit()
        
        flash(f'Staff member {form.name.data} has been added successfully!', 'success')
        return redirect(url_for('community.all_staffs'))
    
    return render_template('add_staff.html', form=form, user=current_user)


# Updated all_staffs route to handle the new fields and filtering
@community.route("/support", methods=['GET'])
@login_required
def all_staffs():
    # Get filter parameters
    role_filter = request.args.get('role', 'all')
    emergency_only = request.args.get('emergency', False)
    
    # Build query
    query = Staff.query
    
    if role_filter != 'all':
        query = query.filter_by(role_type=role_filter)
    
    if emergency_only:
        query = query.filter_by(emergency_contact=True)
    
    staffs = query.all()
    
    # Get emergency staff for quick help section
    emergency_staff = Staff.query.filter_by(emergency_contact=True).all() if hasattr(Staff, 'emergency_contact') else []
    
    # Group staff by role for display
    staff_by_role = {}
    for staff in staffs:
        role = getattr(staff, 'role_type', 'social_worker')
        if role not in staff_by_role:
            staff_by_role[role] = []
        staff_by_role[role].append(staff)
    
    # Count total staff
    staff_count = len(staffs)
    
    return render_template('support.html', 
                         staff_by_role=staff_by_role,
                         emergency_staff=emergency_staff,
                         staff_count=staff_count,
                         user=current_user)