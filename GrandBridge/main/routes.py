from flask import render_template, Blueprint
from flask_login import current_user
from GrandBridge.models import User, Vegetable, Achievement, Event, Memory
main = Blueprint('main', __name__)

@main.route("/")
@main.route("/home")
def home():
    if current_user.is_authenticated:
        id = current_user.id
        harvested_vegetables = Vegetable.query.filter_by(
                                            userid=id, 
                                            harvested=True
                                                ).count()
        total_achievements = Achievement.query.filter_by(id=id).count()
        total_memories = Memory.query.filter_by(userid=id).count()
        user = User.query.get(id)
        if user:
            total_events_participated = user.participating_events.count()
        else:
            total_events_participated = 0
        return render_template('home.html', harvested=harvested_vegetables,
                           achivements=total_achievements,
                           memories=total_memories,
                           participated=total_events_participated)
    else:
        return render_template('home.html')