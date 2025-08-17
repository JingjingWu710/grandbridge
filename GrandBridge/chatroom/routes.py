from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from GrandBridge.models import db, Event, ChatMessage

# If creating a new blueprint:
chatroom = Blueprint('chatroom', __name__)

@login_required
@chatroom.route('/event/<int:id>/participate', methods=['POST'])
def toggle_participation(id):
    """Toggle user participation in an event"""
    event = Event.query.get_or_404(id)
    
    # Check if user can participate
    if not event.can_participate(current_user):
        flash('You are not eligible to participate in this event.', 'danger')
        return redirect(url_for('calendar.event', id=id))
    
    if event.is_participant(current_user):
        # Remove participation
        event.remove_participant(current_user)
        flash('You have left the event.', 'info')
    else:
        # Add participation
        event.add_participant(current_user)
        flash('You are now participating in this event!', 'success')
    
    return redirect(url_for('calendar.event', id=id))

@login_required
@chatroom.route('/event/<int:id>/chat')
def event_chat(id):
    """Display the chat room for an event"""
    event = Event.query.get_or_404(id)
    
    # Check if user is a participant
    if not event.is_participant(current_user):
        flash('You must be a participant to access the chat room.', 'warning')
        return redirect(url_for('calendar.event', id=id))
    
    # Get recent messages (last 100)
    messages = event.chat_messages.order_by(ChatMessage.timestamp.desc()).limit(100).all()
    messages.reverse()  # Show oldest first
    
    # Get list of participants
    participants = event.participants.all()
    
    return render_template('event_chat.html', 
                         event=event, 
                         messages=messages,
                         participants=participants)

@login_required
@chatroom.route('/event/<int:id>/chat/send', methods=['POST'])
def send_message(id):
    """Send a message in the event chat"""
    event = Event.query.get_or_404(id)
    
    # Check if user is a participant
    if not event.is_participant(current_user):
        return jsonify({'error': 'You must be a participant to send messages'}), 403
    
    content = request.json.get('content', '').strip()
    if not content:
        return jsonify({'error': 'Message cannot be empty'}), 400
    
    # Create new message
    message = ChatMessage(
        content=content,
        user_id=current_user.id,
        event_id=event.id
    )
    db.session.add(message)
    db.session.commit()
    
    return jsonify(message.to_dict()), 200

@login_required
@chatroom.route('/event/<int:id>/chat/messages')
def get_messages(id):
    """Get messages for an event (for AJAX polling)"""
    event = Event.query.get_or_404(id)
    
    # Check if user is a participant
    if not event.is_participant(current_user):
        return jsonify({'error': 'You must be a participant to view messages'}), 403
    
    # Get last_id from query parameters
    last_id = request.args.get('last_id', 0, type=int)
    
    # Get messages newer than last_id
    if last_id:
        messages = event.chat_messages.filter(ChatMessage.id > last_id).order_by(ChatMessage.timestamp).all()
    else:
        # Get last 50 messages if no last_id
        messages = event.chat_messages.order_by(ChatMessage.timestamp.desc()).limit(50).all()
        messages.reverse()
    
    return jsonify([msg.to_dict() for msg in messages]), 200

@login_required
@chatroom.route('/event/<int:id>/participants')
def event_participants(id):
    """View list of event participants"""
    event = Event.query.get_or_404(id)
    
    # Check if user can view this event
    if not (event.can_participate(current_user) or current_user.is_admin):
        flash('You do not have permission to view this event.', 'danger')
        return redirect(url_for('chatroom.chatroom_view'))
    
    participants = event.participants.all()
    
    return render_template('event_participants.html', 
                         event=event, 
                         participants=participants)