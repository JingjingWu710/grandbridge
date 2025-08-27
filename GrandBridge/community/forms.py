from flask_wtf import FlaskForm
from wtforms import SubmitField, StringField, TextAreaField
from wtforms.validators import DataRequired, Email

class StaffForm(FlaskForm):
    name = StringField('Name:',
                       validators=[DataRequired()])
    organisation = StringField('Organisation:',
                               validators=[DataRequired()])
    tel = StringField('Telephone number:',
                      validators=[DataRequired()])
    email = StringField('Email address:',
                        validators=[DataRequired(),Email()])
    intro = TextAreaField('Introduction:')
    submit = SubmitField('Submit')