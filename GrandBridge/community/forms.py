from flask_wtf import FlaskForm
from wtforms import SubmitField, StringField, TextAreaField, SelectField, BooleanField
from wtforms.validators import DataRequired, Email, Optional

class StaffForm(FlaskForm):
    name = StringField('Name:', validators=[DataRequired()])
    organisation = StringField('Organisation:', validators=[DataRequired()])
    
    role_type = SelectField('Role Type:', 
                           choices=[
                               ('social_worker', 'Social Worker'),
                               ('psychologist', 'Child Psychologist'),
                               ('education_officer', 'Education Officer'),
                               ('health_visitor', 'Health Visitor'),
                               ('family_support', 'Family Support Worker'),
                               ('legal_advisor', 'Legal Advisor'),
                               ('emergency_responder', 'Emergency Response Team')
                           ],
                           validators=[DataRequired()])
    
    tel = StringField('Telephone number:', validators=[DataRequired()])
    email = StringField('Email address:', validators=[DataRequired(), Email()])
    
    specializations = TextAreaField('Specializations (e.g., behavioral issues, educational support):')
    languages_spoken = StringField('Languages Spoken:')
    availability_hours = StringField('Availability Hours (e.g., Mon-Fri 9am-5pm):')
    emergency_contact = BooleanField('Available for emergencies')
    age_groups = StringField('Age Groups Served:', 
                           validators=[Optional()])
    service_areas = TextAreaField('Service Areas/Communities:')
    training_certifications = TextAreaField('Relevant Training & Certifications:')
    intro = TextAreaField('Introduction:')
    submit = SubmitField('Submit')