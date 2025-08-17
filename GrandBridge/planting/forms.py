from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, RadioField, SubmitField
from wtforms.validators import DataRequired, Length, Optional

class VegetableForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=50)])
    type = SelectField('Type', validators=[DataRequired()], choices=[])
    note = TextAreaField('Note', validators=[Optional(), Length(max=500)])
    
    # ADD THESE TWO FIELDS:
    intention = RadioField('What does this represent?',
                         choices=[
                             ('', 'Just planting'),
                             ('self care', '🌸 Self-Care - I took care of myself'),
                             ('helped', '🤝 Helping - I helped someone'),
                             ('overcame', '💪 Overcame - I handled a challenge'),
                             ('grateful', '💚 Gratitude - Something I appreciate'),
                             ('rest', '😌 Rest - I allowed myself to rest'),
                             ('connection', '👥 Connection - I connected with someone')
                         ],
                         default='',
                         validators=[Optional()])
    
    mood = RadioField('How are you feeling?',
                     choices=[
                         ('5', '😊 Great'),
                         ('4', '🙂 Good'),
                         ('3', '😐 Okay'),
                         ('2', '😟 Difficult'),
                         ('1', '😔 Struggling')
                     ],
                     validators=[Optional()])
    
    submit = SubmitField('Plant')