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
    page_token = None
    while True:
        events = service.events().list(calendarId=CALENDAR_ID, pageToken=page_token).execute()
        for event in events.get("items", []):
            service.events().delete(calendarId=CALENDAR_ID, eventId=event["id"]).execute()
        page_token = events.get("nextPageToken")
        if not page_token:
            break

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
    Interprets naive local times (no tzinfo) as Europe/Paris.
    """
    tz_paris = pytz.timezone("Europe/Paris")
    cleaned_ics = read_and_clean_ics(ics_file)
    calendar = Calendar.from_ical(cleaned_ics)

    processed_uids = set()

    for component in tqdm(calendar.walk()):
        if component.name == "VEVENT":
            uid = str(component.get("UID", "NO-UID"))
            if uid in processed_uids:
                # Skip repeated VEVENT with same UID in the same ICS import
                continue
            processed_uids.add(uid)

            summary = str(component.get("SUMMARY", "No Title"))
            location = str(component.get("LOCATION", ""))

            start_prop = component.get("DTSTART")
            stamp_prop = component.get("DTSTAMP")
            end_prop = component.get("DTEND")

            if not start_prop:
                # No start time => skip
                continue

            start_dt = start_prop.dt
            # Use DTEND if present, otherwise DTSTAMP or fallback
            if not end_prop:
                if stamp_prop:
                    end_dt = stamp_prop.dt
                else:
                    # fallback
                    if isinstance(start_dt, datetime.date) and not isinstance(start_dt, datetime.datetime):
                        end_dt = start_dt
                    else:
                        end_dt = start_dt + datetime.timedelta(hours=1)
            else:
                end_dt = end_prop.dt

            # --- Remove existing duplicates from the calendar by UID ---
            try:
                existing_events = service.events().list(
                    calendarId=CALENDAR_ID,
                    iCalUID=uid
                ).execute()
                for evt in existing_events.get("items", []):
                    service.events().delete(calendarId=CALENDAR_ID, eventId=evt["id"]).execute()
            except Exception:
                pass

            # --- Ensure Europe/Paris if no tzinfo ---
            if isinstance(start_dt, datetime.datetime):
                if start_dt.tzinfo is None:
                    start_dt = tz_paris.localize(start_dt)
                else:
                    # Convert to Europe/Paris if ICS had a different tz
                    start_dt = start_dt.astimezone(tz_paris)
            if isinstance(end_dt, datetime.datetime):
                if end_dt.tzinfo is None:
                    end_dt = tz_paris.localize(end_dt)
                else:
                    end_dt = end_dt.astimezone(tz_paris)

            # --- Create the event body ---
            # Case 1: date-only => all-day event
            if isinstance(start_dt, datetime.date) and not isinstance(start_dt, datetime.datetime):
                event_body = {
                    "summary": summary,
                    "location": location,
                    "start": {"date": start_dt.isoformat()},
                    "end": {"date": end_dt.isoformat()},
                }
            else:
                # Timed event with Europe's tz => store as ISO8601 with +01:00 (or +02:00 in summer)
                event_body = {
                    "summary": summary,
                    "location": location,
                    "start": {"dateTime": start_dt.isoformat()},
                    "end": {"dateTime": end_dt.isoformat()},
                }

            service.events().insert(calendarId=CALENDAR_ID, body=event_body).execute()

def main_client():
    print("- Authenticating to Google Calendar ...")
    service = authenticate_gcal()

    print("- Deleting all existing events ...")
    delete_all_events(service)

    print("- Importing ICS events to Google Calendar ...")
    import_ics_to_gcal(service, BIG_ICS_FILE)
    
    print("Done !")
