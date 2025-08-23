from flask import render_template, url_for, flash, redirect, Blueprint, request, session, abort
import calendar as py_calendar
import pytz
import requests
from ics import Calendar as iCalendar
from calendar import monthrange
from datetime import date, timedelta, datetime, time
from GrandBridge import db
from GrandBridge.calendar.forms import EventForm, EditEventForm
from GrandBridge.models import Event, Family
from flask_login import current_user, login_required
from GrandBridge.utils.external_events import fetch_external_events
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from GrandBridge.utils.decorators import (
    validate_dates,
    user_id_is_required,
    fetchCredentials,
)
from GrandBridge.utils.auth import (
    get_id_info,
    get_flow,
    db_add_user
)
from GrandBridge.config import Config
from GrandBridge.extensions import limiter
from googleapiclient.discovery import build
from GrandBridge.utils.auth import db_get_user_credentials

TOKEN_DIR = "tokens"
calendar = Blueprint('calendar', __name__)

from datetime import date

@calendar.route("/events")
@login_required
def events():
    # Get today's date range (start and end of day)
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    if current_user.is_admin:
        # Admin sees today's events for families they manage
        managed_family_ids = [family.id for family in current_user.admin_families]
        # Get all events for today where any managed family is in the family_ids list
        events = []
        for event in Event.query.filter(
            Event.start >= today_start,
            Event.start <= today_end
        ).order_by(Event.start).all():
            if any(fid in event.family_ids for fid in managed_family_ids):
                events.append(event)
    else:
        # Regular user sees today's events for their family
        if current_user.family_id:
            # Get today's events and filter in Python
            todays_events = Event.query.filter(
                Event.start >= today_start,
                Event.start <= today_end
            ).order_by(Event.start).all()
            events = [e for e in todays_events if current_user.family_id in e.family_ids]
        else:
            events = []
    
    return render_template('events.html', 
                         events=events)


@calendar.route("/event/<int:id>", methods=['GET'])
@login_required
def event(id):
    event = Event.query.filter_by(id=id).first_or_404()
    
    # Get family information for admins
    event_families = []
    if current_user.is_admin and event.family_ids:
        event_families = Family.query.filter(Family.id.in_(event.family_ids)).all()

    return render_template("event.html", event=event, event_families=event_families)

@calendar.route("/events/new", methods=['GET', 'POST'])
@login_required
def new_event():
    if not current_user.is_admin:
        flash('Only an admin can access this page', 'danger')
        return redirect(url_for("main.home"))
        
    form = EventForm()
    if form.validate_on_submit():
        event = Event(
            title=form.title.data,
            start=form.start.data,
            end=form.end.data,
            location=form.location.data,
            description=form.description.data,
            family_ids=form.family_ids.data  # This is now a list of family IDs
        )
        db.session.add(event)
        db.session.commit()
        
        # Create a nice message showing which families were selected
        selected_families = Family.query.filter(Family.id.in_(form.family_ids.data)).all()
        family_names = [f.name for f in selected_families]
        flash(f"Event created successfully for families: {', '.join(family_names)}!", "success")
        return redirect(url_for("calendar.calendar_view"))

    return render_template("create_event.html", form=form)

@calendar.route("/event/<int:id>/edit", methods=['GET', 'POST'])
@login_required
def edit_event(id):
    if not current_user.is_admin:
        flash('Only an admin can access this page', 'danger')
        return redirect(url_for("main.home"))
        
    event = Event.query.filter_by(id=id).first_or_404()
    form = EditEventForm()
    
    if form.validate_on_submit():
        event.title = form.title.data
        event.start = form.start.data
        event.end = form.end.data
        event.location = form.location.data
        event.description = form.description.data
        event.family_ids = form.family_ids.data  # Update the family list
        
        db.session.commit()
        
        # Create a nice message showing which families were selected
        selected_families = Family.query.filter(Family.id.in_(form.family_ids.data)).all()
        family_names = [f.name for f in selected_families]
        flash(f'Event updated successfully for families: {", ".join(family_names)}!', 'success')
        return redirect(url_for("calendar.event", id=id))
    else:
        # Pre-populate form with current event data
        form.title.data = event.title
        form.start.data = event.start
        form.end.data = event.end
        form.location.data = event.location
        form.description.data = event.description
        form.family_ids.data = event.family_ids  # Pre-select current families
        
    return render_template("create_event.html", form=form)

@calendar.route("/event/<int:id>/delete", methods=['POST'])
@login_required
def delete_event(id):
    if current_user.is_admin:
        event = Event.query.filter_by(id=id).first_or_404()
        db.session.delete(event)
        db.session.commit()
        flash('You have deleted this event', 'success')
    else:
        flash('Only an admin can access this page', 'danger')
    return redirect(url_for("main.home"))

def get_month_calendar(year, month):
    cal = py_calendar.Calendar(firstweekday=6)  # Sunday start
    month_days = cal.monthdatescalendar(year, month)
    return month_days  # List of weeks; each week is list of 7 date objects

@calendar.route("/calendar")
@login_required
def calendar_view():  
    # External .ics calendar
    external_events = []
    ics_url = session.get('subscribed_url')
    if ics_url:
        external_events = fetch_external_events(ics_url)
    
    # Read query params, fallback to today
    year = request.args.get("year", type=int)
    month = request.args.get("month", type=int)

    today = datetime.today()
    today_date = today.date()  # Store today's date for comparison
    
    if not year or not month:
        year, month = today.year, today.month

    # Handle overflow/underflow of months
    if month < 1:
        month = 12
        year -= 1
    elif month > 12:
        month = 1
        year += 1

    month_days = get_month_calendar(year, month)
    all_days = sum(month_days, [])
    start_date, end_date = min(all_days), max(all_days)
    
    # Google Calendar Events
    google_events = []
    try:
        credentials = db_get_user_credentials(current_user.google_id)
        if credentials:
            google_events = fetch_google_events(start_date, end_date, credentials)
    except Exception as e:
        print("Google event fetch failed or user not connected:", e)
    
    source_filter = request.args.get("source")
    
    # UPDATED: Filter internal events based on user type
    internal_events = []
    all_events = Event.query.all()
    if current_user.is_admin:
        # Admin can see events from all families they manage
        internal_events = [e for e in all_events if e.is_visible_to_admin(current_user)]
    else:
        # Regular user can only see events from their own family
        if current_user.family_id:
            internal_events = [e for e in all_events if e.is_visible_to_family(current_user.family_id)]
    
    # Calculate week range for week_count
    start_of_week = today_date - timedelta(days=today_date.weekday())  # Monday
    end_of_week = start_of_week + timedelta(days=6)  # Sunday
    
    # Initialize counters
    events_count = 0
    today_count = 0
    week_count = 0
    
    # Map: date -> list of events
    events_by_date = {}
    for day in all_days:
        day_events = []

        if source_filter in [None, "", "internal"]:
            day_events.extend([
                type("EventLike", (), {
                    "title": e.title,
                    "id": e.id,
                    "source": "internal"
                })()
                for e in internal_events if e.occurs_on(day)
            ])

        if source_filter in [None, "", "external"]:
            day_events.extend([
                type("EventLike", (), {
                    "title": e.title,
                    "source": "external"
                })()
                for e in external_events if e.occurs_on(day)
            ])

        if source_filter in [None, "", "google"]:
            day_events.extend([
                type("EventLike", (), {
                    "event_id": e.get("id"),
                    "title": e["title"],
                    "location": e.get("location"),
                    "meet_link": e.get("meet_link"),
                    "source": "google"
                })()
                for e in google_events if e["date"] == day
            ])

        events_by_date[day] = day_events
        
        # Count events
        day_event_count = len(day_events)
        events_count += day_event_count
        
        # Count today's events
        if day == today_date:
            today_count = day_event_count
        
        # Count this week's events
        if start_of_week <= day <= end_of_week:
            week_count += day_event_count

    return render_template("calendar.html",
                           month_days=month_days,
                           year=year,
                           month=month,
                           events_by_date=events_by_date,
                           events_count=events_count,
                           today_count=today_count,
                           week_count=week_count)


@calendar.route("/calendar/subscribe")
@login_required
def subscribe_calendar():
    ics_url = request.args.get("url")
    if not ics_url:
        return "Missing .ics URL", 400
    
    # Optionally: validate or sanitize the URL
    session['subscribed_url'] = ics_url
    flash('You have subscribed the calendar', 'success')
    return redirect(url_for('calendar.calendar_view'))

@login_required
@calendar.route("/google_event/<event_id>")
def google_event(event_id):
    google_events = session.get("google_events", [])
    event_data = next((e for e in google_events if e["id"] == event_id), None)
    if not event_data:
        abort(404)
    date = event_data["date"]
    title = event_data["title"]
    start_time = event_data["start_time"]
    end_time = event_data["end_time"]
    location = event_data["location"]
    meet_link = event_data["meet_link"]
    return render_template(
            'google_event.html',
            event_id=event_id,
            date=date,
            title=title,
            start_time=start_time,
            end_time=end_time,
            location=location,
            meet_link=meet_link
                            )  

@calendar.route("/google_login")
@login_required
def google_login():
    try:
        authorization_url, state = get_flow().authorization_url()
        session["state"] = state
        return redirect(authorization_url)
    except Exception as error:
        print(f"Error occured: {error}")
        return redirect("/")


@calendar.route("/google_logout")
@login_required
def google_logout():
    session.clear()
    return redirect("/")


@calendar.route("/callback")
@login_required
def callback():
    try:
        get_flow().fetch_token(authorization_response=request.url)

        if not session["state"] == request.args["state"]:
            abort(500)  # State does not match!

        credentials = get_flow().credentials
        id_info = get_id_info(credentials)
        
        session["user_id"] = id_info.get("sub")
        session["name"] = id_info.get("name")
        
        user_id = id_info.get("sub")
        
        db_add_user(current_user.id, user_id, credentials)
        return redirect(url_for("calendar.calendar_view"))
    except Exception as error:
        print(f"Error occured: {error}")
        return redirect("/")

@calendar.route("/google_event/<event_id>/delete", methods=["POST"])
@login_required
def delete_google_event(event_id):
    credentials = db_get_user_credentials(current_user.google_id)
    service = build("calendar", "v3", credentials=credentials)

    try:
        service.events().delete(calendarId="primary", eventId=event_id).execute()
        flash("Event deleted successfully", "success")
    except Exception as e:
        flash(f"Error deleting event: {e}", "danger")

    return redirect(url_for("calendar.calendar_view"))

@calendar.route("/google_event/<event_id>/edit", methods=["GET", "POST"])
def edit_google_event(event_id):
    credentials = db_get_user_credentials(current_user.google_id)
    service = build("calendar", "v3", credentials=credentials)

    event = service.events().get(calendarId="primary", eventId=event_id).execute()

    if request.method == "POST":
        event["summary"] = request.form.get("title")
        event["location"] = request.form.get("location")

        tz = pytz.timezone("Europe/London")
        start_str = request.form.get("start_datetime")  # e.g., '2025-08-03T15:00'
        end_str = request.form.get("end_datetime")

        try:
            start_dt = tz.localize(datetime.strptime(start_str, "%Y-%m-%dT%H:%M"))
            end_dt = tz.localize(datetime.strptime(end_str, "%Y-%m-%dT%H:%M"))
        except Exception as e:
            flash(f"Time parse failed: {e}", "danger")
            return render_template("edit_google_event.html", event=event)

        event["start"] = {
            "dateTime": start_dt.isoformat(),
            "timeZone": "Europe/London"
        }
        event["end"] = {
            "dateTime": end_dt.isoformat(),
            "timeZone": "Europe/London"
        }

        try:
            service.events().update(calendarId="primary", eventId=event_id, body=event).execute()
            flash("Event updated", "success")
            return redirect(url_for("calendar.calendar_view"))
        except Exception as e:
            flash(f"Update failed: {e}", "danger")

    return render_template("edit_google_event.html", event=event)

def fetch_google_events(start_date, end_date, credentials):
    service = build("calendar", "v3", credentials=credentials)
    start = datetime.combine(start_date, time.min).isoformat() + "Z"  # UTC
    end = datetime.combine(end_date, time.max).isoformat() + "Z"

    events_result = service.events().list(
        calendarId="primary",
        timeMin=start,
        timeMax=end,
        maxResults=100,
        singleEvents=True,
        orderBy="startTime"
    ).execute()

    events = events_result.get("items", [])
    event_objs = []

    for event in events:
        summary = event.get("summary", "No Title")
        location = event.get("location", None)
        meet_link = event.get("hangoutLink", None)

        start_str = event["start"].get("dateTime", event["start"].get("date"))
        end_str = event["end"].get("dateTime", event["end"].get("date"))

        try:
            start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
        except ValueError:
            continue

        # Convert to local time zone
        tz = pytz.timezone("Europe/London")
        start_dt = start_dt.astimezone(tz)
        end_dt = end_dt.astimezone(tz)

        event_objs.append({
            "id": event["id"],
            "date": start_dt.date(),
            "title": summary,
            "start_time": start_dt.time().strftime("%H:%M"),
            "end_time": end_dt.time().strftime("%H:%M"),
            "location": location,
            "meet_link": meet_link
        })
    session['google_events'] = event_objs

    return event_objs



# @calendar.route("/google_events", methods=["GET"])
# @limiter.limit("5 per minute")
# def get_google_events():
#     return render_template("google_events.html")


# @calendar.route("/google_events", methods=["POST"])
# @limiter.limit("5 per minute")
# @user_id_is_required
# @validate_dates
# @fetchCredentials
# def post_events(user_id, dates, credentials):
#     print("Trying to get events...")
#     start_date, end_date = dates

#     try:
#         event_list = get_calendar_events(start_date, end_date, credentials)
#         return (
#         f"Your upcoming events are between "
#         f"{start_date} and {end_date}: <br/> {', '.join(event_list)} <br/> "
#         f"<a href='/logout'><button>Logout</button></a>"
#     )
#     except Exception as error:
#         print(f"Error occured: {error}")
#         return redirect("/")

# def get_calendar_events(start_date, end_date, credentials):
#     service = build("calendar", "v3", credentials=credentials)
#     start = datetime.combine(start_date, time.min).isoformat() + "Z"  # 'Z' indicates UTC time
#     end = datetime.combine(end_date, time.max).isoformat() + "Z"  # 'Z' indicates UTC time

#     events_result = (
#         service.events()
#         .list(
#             calendarId="primary",
#             timeMin=start,
#             timeMax=end,
#             maxResults=10,
#             singleEvents=True,
#             orderBy="startTime",
#         )
#         .execute()
#     )

#     events = events_result.get("items", [])
#     event_list = []

#     if not events:
#         event_list.append("No upcoming events found.")
#     else:
#         for event in events:
#             start = event["start"].get("dateTime", event["start"].get("date"))
#             event_time = (
#                 datetime.fromisoformat(start)
#                 .astimezone(pytz.timezone("Europe/London"))
#                 .strftime("%Y-%m-%d %H:%M:%S")
#             )
#             event_list.append(f"{event_time} - {event['summary']}")

#     return event_list