import os
import re
import datetime
import pytz
from icalendar import Calendar
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from dotenv import load_dotenv, find_dotenv
from tqdm import tqdm

load_dotenv(find_dotenv())
DOWNLOADS_PATH = os.getenv("DOWNLOADS_PATH")

SCOPES = ["https://www.googleapis.com/auth/calendar"]
CALENDAR_ID = "primary"
BIG_ICS_FILE = os.path.join(DOWNLOADS_PATH, "big_planning.ics")
CLIENT_SECRETS_FILE = "client.json"

def authenticate_gcal():
    """
    Authenticate user via OAuth2, using client.json,
    returning an authorized calendar service instance.
    """
    creds = None
    token_file = "token.json"

    if os.path.exists(token_file):
        import pickle
        with open(token_file, "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        import pickle
        with open(token_file, "wb") as token:
            pickle.dump(creds, token)

    return build("calendar", "v3", credentials=creds)

def delete_all_events(service):
    """
    Delete every event from the specified Google Calendar (CALENDAR_ID).
    """
    page_token = None
    while True:
        events = service.events().list(calendarId=CALENDAR_ID, pageToken=page_token).execute()
        for event in events.get("items", []):
            service.events().delete(calendarId=CALENDAR_ID, eventId=event["id"]).execute()
        page_token = events.get("nextPageToken")
        if not page_token:
            break
    print("All events deleted from calendar.")

def read_and_clean_ics(ics_file_path):
    """
    Read the ICS file (which may contain multiple VCALENDAR blocks)
    and produce a single valid ICS string with:
      - Exactly one VCALENDAR
      - All VEVENT blocks extracted
    """
    with open(ics_file_path, "r", encoding="utf-8") as f:
        ics_data = f.read()

    # Extract all VEVENT blocks
    events = re.findall(r"BEGIN:VEVENT.*?END:VEVENT", ics_data, flags=re.DOTALL)

    # Build a single VCALENDAR
    cleaned_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//hacksw/handcal//NONSGML v1.0//EN",
        "METHOD:PUBLISH",
        "X-WR-TIMEZONE:Europe/Paris",
    ]
    cleaned_lines.extend(events)
    cleaned_lines.append("END:VCALENDAR")

    return "\n".join(cleaned_lines)

def import_ics_to_gcal(service, ics_file):
    """
    Parse ICS and insert events into Google Calendar.
    Cleans up duplicates by matching on iCalUID == ICS UID (if recognized),
    and uses DTSTART + DTSTAMP for duration if DTEND is missing.
    """
    cleaned_ics = read_and_clean_ics(ics_file)
    calendar = Calendar.from_ical(cleaned_ics)

    for component in tqdm(calendar.walk()):
        if component.name == "VEVENT":
            uid = str(component.get("UID", "NO-UID"))
            summary = str(component.get("SUMMARY", "No Title"))
            location = str(component.get("LOCATION", ""))

            start_prop = component.get("DTSTART")
            stamp_prop = component.get("DTSTAMP")
            end_prop = component.get("DTEND")

            if not start_prop:
                print(f"Skipping event with no DTSTART (UID={uid})")
                continue

            start_dt = start_prop.dt
            # If DTEND is missing, use DTSTAMP for end
            # If DTSTAMP is also missing, fallback 1h from start
            if not end_prop:
                if stamp_prop:
                    end_dt = stamp_prop.dt
                else:
                    # fallback if no DTSTAMP
                    if isinstance(start_dt, datetime.date) and not isinstance(start_dt, datetime.datetime):
                        end_dt = start_dt  # all-day event
                    else:
                        end_dt = start_dt + datetime.timedelta(hours=1)
            else:
                end_dt = end_prop.dt

            # Delete existing events with same iCalUID, if recognized
            # (some accounts may let you search by iCalUID=..., some may not)
            try:
                existing_events = service.events().list(
                    calendarId=CALENDAR_ID,
                    iCalUID=uid
                ).execute()

                for evt in existing_events.get("items", []):
                    service.events().delete(calendarId=CALENDAR_ID, eventId=evt["id"]).execute()
                if existing_events.get("items"):
                    print(f"Removed duplicates for UID={uid}")
            except Exception as e:
                print(f"Warning: Could not remove duplicates for UID={uid}: {e}")

            # Convert datetime objects to RFC3339 if they aren't already
            if isinstance(start_dt, datetime.date) and not isinstance(start_dt, datetime.datetime):
                # All-day event
                event_body = {
                    "summary": summary,
                    "location": location,
                    "start": {"date": start_dt.isoformat()},
                    "end": {"date": end_dt.isoformat()},
                }
            else:
                # Timed event
                if start_dt.tzinfo is None:
                    start_dt = pytz.UTC.localize(start_dt)
                if end_dt.tzinfo is None:
                    end_dt = pytz.UTC.localize(end_dt)

                event_body = {
                    "summary": summary,
                    "location": location,
                    "start": {"dateTime": start_dt.isoformat()},
                    "end": {"dateTime": end_dt.isoformat()},
                }

            # Insert the new event
            created = service.events().insert(calendarId=CALENDAR_ID, body=event_body).execute()
            # print(f"Imported UID={uid} -> {created.get('htmlLink')}")

def main_client():
    print("- Authenticating to Google Calendar ...")
    service = authenticate_gcal()

    print("- Deleting all existing events ...")
    delete_all_events(service)

    print("- Importing ICS events to Google Calendar ...")
    import_ics_to_gcal(service, BIG_ICS_FILE)
    
    print("Done !")