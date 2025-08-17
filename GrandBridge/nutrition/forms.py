from flask_wtf import FlaskForm
from wtforms import StringField, DateField, SubmitField, FieldList, FormField, FloatField, SelectField
from wtforms.validators import DataRequired

class FoodItemForm(FlaskForm):
    food_name = StringField('Food Name', validators=[DataRequired()])
    amount = FloatField('Amount', validators=[DataRequired()])
    unit = SelectField('Unit', choices=[
        ('g', 'g'), ('kg', 'kg'),
        ('ml', 'ml'), ('l', 'l'),
        ('pieces', 'pieces'), ('tbsp', 'tbsp'), ('tsp', 'tsp')
    ], validators=[DataRequired()])

class FoodForm(FlaskForm):
    items = FieldList(FormField(FoodItemForm), min_entries=1)
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('End Date', validators=[DataRequired()])
    submit = SubmitField('Submit All')