from flask import render_template, url_for, flash, redirect, request, Blueprint
from GrandBridge import db, bcrypt
from GrandBridge.users.forms import RegistrationForm, LoginForm, UpdateAccountForm, UpdateAdminAccountForm ,CreateFamilyForm, EditFamilyForm
from GrandBridge.models import User, Family
from flask_login import login_user, current_user, logout_user, login_required

users = Blueprint('users', __name__)

@users.route("/register", methods=['GET', 'POST'])
def register():
    # if current_user.is_authenticated:
    #     return redirect(url_for('main.home'))

    form = RegistrationForm()

    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        is_admin = form.is_admin.data
        if not is_admin:
            family_id_input = form.family_id.data if form.family_id.data else None

            family = None
            if family_id_input:
                # Try finding an existing family by id
                family = Family.query.filter_by(id=family_id_input).first()
                if not family:
                    # Create new family with provided id
                    family = Family(id=family_id_input, name=form.username.data)
                    db.session.add(family)
            else:
                # Create a new family without a provided id
                family = Family(name=form.username.data)
                db.session.add(family)
                db.session.flush()  # so family.id is generated

            user = User(
                username=form.username.data,
                email=form.email.data,
                password=hashed_password,
                is_admin=is_admin,
                family_id=family.id
            )
        else:
            user = User(
                username=form.username.data,
                email=form.email.data,
                password=hashed_password,
                is_admin=is_admin,
            )

        db.session.add(user)
        db.session.commit()

        flash('Your account has been created!', 'success')
        return redirect(url_for('users.login'))

    return render_template('register.html', title='Register', form=form)


@users.route("/login", methods=['GET','POST'])
def login():
    # if current_user.is_authenticated:
    #     return redirect(url_for('main.home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            flash('Login Successful!', 'success')
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            else:
                return redirect(url_for('main.home'))
        else:
            flash('Login Unsuccessful. Please check email and password.', 'danger')
    return render_template('login.html', title='Login', form=form)

@users.route("/logout")
def logout():
    logout_user()
    flash('You have logged out.', 'info')
    return redirect(url_for('main.home'))

@users.route("/account", methods=['GET','POST'])
@login_required
def account():
    if current_user.is_admin:
        form = UpdateAdminAccountForm()
    else:
        form = UpdateAccountForm()
        
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.email = form.email.data
        
        if not current_user.is_admin:
            family_id_input = form.family_id.data.strip() if form.family_id.data else None
            
            if family_id_input:
                # User wants to join an existing family by ID
                family = Family.query.filter_by(id=family_id_input).first()
                
                if family:
                    # Family exists - join it
                    current_user.family_id = family.id
                    flash(f"You have joined family '{family.name}' (ID: {family.id}).", "success")
                else:
                    # Family with this ID doesn't exist - show error
                    flash(f'No family found with ID {family_id_input}. Leave Family ID blank to create a new family with your username.', 'danger')
                    return redirect(url_for('users.account'))
            else:
                # No family ID provided - create new family with username
                family = Family(name=current_user.username)
                db.session.add(family)
                db.session.flush()  # Get the auto-generated ID
                
                current_user.family_id = family.id
                flash(f"New family '{family.name}' created with ID {family.id}. You are now a member!", "success")
            
            # Update other user fields
            current_user.address = form.address.data
            current_user.contact_info = form.contact_info.data
            
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('users.account'))
        
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
        if not current_user.is_admin:
            form.family_id.data = current_user.family_id
            form.address.data = current_user.address
            form.contact_info.data = current_user.contact_info
    
    # Prepare family information for normal users
    family_info = None
    if not current_user.is_admin and current_user.family_id:
        user_family = Family.query.get(current_user.family_id)
        if user_family:
            # Get all family members (including current user)
            family_members = User.query.filter_by(family_id=current_user.family_id, is_admin=False).all()
            
            # Get family admins (users who have this family in their admin_families)
            family_admins = User.query.filter(
                User.is_admin == True,
                User.admin_families.any(Family.id == current_user.family_id)
            ).all()
            
            family_info = {
                'family': user_family,
                'members': family_members,
                'admins': family_admins
            }
            
    return render_template('account.html', title='Account', form=form, family_info=family_info)

@users.route("/account/delete", methods=['POST'])
@login_required
def delete_account():
    account = User.query.filter_by(id=current_user.id).first_or_404()
    
    logout_user()  # Log out the user BEFORE deleting the account
    
    db.session.delete(account)
    db.session.commit()
    
    flash('Your account has been deleted.', 'success')
    return redirect(url_for('users.login'))

@users.route("/create_family", methods=['GET', 'POST'])
@login_required
def create_family():
    if not current_user.is_admin:
        flash("You do not have permission to create a family.", "danger")
        return redirect(url_for('main.home'))

    form = CreateFamilyForm()
    if form.validate_on_submit():
        name = form.name.data.strip()
        provided_id = form.id.data
        
        if provided_id:
            # User wants to join an existing family by ID
            family = Family.query.filter_by(id=provided_id).first()
            
            if family:
                # Family exists - join as admin
                if family not in current_user.admin_families:
                    current_user.admin_families.append(family)
                    db.session.commit()
                    flash(f"You have been added as an admin for existing family (ID: {family.id}) You may change its name on this page.", "success")
                else:
                    flash(f"You are already an admin for family '{family.name}' (ID: {family.id}). You may update its name on 'All Families' Page.", "info")
            else:
                # Family with this ID doesn't exist - show error
                flash(f'No family found with ID {provided_id}. Leave ID blank to create a new family.', 'danger')
                return redirect(url_for('users.create_family'))
        else:
            # No ID provided - create new family
            family = Family(name=name)
            db.session.add(family)
            db.session.flush()
            
            current_user.admin_families.append(family)
            db.session.commit()
            flash(f"New family '{name}' created with ID {family.id}. You are its admin!", "success")
        
        return redirect(url_for('users.all_families'))

    return render_template('create_family.html', title='Create Family', form=form)

@users.route("/edit_family/<int:family_id>", methods=['GET', 'POST'])
@login_required
def edit_family(family_id):
    if not current_user.is_admin:
        flash("You do not have permission to edit this family.", "danger")
        return redirect(url_for('main.home'))

    family = Family.query.get_or_404(family_id)
    
    # Ensure current user is admin for this family
    if family not in current_user.admin_families:
        flash("You do not have permission to edit this family.", "danger")
        return redirect(url_for('main.home'))

    form = EditFamilyForm()
    
    if form.validate_on_submit():
        family.name = form.name.data.strip()
        
        db.session.commit()
        flash(f"Family '{family.name}' updated successfully!", "success")
        return redirect(url_for('users.all_families'))
    
    elif request.method == 'GET':
        form.name.data = family.name
        
        
    return render_template('edit_family.html', title='Edit Family', form=form, family=family)

@users.route("/remove_admin/<int:family_id>", methods=['POST'])
@login_required
def remove_admin(family_id):
    family = Family.query.get_or_404(family_id)

    # Ensure current user is an admin for this family
    if not current_user.admin_families.filter_by(id=family.id).first():
        flash("You do not have permission to remove yourself as an admin from this family.", "danger")
        return redirect(url_for('main.home'))

    # Remove the admin relationship
    current_user.admin_families.remove(family)
    db.session.commit()

    flash(f"You are no longer an admin for '{family.name}'.", "success")
    return redirect(url_for('users.all_families'))


@users.route("/all_families")
@login_required
def all_families():
    if not current_user.is_admin:
        flash("You do not have permission to view this page.", "danger")
        return redirect(url_for('main.home'))
    
    # Assuming current_user.admin_families relationship exists
    families = current_user.admin_families.all()
    return render_template('all_families.html', families=families)


    

