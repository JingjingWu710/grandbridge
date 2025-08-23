from flask import render_template, url_for, flash, redirect, Blueprint, request
from GrandBridge.models import db
from GrandBridge.nutrition.forms import FoodForm
from GrandBridge.models import FoodEntry, FoodRecord
from flask_login import login_required, current_user
from openai import OpenAI
import os
from datetime import datetime


client = OpenAI(
    api_key=os.getenv('OPENAI_API_KEY')
)

nutrition = Blueprint('nutrition', __name__)

@nutrition.route('/add_food', methods=['GET', 'POST'])
@login_required
def add_food():
    form = FoodForm()
    error = None

    if request.method == 'POST':
        print("Form data received:", dict(request.form))
        
        # Validate basic form fields first
        if form.start_date.validate(form) and form.end_date.validate(form):
            start = form.start_date.data
            end = form.end_date.data

            if end < start:
                error = "End date cannot be before start date."
            else:
                # Process food items directly from request.form
                # Find all item indices (handle gaps in numbering)
                item_indices = set()
                for key in request.form.keys():
                    if key.startswith('items-') and '-food_name' in key:
                        try:
                            index = int(key.split('-')[1])
                            item_indices.add(index)
                        except ValueError:
                            continue
                
                food_items = []
                for i in sorted(item_indices):
                    food_name = request.form.get(f'items-{i}-food_name')
                    amount = request.form.get(f'items-{i}-amount')
                    unit = request.form.get(f'items-{i}-unit')
                    
                    # Validate individual item
                    if food_name and food_name.strip() and amount:
                        try:
                            amount_float = float(amount)
                            if amount_float > 0:
                                food_items.append({
                                    'food_name': food_name.strip(),
                                    'amount': amount_float,
                                    'unit': unit
                                })
                            else:
                                error = f"Amount for '{food_name}' must be greater than 0."
                                break
                        except ValueError:
                            error = f"Invalid amount for '{food_name}'. Please enter a valid number."
                            break
                    else:
                        error = f"Please fill in all fields for '{food_name or 'item'}'"
                        break
                
                if not error and food_items:
                    try:
                        record = FoodRecord(user_id=current_user.id)
                        db.session.add(record)
                        db.session.flush()  # Get the record ID

                        for item in food_items:
                            entry = FoodEntry(
                                food_name=item['food_name'],
                                start_date=start,
                                end_date=end,
                                amount=item['amount'],
                                unit=item['unit'],
                                user_id=current_user.id,
                                record=record
                            )
                            db.session.add(entry)

                        # Prepare prompt content
                        duration = (end - start).days + 1
                        food_list_text = "\n".join([
                            f"- {item['amount']} {item['unit']} of {item['food_name']}" 
                            for item in food_items
                        ])

                        # Create a more detailed prompt for better GPT responses
                        prompt_text = f"""
                        Food Diary Analysis:
                        
                        Duration: {duration} day(s) (from {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')})
                        
                        Foods consumed:
                        {food_list_text}
                        
                        Please provide:
                        1. Nutritional analysis of these foods (estimated calories, macronutrients, key vitamins/minerals)
                        2. Assessment of dietary balance and any nutritional gaps
                        3. Specific dietary advice and recommendations for improvement
                        4. A suggested balanced daily menu that complements these foods
                        5. Any health considerations or warnings if applicable
                        
                        Keep the response concise but informative (under 300 words).
                        """

                        # Call OpenAI API (for OpenAI library v1.0+)
                        try:
                            response = client.chat.completions.create(
                                model="gpt-3.5-turbo", 
                                messages=[
                                    {"role": "system", "content": "You are a professional nutritionist providing personalized dietary advice based on food consumption data."},
                                    {"role": "user", "content": prompt_text}
                                ],
                                max_tokens=500,
                                temperature=0.7,
                                top_p=0.9
                            )
                            
                            record.nutrition_advice = response.choices[0].message.content.strip()
                            
                        except Exception as e:
                            # Handle specific OpenAI errors
                            error_message = str(e)
                            if "rate_limit" in error_message.lower():
                                record.nutrition_advice = "API rate limit reached. Please try again later."
                                flash('Rate limit reached, but food entries were saved.', 'warning')
                            elif "authentication" in error_message.lower() or "api_key" in error_message.lower():
                                record.nutrition_advice = "Authentication failed. Please check API key."
                                flash('API authentication failed, but food entries were saved.', 'warning')
                            else:
                                record.nutrition_advice = f"Unable to generate advice: {error_message[:100]}"
                                flash('Could not generate advice, but food entries were saved.', 'warning')
                            print(f"OpenAI API error: {e}")

                        db.session.commit()
                        flash('All food entries added successfully!', 'success')
                        return redirect(url_for('nutrition.food_record'))

                    except Exception as e:
                        db.session.rollback()
                        error = f"An error occurred while saving: {str(e)}"
                        print(f"Database error: {e}")
                
                elif not error and not food_items:
                    error = "Please add at least one food item."
        else:
            # Handle form validation errors for date fields
            if form.start_date.errors:
                error = f"Start date error: {form.start_date.errors[0]}"
            elif form.end_date.errors:
                error = f"End date error: {form.end_date.errors[0]}"
            else:
                error = "Please check your date entries."

    print("Form not submitted successfully")
    return render_template('add_food.html', form=form, error=error)


@nutrition.route("/food_record", methods=['GET'])
@login_required
def food_record():
    records = FoodRecord.query.\
        join(FoodRecord.entries).\
        filter(FoodEntry.user_id == current_user.id).\
        options(db.joinedload(FoodRecord.entries)).\
        all()
    return render_template('food_record.html', records=records)

@nutrition.route("/delete_record/<int:record_id>", methods=['POST'])
@login_required
def delete_record(record_id):
    record = FoodRecord.query.get_or_404(record_id)
    
    # Security check: ensure the user owns this record
    if record.user_id != current_user.id:
        flash('You do not have permission to delete this record.', 'danger')
        return redirect(url_for('nutrition.food_record'))
    
    try:
        db.session.delete(record)
        db.session.commit()
        flash('Food record deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting record: {str(e)}', 'danger')
    
    return redirect(url_for('nutrition.food_record'))