from flask_wtf import FlaskForm
from wtforms import SubmitField, StringField, DateTimeField, TextAreaField, SelectMultipleField
from wtforms.validators import DataRequired, Optional
from wtforms.widgets import CheckboxInput, ListWidget
from GrandBridge.models import Family

class MultiCheckboxField(SelectMultipleField):
    """Custom field that renders as checkboxes instead of select multiple"""
    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()

class EventForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    start = DateTimeField('Start Time', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    end = DateTimeField('End Time', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    location = StringField('Location', validators=[Optional()])
    description = TextAreaField('Description')
    
    # Multiple family selection
    family_ids = MultiCheckboxField('Select Families', coerce=int, validators=[Optional()])
    
    submit = SubmitField('Done')
    
    def __init__(self, *args, **kwargs):
        super(EventForm, self).__init__(*args, **kwargs)
        # Populate family choices dynamically
        self.family_ids.choices = [(family.id, f"{family.name} (ID: {family.id})") 
                                   for family in Family.query.all()]

class EditEventForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    start = DateTimeField('Start Time', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    end = DateTimeField('End Time', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    location = StringField('Location', validators=[Optional()])
    description = TextAreaField('Description')
    
    # Multiple family selection
    family_ids = MultiCheckboxField('Select Families', coerce=int, validators=[Optional()])
    
    submit = SubmitField('Done')
    
    def __init__(self, *args, **kwargs):
        super(EditEventForm, self).__init__(*args, **kwargs)
        # Populate family choices dynamically
        self.family_ids.choices = [(family.id, f"{family.name} (ID: {family.id})") 
                                   for family in Family.query.all()]