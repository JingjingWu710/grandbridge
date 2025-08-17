from flask_wtf import FlaskForm
from flask_login import current_user
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectField, IntegerField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Optional
from GrandBridge.models import User

class RegistrationForm(FlaskForm):
    def str_to_bool(value):
        return str(value).lower() == "true"
    username = StringField('Full Name', 
                           validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email for Login',
                        validators=[DataRequired(),Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', 
                                     validators=[DataRequired(), EqualTo('password')])
    family_id = IntegerField('Family ID', validators=[Optional()])


    is_admin = SelectField(
        'Are you a community admin?',
        choices=[
            ('false', 'No'),
            ('true', 'Yes')
        ],
        coerce=str_to_bool
    )

    submit = SubmitField('Sign up')
    
    # def validate_username(self, username):
    #     user = User.query.filter_by(username=username.data).first()
    #     if user:
    #         raise ValidationError('That username is taken')
    def validate_email(self, email):
        email = User.query.filter_by(email=email.data).first()
        if email:
            raise ValidationError('That email is taken')
        
class LoginForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(),Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Log In')
    
class UpdateAccountForm(FlaskForm):
    username = StringField('Full Name', 
                           validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email for Login',
                        validators=[DataRequired(),Email()])
    address = StringField('Address', 
                           validators=[Optional()])
    contact_info = StringField('Contact Info', 
                           validators=[Optional()])
    family_id = StringField('Family ID', validators=[Optional()])
    submit = SubmitField('Update')
    
    # def validate_username(self, username):
    #     if username.data != current_user.username:
    #         user = User.query.filter_by(username=username.data).first()
    #         if user:
    #             raise ValidationError('That username is taken')
            
    def validate_email(self, email):
        if email.data != current_user.email:
            email = User.query.filter_by(email=email.data).first()
            if email:
                raise ValidationError('That email is taken')
            
class UpdateAdminAccountForm(FlaskForm):
    username = StringField('Full Name', 
                           validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email for Login',
                        validators=[DataRequired(),Email()])
    family_id = StringField('Family ID', validators=[Optional()])
    submit = SubmitField('Update')
    
    # def validate_username(self, username):
    #     if username.data != current_user.username:
    #         user = User.query.filter_by(username=username.data).first()
    #         if user:
    #             raise ValidationError('That username is taken')
            
    def validate_email(self, email):
        if email.data != current_user.email:
            email = User.query.filter_by(email=email.data).first()
            if email:
                raise ValidationError('That email is taken')

class CreateFamilyForm(FlaskForm):
    id = IntegerField('Family ID', validators=[Optional()])
    name = StringField('Family Name', validators=[DataRequired(), Length(min=2, max=50)])
    submit = SubmitField('Submit')

class EditFamilyForm(FlaskForm):
    name = StringField('Family Name', validators=[DataRequired(), Length(min=2, max=50)])
    submit = SubmitField('Submit')

            
            