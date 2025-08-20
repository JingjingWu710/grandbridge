from flask import render_template, url_for, flash, redirect, Blueprint, abort, request, jsonify
from GrandBridge.models import db, Vegetable, Achievement, User, MindfulnessLog, DailyCheckIn
from GrandBridge.planting.forms import VegetableForm
from datetime import datetime, date, timedelta
from sqlalchemy import func
import random

from flask_login import login_required, current_user

planting = Blueprint('planting', __name__)

MINDFULNESS_ACTIVITIES = {
    "breathing": {
        "name": "Breathing Exercise",
        "icon": "🌬️",
        "activities": [
            {
                "id": "478",
                "name": "4-7-8 Breathing",
                "description": "Inhale for 4, hold for 7, exhale for 8 seconds",
                "duration": 3,
                "coins_reward": 5
            }
        ]
    }
}

CAREGIVER_AFFIRMATIONS = [
    "Your love bridges the distance and gives these children stability.",
    "It's okay to feel tired - raising grandchildren takes incredible strength.",
    "Your wisdom and patience are exactly what they need right now.",
    "Every day you provide them with a home is a gift of security.",
    "You are enough, even when the days feel overwhelming."
]

ALL_VEGETABLES = [
    {"key": "carrot", "name": "Carrot", "image": "pics/carrot.png"},
    {"key": "potato", "name": "Potato", "image": "pics/potato.png"},
    {"key": "spinach", "name": "Spinach", "image": "pics/spinach.png"},
    {"key": "cabbage", "name": "Cabbage", "image": "pics/cabbage.png"},
    {"key": "tomato", "name": "Tomato", "image": "pics/tomato.png"},
    {"key": "lettuce", "name": "Lettuce", "image": "pics/lettuce.png"},
    {"key": "broccoli", "name": "Broccoli", "image": "pics/broccoli.png"},
    {"key": "eggplant", "name": "Eggplant", "image": "pics/eggplant.png"},
    {"key": "corn", "name": "Corn", "image": "pics/corn.png"},
    {"key": "pepper", "name": "Pepper", "image": "pics/pepper.png"},
]

@planting.route("/plant_breathe/<int:veg_id>")
@login_required
def plant_breathe(veg_id):
    """Integrated planting and breathing page"""
    veg = Vegetable.query.get_or_404(veg_id)
    
    if veg.userid != current_user.id:
        abort(403)
    
    # Only allow this for vegetables that haven't been harvested
    if veg.harvested:
        flash('This plant has already been harvested!', 'warning')
        return redirect(url_for('planting.view_vegetable', veg_id=veg_id))
    
    return render_template("plant_breathe.html", veg=veg)

# @planting.route("/mindfulness")
# @login_required
# def mindfulness_home():
#     """Simple mindfulness homepage"""
#     return render_template("mindfulness_home.html", 
#                          activities=MINDFULNESS_ACTIVITIES)

@planting.route("/complete_mindfulness/<activity_type>/<activity_id>", methods=["POST"])
@login_required
def complete_mindfulness(activity_type, activity_id):
    """Complete a mindfulness activity with tracking"""
    
    # Find the activity details
    activity = None
    if activity_type in MINDFULNESS_ACTIVITIES:
        for act in MINDFULNESS_ACTIVITIES[activity_type]["activities"]:
            if act["id"] == activity_id:
                activity = act
                break
    
    if not activity:
        flash('Activity not found', 'error')
        return redirect(url_for('planting.wellness_dashboard'))
    
    # Log the activity
    log = MindfulnessLog(
        user_id=current_user.id,
        activity_type=activity_type,
        activity_id=activity_id,
        duration_minutes=activity["duration"],
        coins_earned=activity["coins_reward"]
    )
    db.session.add(log)
    
    # Update user stats
    current_user.coins += activity["coins_reward"]
    current_user.total_mindful_minutes = (current_user.total_mindful_minutes or 0) + activity["duration"]
    
    # Update mindfulness streak
    today = date.today()
    if current_user.last_mindfulness_date != today:
        if current_user.last_mindfulness_date == today - timedelta(days=1):
            current_user.mindfulness_streak = (current_user.mindfulness_streak or 0) + 1
        else:
            current_user.mindfulness_streak = 1
        current_user.last_mindfulness_date = today
    
    db.session.commit()
    
    flash(f'Well done! You earned {activity["coins_reward"]} coins! 🎉', 'success')
    
    # Check for achievements
    if current_user.mindfulness_streak == 3:
        flash('Achievement Unlocked: 3-Day Mindfulness Streak! 🏆', 'success')
    
    return redirect(url_for('planting.wellness_dashboard'))

@planting.route("/planting", methods=['GET', 'POST'])
@login_required
def plant():
    user_vegs = [(v, v.capitalize()) for v in current_user.unlocked_vegetables]
    form = VegetableForm()
    form.type.choices = user_vegs

    if form.validate_on_submit():
        veg = Vegetable(
            name=form.name.data,
            type=form.type.data,
            plant_time=datetime.now(),
            note=form.note.data,
            intention=form.intention.data if form.intention.data else None,
            mood_before=int(form.mood.data) if form.mood.data else None,
            seed_image="pics/seed.png",
            sprout_image="pics/sprout.png",
            harvest_image="pics/harvest.png",
            userid=current_user.id
        )
        db.session.add(veg)
        db.session.commit()
        
        # Redirect directly to breathing exercise
        flash('Time to breathe life into your plant! 🌱', 'success')
        return redirect(url_for("planting.plant_breathe", veg_id=veg.id))
    
    affirmation = random.choice(CAREGIVER_AFFIRMATIONS)
    prompts = [
    "What moment with your grandchild brought you joy today?",
    "How did you help them feel loved and secure today?",
    "What tradition or memory did you share with them?",
    "How did you handle a challenging parenting moment today?",
    "What reminded you of their parents, and how did you navigate those feelings?"
]
    prompt = random.choice(prompts)
    
    return render_template("plant.html", 
                         form=form, 
                         affirmation=affirmation,
                         prompt=prompt)

@planting.route("/grow_with_breath/<int:veg_id>", methods=["POST"])
@login_required
def grow_with_breath(veg_id):
    """API endpoint to update vegetable growth during breathing"""
    veg = Vegetable.query.get_or_404(veg_id)
    
    if veg.userid != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403
    
    data = request.get_json()
    phase = data.get('phase')
    
    # Update vegetable stage based on breathing progress
    if phase == 'cycle_1_complete' and veg.stage == 'seed':
        veg.stage = 'sprout'
        message = "Your seed is sprouting with your breath! 🌱"
    elif phase == 'cycle_2_complete' and veg.stage == 'sprout':
        veg.stage = 'ready_to_harvest'
        message = "Your plant is growing strong! 🌿"
    elif phase == 'exercise_complete':
        # Complete the harvest
        veg.stage = 'harvest'
        veg.harvested = True
        veg.harvest_completed_at = datetime.now()
        
        # Update user stats
        user = User.query.get(current_user.id)
        user.plant_count = (user.plant_count or 0) + 1
        # user.last_plant_date = date.today()
        user.coins += 20  # Extra coins for breathing-integrated harvest
        
        # Update mindfulness stats
        user.total_mindful_minutes = (user.total_mindful_minutes or 0) + 1
        
        # Update mindfulness streak
        today = date.today()
        if user.last_mindfulness_date != today:
            if user.last_mindfulness_date == today - timedelta(days=1):
                user.mindfulness_streak = (user.mindfulness_streak or 0) + 1
            else:
                user.mindfulness_streak = 1
            user.last_mindfulness_date = today
        
        # Log the mindfulness activity
        mindfulness_log = MindfulnessLog(
            user_id=current_user.id,
            activity_type='breathing',
            activity_id='plant_breathing',
            duration_minutes=1,
            coins_earned=10
        )
        db.session.add(mindfulness_log)
        
        message = "Harvest complete! Your mindful breathing has nurtured this plant to perfection! 🌾✨"
        
        db.session.commit()
        
        # Check for achievements
        unlock = update_user_stats()
        
        return jsonify({
            "success": True,
            "stage": veg.stage,
            "message": message,
            "harvested": True,
            "coins_earned": 20,
            "total_coins": user.coins,
            "achievements": [{"name": a.name, "description": a.description} for a in unlock]
        })
    else:
        message = "Keep breathing..."
    
    db.session.commit()
    
    return jsonify({
        "success": True,
        "stage": veg.stage,
        "message": message,
        "harvested": veg.harvested
    })

@planting.route("/wellness_dashboard")
@login_required
def wellness_dashboard():
    """Simple wellness dashboard"""
    user = current_user
    
    # Calculate simple wellness score
    wellness_score = 0
    wellness_score += min(user.streak * 10, 50)  # Max 50 points from plant streak
    wellness_score += min((user.mindfulness_streak or 0) * 10, 50)  # Max 50 from mindfulness
    wellness_score += min((user.total_mindful_minutes or 0), 100)  # Max 100 from minutes
    
    # Get recent activities
    recent_plants = Vegetable.query.filter_by(userid=user.id)\
                                  .order_by(Vegetable.plant_time.desc())\
                                  .limit(3).all()
    
    recent_mindfulness = MindfulnessLog.query.filter_by(user_id=user.id)\
                                            .order_by(MindfulnessLog.date_completed.desc())\
                                            .limit(3).all()
    
    return render_template("wellness_dashboard.html",
                         wellness_score=wellness_score,
                         recent_plants=recent_plants,
                         recent_mindfulness=recent_mindfulness,
                         user=user)

# @planting.route("/breathing")
# @login_required
# def breathing_exercise():
#     """Interactive breathing exercise page"""
#     return render_template("breathing_exercise.html")
@planting.route("/update_mood_after/<int:veg_id>", methods=["POST"])
@login_required
def update_mood_after(veg_id):
    """Update mood after harvesting"""
    veg = Vegetable.query.get_or_404(veg_id)
    
    if veg.userid != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403
    
    data = request.get_json()
    mood_after = data.get('mood_after')
    
    if mood_after:
        veg.mood_after = int(mood_after)
        db.session.commit()
        
        mood_change = 0
        if veg.mood_before:
            mood_change = veg.mood_after - veg.mood_before
        
        return jsonify({
            "success": True,
            "mood_after": veg.mood_after,
            "mood_change": mood_change
        })
    
    return jsonify({"error": "No mood provided"}), 400

@planting.route("/daily_checkin", methods=['GET', 'POST'])
@login_required
def daily_checkin():
    """Daily wellness check-in"""
    
    # Check if already completed today
    today = date.today()
    existing_checkin = DailyCheckIn.query.filter_by(
        user_id=current_user.id,
        check_in_date=today
    ).first()
    
    if existing_checkin and request.method == 'GET':
        flash('You already completed today\'s check-in! Come back tomorrow.', 'info')
        return redirect(url_for('planting.view_checkin', checkin_id=existing_checkin.id))
    
    if request.method == 'POST':
        checkin = DailyCheckIn(
            user_id=current_user.id,
            check_in_date=today,
            energy_level=int(request.form.get('energy_level', 3)),
            mood_rating=int(request.form.get('mood_rating', 3)),
            stress_level=int(request.form.get('stress_level', 3)),
            sleep_quality=int(request.form.get('sleep_quality', 3)),
            took_breaks=bool(request.form.get('took_breaks')),
            ate_well=bool(request.form.get('ate_well')),
            connected_with_others=bool(request.form.get('connected_with_others')),
            did_something_enjoyable=bool(request.form.get('did_something_enjoyable')),
            grateful_for=request.form.get('grateful_for', ''),
            biggest_challenge=request.form.get('biggest_challenge', '')
        )
        
        db.session.add(checkin)
        
        # Award coins for check-in
        current_user.coins += 3
        
        # Update check-in streak
        yesterday = today - timedelta(days=1)
        yesterday_checkin = DailyCheckIn.query.filter_by(
            user_id=current_user.id,
            check_in_date=yesterday
        ).first()
        
        if yesterday_checkin:
            current_user.checkin_streak = getattr(current_user, 'checkin_streak', 0) + 1
        else:
            current_user.checkin_streak = 1
        
        db.session.commit()
        
        flash('Check-in complete! You earned 3 coins. 🌟', 'success')
        return redirect(url_for('planting.view_checkin', checkin_id=checkin.id))
    
    return render_template('daily_checkin.html')

@planting.route("/checkin/<int:checkin_id>")
@login_required
def view_checkin(checkin_id):
    """View check-in results with insights"""
    checkin = DailyCheckIn.query.get_or_404(checkin_id)
    
    if checkin.user_id != current_user.id:
        abort(403)
    
    # Calculate wellness score for this check-in
    wellness_score = 0
    wellness_score += checkin.energy_level * 5
    wellness_score += checkin.mood_rating * 5
    wellness_score += (6 - checkin.stress_level) * 5  # Reverse stress score
    wellness_score += checkin.sleep_quality * 5
    
    # Add points for self-care actions
    if checkin.took_breaks: wellness_score += 5
    if checkin.ate_well: wellness_score += 5
    if checkin.connected_with_others: wellness_score += 5
    if checkin.did_something_enjoyable: wellness_score += 5
    
    # Generate personalized insights
    insights = []
    
    if checkin.stress_level >= 4:
        insights.append("Caring for grandchildren while managing your own needs is exhausting. Consider asking a neighbor or family member for a few hours of help.")

    if checkin.energy_level <= 2:
        insights.append("Your energy is precious - it's okay to have quiet days with simple activities like reading together or watching their favorite shows.")

    if checkin.sleep_quality <= 2:
        insights.append("Children's schedules can disrupt your sleep. Try to rest when they nap or have quiet time, even if it's just for 20 minutes.")

    if not checkin.took_breaks:
        insights.append("Even while supervising children, you can take micro-breaks - sit while they play, breathe deeply during their screen time.")

    if checkin.connected_with_others:
        insights.append("Staying connected with other adults is so important when you're focused on little ones all day. You're doing great!")

    if checkin.did_something_enjoyable:
        insights.append("Finding joy while caregiving is vital - whether it's watching them discover something new or enjoying your evening tea after bedtime.")
    
    # Get weekly trend
    week_ago = checkin.check_in_date - timedelta(days=7)
    weekly_checkins = DailyCheckIn.query.filter(
        DailyCheckIn.user_id == current_user.id,
        DailyCheckIn.check_in_date >= week_ago,
        DailyCheckIn.check_in_date <= checkin.check_in_date
    ).all()
    
    return render_template('view_checkin.html',
                         checkin=checkin,
                         wellness_score=wellness_score,
                         insights=insights,
                         weekly_count=len(weekly_checkins))

@planting.route("/checkin/history")
@login_required
def checkin_history():
    """View check-in history with trends"""
    checkins = DailyCheckIn.query.filter_by(user_id=current_user.id)\
                                 .order_by(DailyCheckIn.check_in_date.desc())\
                                 .limit(30).all()
    
    # Calculate averages
    if checkins:
        avg_mood = sum(c.mood_rating for c in checkins) / len(checkins)
        avg_stress = sum(c.stress_level for c in checkins) / len(checkins)
        avg_energy = sum(c.energy_level for c in checkins) / len(checkins)
        avg_sleep = sum(c.sleep_quality for c in checkins) / len(checkins)
    else:
        avg_mood = avg_stress = avg_energy = avg_sleep = 0
    
    return render_template('checkin_history.html',
                         checkins=checkins,
                         avg_mood=avg_mood,
                         avg_stress=avg_stress,
                         avg_energy=avg_energy,
                         avg_sleep=avg_sleep)





# @planting.route("/mindful_harvest/<int:veg_id>")
# @login_required
# def mindful_harvest(veg_id):
#     """Breathing exercise before harvesting"""
#     veg = Vegetable.query.get_or_404(veg_id)
    
#     if veg.userid != current_user.id:
#         abort(403)
    
#     if veg.stage != 'ready_to_harvest':
#         flash('This plant is not ready for harvest yet!', 'warning')
#         return redirect(url_for('planting.view_vegetable', veg_id=veg_id))
    
#     return render_template('mindful_harvest.html', veg=veg)

# @planting.route("/complete_harvest/<int:veg_id>", methods=["POST"])
# @login_required
# def complete_harvest(veg_id):
#     """Complete harvest after breathing exercise"""
#     veg = Vegetable.query.get_or_404(veg_id)
    
#     if veg.userid != current_user.id:
#         abort(403)
    
#     if veg.stage != 'ready_to_harvest':
#         return jsonify({"error": "Not ready for harvest"}), 400
    
#     # Mark as harvested
#     veg.stage = 'harvest'
#     veg.harvested = True
#     veg.mindful_harvest = True
#     veg.harvest_completed_at = datetime.now()
    
#     # Update user stats
#     user = User.query.get(current_user.id)
#     user.plant_count = (user.plant_count or 0) + 1
#     user.last_plant_date = date.today()
    
#     # Extra coins for mindful harvesting
#     user.coins += 15  # 10 for harvest + 5 for mindfulness
    
#     # Log the mindfulness activity
#     mindfulness_log = MindfulnessLog(
#         user_id=current_user.id,
#         activity_type='breathing',
#         activity_id='harvest_breathing',
#         duration_minutes=2,
#         coins_earned=5
#     )
#     db.session.add(mindfulness_log)
    
#     db.session.commit()
    
#     # Check achievements
#     unlock = update_user_stats()
    
#     return jsonify({
#         "success": True,
#         "message": "Mindful harvest complete! You earned 15 coins!",
#         "coins_earned": 15,
#         "total_coins": user.coins,
#         "achievements": [{"name": a.name, "description": a.description} for a in unlock]
#     })

@planting.route("/weekly_report")
@login_required
def weekly_report():
    """Generate weekly wellness report"""
    today = date.today()
    week_start = today - timedelta(days=7)
    
    # Get week's data
    weekly_plants = Vegetable.query.filter(
        Vegetable.userid == current_user.id,
        Vegetable.plant_time >= week_start
    ).all()
    
    weekly_checkins = DailyCheckIn.query.filter(
        DailyCheckIn.user_id == current_user.id,
        DailyCheckIn.check_in_date >= week_start
    ).all()
    
    weekly_mindfulness = MindfulnessLog.query.filter(
        MindfulnessLog.user_id == current_user.id,
        MindfulnessLog.date_completed >= week_start
    ).all()
    
    # Calculate statistics
    stats = calculate_weekly_stats(weekly_plants, weekly_checkins, weekly_mindfulness)
    
    # Generate insights
    insights = generate_weekly_insights(stats, weekly_checkins)
    
    # Get mood patterns
    mood_pattern = analyze_mood_patterns(weekly_checkins)
    
    # Get achievements this week
    weekly_achievements = Achievement.query.filter(
        Achievement.user_id == current_user.id,
        Achievement.date_earned >= week_start
    ).all()
    
    return render_template('weekly_report.html',
                         stats=stats,
                         insights=insights,
                         mood_pattern=mood_pattern,
                         achievements=weekly_achievements,
                         plants=weekly_plants,
                         checkins=weekly_checkins,
                         timedelta=timedelta)

def calculate_weekly_stats(plants, checkins, mindfulness):
    """Calculate comprehensive weekly statistics"""
    stats = {
        'total_plants': len(plants),
        'total_checkins': len(checkins),
        'total_mindfulness': len(mindfulness),
        'mindful_minutes': sum(m.duration_minutes for m in mindfulness),
        'avg_mood': 0,
        'avg_energy': 0,
        'avg_stress': 0,
        'avg_sleep': 0,
        'best_day': None,
        'toughest_day': None,
        'self_care_score': 0,
        'consistency_score': 0
    }
    
    if checkins:
        stats['avg_mood'] = sum(c.mood_rating for c in checkins) / len(checkins)
        stats['avg_energy'] = sum(c.energy_level for c in checkins) / len(checkins)
        stats['avg_stress'] = sum(c.stress_level for c in checkins) / len(checkins)
        stats['avg_sleep'] = sum(c.sleep_quality for c in checkins) / len(checkins)
        
        # Find best and toughest days
        daily_scores = {}
        for checkin in checkins:
            score = (checkin.mood_rating + checkin.energy_level + 
                    (6 - checkin.stress_level) + checkin.sleep_quality)
            daily_scores[checkin.check_in_date] = score
        
        if daily_scores:
            stats['best_day'] = max(daily_scores, key=daily_scores.get)
            stats['toughest_day'] = min(daily_scores, key=daily_scores.get)
        
        # Calculate self-care score
        care_actions = sum(
            (c.took_breaks + c.ate_well + c.connected_with_others + c.did_something_enjoyable)
            for c in checkins
        )
        stats['self_care_score'] = (care_actions / (len(checkins) * 4)) * 100
    
    # Calculate consistency score
    days_active = len(set(
        [p.plant_time.date() for p in plants] +
        [c.check_in_date for c in checkins] +
        [m.date_completed.date() for m in mindfulness]
    ))
    stats['consistency_score'] = (days_active / 7) * 100
    
    return stats

def generate_weekly_insights(stats, checkins):
    """Generate personalized insights based on weekly patterns"""
    insights = []
    
    # Consistency insights
    if stats['consistency_score'] >= 85:
        insights.append({
            'type': 'success',
            'icon': '🌟',
            'title': 'Outstanding Consistency!',
            'message': 'You checked in with yourself nearly every day while caring for your grandchildren. Your dedication to your own wellbeing is inspiring!'
        })
    elif stats['consistency_score'] >= 60:
        insights.append({
            'type': 'info',
            'icon': '💪',
            'title': 'Good Routine Building',
            'message': f"You stayed consistent {int(stats['consistency_score'])}% of the week despite your caregiving demands. Try to add just one more check-in next week."
        })
    else:
        insights.append({
            'type': 'warning',
            'icon': '🌱',
            'title': 'Room to Grow',
            'message': 'Caring for little ones makes self-care harder. Try checking in during their nap time or after bedtime.'
        })

    # Mood insights
    if stats['avg_mood'] >= 4:
        insights.append({
            'type': 'success',
            'icon': '😊',
            'title': 'Positive Mood Week',
            'message': 'Your mood stayed strong even while managing grandchildren. The joy they bring is clearly sustaining you!'
        })
    elif stats['avg_mood'] < 2.5:
        insights.append({
            'type': 'warning',
            'icon': '💚',
            'title': 'Emotional Support Needed',
            'message': 'This was emotionally challenging. Consider calling a friend, joining a grandparents support group, or asking family for help.'
        })

    # Stress insights
    if stats['avg_stress'] > 3.5:
        insights.append({
            'type': 'warning',
            'icon': '😰',
            'title': 'High Stress Detected',
            'message': 'Raising grandchildren is stressful. Try deep breathing when they\'re occupied, or step outside for fresh air during their play time.'
        })

    # Sleep insights
    if stats['avg_sleep'] < 3:
        insights.append({
            'type': 'warning',
            'icon': '😴',
            'title': 'Sleep Needs Attention',
            'message': 'Children can disrupt your sleep patterns. Try going to bed 30 minutes after they do, and keep your bedroom cool and quiet.'
        })
    elif stats['avg_sleep'] >= 4:
        insights.append({
            'type': 'success',
            'icon': '🛌',
            'title': 'Great Sleep Quality',
            'message': 'Good sleep gives you energy for active grandchildren. Keep protecting your bedtime routine!'
        })

    # Self-care insights
    if stats['self_care_score'] >= 75:
        insights.append({
            'type': 'success',
            'icon': '✨',
            'title': 'Excellent Self-Care',
            'message': f"You completed {int(stats['self_care_score'])}% of self-care while caring for grandchildren. You understand that caring for yourself helps you care for them!"
        })
    elif stats['self_care_score'] < 40:
        insights.append({
            'type': 'warning',
            'icon': '⚠️',
            'title': 'Increase Self-Care',
            'message': 'You\'re giving everything to your grandchildren but forgetting yourself. Even 10 minutes of "me time" daily makes a difference.'
        })

    # Mindfulness insights
    if stats['mindful_minutes'] >= 30:
        insights.append({
            'type': 'success',
            'icon': '🧘',
            'title': 'Mindfulness Champion',
            'message': f"You practiced {stats['mindful_minutes']} minutes of mindfulness while managing busy grandchildren. This patience practice serves you both!"
        })
    elif stats['mindful_minutes'] == 0:
        insights.append({
            'type': 'info',
            'icon': '🌸',
            'title': 'Try Mindfulness',
            'message': 'No quiet moments this week? Try 2 minutes of deep breathing while they play independently or watch their favorite show.'
        })
    
    return insights

def analyze_mood_patterns(checkins):
    """Analyze mood patterns throughout the week"""
    if not checkins:
        return None
    
    patterns = {
        'trend': 'stable',  # improving, declining, stable, variable
        'best_time': None,
        'worst_time': None,
        'weekend_vs_weekday': None
    }
    
    # Sort by date
    sorted_checkins = sorted(checkins, key=lambda x: x.check_in_date)
    
    if len(sorted_checkins) >= 3:
        # Check trend
        first_half = sorted_checkins[:len(sorted_checkins)//2]
        second_half = sorted_checkins[len(sorted_checkins)//2:]
        
        first_avg = sum(c.mood_rating for c in first_half) / len(first_half)
        second_avg = sum(c.mood_rating for c in second_half) / len(second_half)
        
        if second_avg > first_avg + 0.5:
            patterns['trend'] = 'improving'
        elif second_avg < first_avg - 0.5:
            patterns['trend'] = 'declining'
        elif max(c.mood_rating for c in sorted_checkins) - min(c.mood_rating for c in sorted_checkins) >= 3:
            patterns['trend'] = 'variable'
    
    return patterns

# @planting.route("/email_report")
# @login_required
# def email_report_settings():
#     """Settings for weekly email reports"""
#     return render_template('email_report_settings.html',
#                          email_enabled=getattr(current_user, 'weekly_report_enabled', False),
#                          email_day=getattr(current_user, 'report_day', 'Sunday'))

@planting.route("/unlock", methods=["GET", "POST"])
@login_required
def unlock():
    # Get all locked vegetables (those not in current_user.unlocked_vegetables)
    locked = [veg for veg in ALL_VEGETABLES if veg["key"] not in current_user.unlocked_vegetables]
    cost = 10

    if request.method == 'POST':
        veg_to_unlock = request.form.get('vegetable')
        if veg_to_unlock and veg_to_unlock in [v["key"] for v in locked]:
            if current_user.coins >= cost:
                current_user.coins -= cost
                current_user.unlocked_vegetables.append(veg_to_unlock)
                db.session.commit()
                flash(f"You've unlocked {veg_to_unlock.capitalize()}!", 'success')
            else:
                flash("Not enough coins!", 'danger')
        return redirect(url_for('planting.unlock'))

    return render_template("unlock.html", locked=locked, cost=cost)



@planting.route("/plant/<int:veg_id>")
@login_required
def view_vegetable(veg_id):
    veg = Vegetable.query.get_or_404(veg_id)
    if veg.userid != current_user.id:
        abort(403)
    
    # If not harvested, go to breathing page
    if not veg.harvested:
        return redirect(url_for('planting.plant_breathe', veg_id=veg_id))
    
    # If harvested, show a simple completion page or redirect to garden
    return render_template("vegetable_complete.html", veg=veg, id=current_user.id)

@planting.route("/plant/all_vegetables")
@login_required
def all_vegetables():
    veg = Vegetable.query.filter_by(userid=current_user.id).all()
    return render_template("vegetables.html", veg=veg)

@planting.route("/plant/guide", methods=['GET'])
def fake_plant():
    return render_template("plant_guide.html")

@planting.route("/glory_hall")
@login_required
def glory_hall():
    achievements = Achievement.query.filter_by(user_id=current_user.id).all()
    return render_template("glory_hall.html", achievements=achievements, timedelta=timedelta)

def update_user_stats():
    # print("update user stats")
    user = User.query.get(current_user.id)
    today = date.today()

    # First-time planting
    if user.last_plant_date is None:
        user.streak = 1
    elif user.last_plant_date == today:
        pass
    elif user.last_plant_date == today - timedelta(days=1):
        user.streak += 1
    else:
        user.streak = 1

    user.last_plant_date = today
    db.session.commit()

    # Force a reload to reflect updated values
    db.session.refresh(user)  # this line ensures user has fresh data
    unlock = grant_achievements(user)
    return unlock

def grant_achievements(user):
    streak = user.streak
    user_id = user.id
    existing = {a.name for a in Achievement.query.filter_by(user_id=user_id).all()}
    count = user.plant_count
    coins = user.coins

    unlock = []

    count_milestones = [
        (3, "Planted 3 Vegetables", "Planted 3 vegetables!"),
        (10, "Planted 10 Vegetables", "Planted 10 vegetables!"),
        (100, "Planted 100 Vegetables", "You're a farming master!")
    ]

    for threshold, name, description in count_milestones:
        if count >= threshold and name not in existing:
            a = Achievement(user_id=user_id, name=name, description=description)
            db.session.add(a)
            unlock.append(a)
    
    coins_milestones = [
    (50, "Self-Care Saver", "50 wellness points earned - you're investing in yourself!"),
    (200, "Resilience Builder", "200 wellness points - your strength is growing!"),
    (500, "Caregiving Champion", "500 points! You're showing that grandparents can thrive too!")
]
    
    for threshold, name, description in coins_milestones:
        if coins >= threshold and name not in existing:
            a = Achievement(user_id=user_id, name=name, description=description)
            db.session.add(a)
            unlock.append(a)
            
    if streak >= 3 and "3-Day Streak" not in existing:
        a = Achievement(user_id=user_id, name="3-Day Streak", description="Planted 3 days in a row!")
        db.session.add(a)
        unlock.append(a)

    if streak >= 10 and "10-Day Streak" not in existing:
        a = Achievement(user_id=user_id, name="10-Day Streak", description="Planted 10 days in a row!")
        db.session.add(a)
        unlock.append(a)
        
    # Add mindful harvest achievements
    mindful_harvests = Vegetable.query.filter_by(
        userid=user.id,
        harvested=True
    ).count()
    
    mindful_milestones = [
    (1, "Mindful Grandparent", "First moment of mindfulness while caregiving - well done!"),
    (5, "Peaceful Moments", "5 mindful breaks taken - you're finding calm in the chaos!"),
    (20, "Zen Grandparent", "20 mindful moments - you've mastered finding peace while raising little ones!")
]
    
    for threshold, name, description in mindful_milestones:
        if mindful_harvests >= threshold and name not in existing:
            a = Achievement(user_id=user_id, name=name, description=description)
            db.session.add(a)
            unlock.append(a)

    db.session.commit()
    
    return unlock



