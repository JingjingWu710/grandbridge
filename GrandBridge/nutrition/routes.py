from flask import render_template, url_for, flash, redirect, Blueprint, request
from GrandBridge.models import db
from GrandBridge.nutrition.forms import FoodForm
from GrandBridge.models import FoodEntry, FoodRecord
from transformers import pipeline
from flask_login import login_required, current_user


# Load pipeline once (at module level)
gpt2_pipe = pipeline("text-generation", model="openai-community/gpt2")


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
                            f"- {item['amount']} {item['unit']} of {item['food_name']}" for item in food_items
                        ])

                        prompt_text = (
                            f"The user recorded the following food consumption over {duration} days:\n"
                            f"{food_list_text}\n\n"
                            "Please analyze the nutrition intake, give dietary advice, "
                            "and recommend a balanced daily menu based on the above."
                        )

                        # Use local transformers pipeline
                        result = gpt2_pipe(prompt_text, max_new_tokens=200, do_sample=True, temperature=0.7)

                        if isinstance(result, list) and "generated_text" in result[0]:
                            record.nutrition_advice = result[0]["generated_text"]
                        else:
                            record.nutrition_advice = "Unable to generate advice at this time."

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