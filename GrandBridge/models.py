from GrandBridge import db, login_manager
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy import PickleType
from sqlalchemy_utils import JSONType

# Association table for admin - family
admin_family = db.Table(
    'admin_family',
    db.Column('admin_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('family_id', db.Integer, db.ForeignKey('family.id'), primary_key=True)
)

# Association table for event participants (many-to-many)
event_participants = db.Table('event_participants',
    db.Column('event_id', db.Integer, db.ForeignKey('event.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('joined_at', db.DateTime, default=datetime.utcnow)
)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    address = db.Column(db.String(60), nullable=True)
    contact_info = db.Column(db.String(60), nullable=True)
    
    
    # Family relationship for normal users
    family_id = db.Column(db.Integer, db.ForeignKey('family.id'), nullable=True)
    admin_families = db.relationship(
    'Family',
    secondary=admin_family,
    backref=db.backref('admins', lazy='dynamic'),
    lazy='dynamic'
)

    # Google credentials
    google_credentials_data = db.Column(db.JSON, nullable=True)
    google_credentials_json = db.Column(db.Text, nullable=True)
    google_id = db.Column(db.String(255), unique=True)

    last_plant_date = db.Column(db.Date)
    streak = db.Column(db.Integer, default=0)
    coins = db.Column(db.Integer, default=0)
    plant_count = db.Column(db.Integer, default=0)
    
    unlocked_vegetables = db.Column(MutableList.as_mutable(PickleType), default=lambda: ['carrot', 'potato', 'spinach', 'cabbage', 'tomato'])
    
    mindfulness_streak = db.Column(db.Integer, default=0)
    last_mindfulness_date = db.Column(db.Date)
    total_mindful_minutes = db.Column(db.Integer, default=0)
    wellness_score = db.Column(db.Integer, default=0)
    
    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    
    # Relationships - Using backref for simplicity
    author = db.relationship('User', backref=db.backref('sent_chat_messages', lazy='dynamic'))
    # Note: event relationship is created by Event.chat_messages backref
    
    
    def __repr__(self):
        return f"ChatMessage('{self.author.username}', '{self.content[:20]}...', '{self.timestamp}')"
    
    def to_dict(self):
        """Convert message to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'content': self.content,
            'username': self.author.username,
            'user_id': self.user_id,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'edited': self.edited
        }


class Family(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)

    # One-to-many: a family has multiple users
    members = db.relationship('User', backref='family', lazy=True)

    def __repr__(self):
        return f"<Family {self.name}>"

    
class Achievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    name = db.Column(db.String(50))
    description = db.Column(db.String(255))
    date_earned = db.Column(db.DateTime, default=datetime.now())
    user = db.relationship('User', backref='achievements')
    


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)

    # Start and end are datetime objects (date + time)
    start = db.Column(db.DateTime, nullable=False)
    end = db.Column(db.DateTime, nullable=False)
    
    # Location
    location = db.Column(db.String(60), nullable=True)
    
    # Description (can be empty)
    description = db.Column(db.Text)
    
    # Change from single family_id to list of family_ids
    family_ids = db.Column(JSONType, nullable=True, default=list)
    
    # Add participants relationship
    participants = db.relationship(
        'User',
        secondary=event_participants,
        backref=db.backref('participating_events', lazy='dynamic'),
        lazy='dynamic'
    )
    
    # Add chat_messages relationship with unique name
    chat_messages = db.relationship('ChatMessage', 
                                   backref='event', 
                                   lazy='dynamic', 
                                   cascade='all, delete-orphan')

    def __init__(self, **kwargs):
        # Ensure family_ids is always a list
        if 'family_ids' in kwargs and not isinstance(kwargs['family_ids'], list):
            kwargs['family_ids'] = [kwargs['family_ids']]
        super().__init__(**kwargs)
    
    def occurs_on(self, day_date):
        # Check if event overlaps a specific date (for calendar view)
        return self.start.date() <= day_date <= self.end.date()
    
    def is_visible_to_family(self, family_id):
        """Check if this event should be visible to a specific family"""
        return family_id in self.family_ids if family_id else False
    
    def is_visible_to_admin(self, admin_user):
        """Check if this event should be visible to an admin based on their managed families"""
        if not admin_user.is_admin:
            return False
        
        managed_family_ids = [family.id for family in admin_user.admin_families]
        return any(family_id in managed_family_ids for family_id in self.family_ids)
    
    def is_participant(self, user):
        """Check if a user is a participant in this event"""
        return self.participants.filter(event_participants.c.user_id == user.id).count() > 0
    
    def add_participant(self, user):
        """Add a user as a participant"""
        if not self.is_participant(user):
            self.participants.append(user)
            db.session.commit()
    
    def remove_participant(self, user):
        """Remove a user from participants"""
        if self.is_participant(user):
            self.participants.remove(user)
            db.session.commit()
    
    def can_participate(self, user):
        """Check if a user can participate in this event"""
        if user.is_admin:
            # Admin can participate if they manage any of the event's families
            managed_family_ids = [family.id for family in user.admin_families]
            return any(family_id in managed_family_ids for family_id in self.family_ids)
        else:
            # Regular user can participate if their family is included in the event
            return user.family_id in self.family_ids if user.family_id else False
    
class Vegetable(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    type = db.Column(db.String, nullable=False)
    plant_time = db.Column(db.DateTime, default=datetime.now())
    harvested = db.Column(db.Boolean, default=False)
    stage = db.Column(db.String(10), default='seed')
    seed_image = db.Column(db.String(200))
    sprout_image = db.Column(db.String(200))
    harvest_image = db.Column(db.String(200))
    note = db.Column(db.Text)
    userid = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    intention = db.Column(db.String(50))  # self_care, helped_other, etc
    mood_before = db.Column(db.Integer)  # 1-5 scale
    mood_after = db.Column(db.Integer)   # 1-5 scale
    
    harvest_completed_at = db.Column(db.DateTime)

class MindfulnessLog(db.Model):
    """Track mindfulness activities"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    activity_type = db.Column(db.String(30), nullable=False)  # breathing, movement, etc
    activity_id = db.Column(db.String(30), nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False)
    date_completed = db.Column(db.DateTime, default=datetime.now)
    coins_earned = db.Column(db.Integer, default=0)
    
    # Add relationship to User
    user = db.relationship('User', backref='mindfulness_logs')
    
class DailyCheckIn(db.Model):
    """Quick daily wellness check-ins"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    check_in_date = db.Column(db.Date, default=date.today)
    
    # Quick ratings (1-5 scale)
    energy_level = db.Column(db.Integer)
    mood_rating = db.Column(db.Integer)
    stress_level = db.Column(db.Integer)
    sleep_quality = db.Column(db.Integer)
    
    # Yes/No questions
    took_breaks = db.Column(db.Boolean, default=False)
    ate_well = db.Column(db.Boolean, default=False)
    connected_with_others = db.Column(db.Boolean, default=False)
    did_something_enjoyable = db.Column(db.Boolean, default=False)
    
    # Open text (optional)
    grateful_for = db.Column(db.String(255))
    biggest_challenge = db.Column(db.String(255))
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    user = db.relationship('User', backref='check_ins')
    
class Location(db.Model):
    """Enhanced Location model for food pickup points"""
    __tablename__ = 'locations'
    
    id = db.Column(db.Integer, primary_key=True)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    name = db.Column(db.String(255), nullable=False, default='Food Pickup Point')
    address = db.Column(db.String(500))
    
    # Additional fields for enhanced functionality
    description = db.Column(db.Text)  # Detailed description of the location
    operating_hours = db.Column(db.String(255))  # e.g., "Mon-Fri 9AM-5PM"
    contact_info = db.Column(db.String(255))  # Phone or email
    capacity = db.Column(db.String(100))  # e.g., "Serves 50 people daily"
    food_types = db.Column(db.String(500))  # Types of food available
    
    # Status and tracking
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Relationships
    created_by = db.relationship('User', backref='created_locations')
    # visits = db.relationship('LocationVisit', backref='location', cascade='all, delete-orphan')
    
    def to_dict(self):
        """Convert location to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'lat': self.latitude,
            'lng': self.longitude,
            'name': self.name,
            'address': self.address,
            'description': self.description,
            'operating_hours': self.operating_hours,
            'contact_info': self.contact_info,
            'capacity': self.capacity,
            'food_types': self.food_types,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'visit_count': len(self.visits) if self.visits else 0
        }
    
    def __repr__(self):
        return f'<Location {self.name}>'


# class LocationVisit(db.Model):
#     """Track user visits to food pickup locations"""
#     __tablename__ = 'location_visits'
    
#     id = db.Column(db.Integer, primary_key=True)
#     location_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=False)
#     user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
#     visit_date = db.Column(db.DateTime, default=datetime.utcnow)
#     notes = db.Column(db.Text)
    
#     # Relationships
#     user = db.relationship('User', backref='location_visits')
    
#     def __repr__(self):
#         return f'<LocationVisit {self.user_id} -> {self.location_id}>'
    
class Memory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    filetype = db.Column(db.String(50), nullable=False)
    text = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now())
    userid = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
class FoodRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    submitted_at = db.Column(db.DateTime, default=datetime.now)
    nutrition_advice = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Define the relationship
    entries = db.relationship('FoodEntry', backref='record', cascade='all, delete-orphan')


class FoodEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    food_name = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    record_id = db.Column(db.Integer, db.ForeignKey('food_record.id'), nullable=False)
    
class Staff(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), nullable=False)
    organisation = db.Column(db.String(60), nullable=False)
    tel = db.Column(db.String(60), nullable=False)
    email = db.Column(db.String(60), nullable=False)
    intro = db.Column(db.Text, nullable=False)
