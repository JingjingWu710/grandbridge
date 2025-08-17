import requests
from ics import Calendar as iCalendar
class ExternalEvent:
    def __init__(self, title, begin, end=None):
        self.title = title
        self.begin = begin
        self.end = end

    def occurs_on(self, day):
        # day is a datetime.date
        return self.begin.date() <= day <= (self.end.date() if self.end else self.begin.date())

def fetch_external_events(ics_url):
    try:
        response = requests.get(ics_url)
        response.raise_for_status()

        calendar = iCalendar(response.text)
        events = []

        for event in calendar.events:
            events.append(ExternalEvent(
                title=event.name,
                begin=event.begin.datetime,
                end=event.end.datetime if event.end else None
            ))

        return events

    except Exception as e:
        print(f"[ERROR] Failed to fetch or parse .ics: {e}")
        return []