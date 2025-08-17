from flask import render_template, url_for, flash, redirect, Blueprint, abort, request
from GrandBridge.models import db, Staff
from flask_login import login_required, current_user
from GrandBridge.community.forms import StaffForm

community = Blueprint('community', __name__)

@community.route("/support", methods=['GET'])
@login_required
def all_staffs():
    staffs = Staff.query.all()
    return render_template('support.html', staffs=staffs, user=current_user)

@community.route("/support/add_staff", methods=['GET', 'POST'])
@login_required
def add_staff():
    if current_user.is_admin:
        form = StaffForm()
        if form.validate_on_submit():
            staff = Staff(
                name = form.name.data,
                organisation = form.organisation.data,
                tel = form.tel.data,
                email = form.email.data,
                intro = form.intro.data
            )
            db.session.add(staff)
            db.session.commit()
            
            flash('Staff added', 'success')
            return redirect(url_for('community.all_staffs'))
        return render_template('add_staff.html', form=form)
    else:
        flash('You cannot add new staff', 'danger')
        return redirect(url_for('community.all_staffs'))