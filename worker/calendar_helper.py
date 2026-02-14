import pickle
import uuid
import os
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

TOKEN_FILE = "token.pickle"

# Load team emails from .env
# Example in .env:
# TEAM_EMAILS=avinash.dp@somaiya.edu,chaitanya.sathe@somaiya.edu
TEAM_EMAILS = os.getenv("TEAM_EMAILS", "")
TEAM_EMAILS = [email.strip() for email in TEAM_EMAILS.split(",") if email.strip()]


# -----------------------------
# GET GOOGLE CALENDAR SERVICE
# -----------------------------
def get_calendar_service():
    with open(TOKEN_FILE, "rb") as token:
        creds = pickle.load(token)

    service = build("calendar", "v3", credentials=creds)
    return service


# -----------------------------
# CREATE EVENT
# -----------------------------
def create_calendar_event(company_name, founder_email, slot_time, duration_minutes=30):
    try:
        service = get_calendar_service()

        start_dt = datetime.fromisoformat(slot_time)
        end_dt = start_dt + timedelta(minutes=duration_minutes)

        attendees = []

        # Add founder email
        if founder_email:
            attendees.append({"email": founder_email})

        # Add team emails
        for email in TEAM_EMAILS:
            attendees.append({"email": email})

        event_body = {
            "summary": f"Startup Review: {company_name}",
            "description": f"Startup: {company_name}\nFounder: {founder_email}",
            "start": {
                "dateTime": start_dt.isoformat(),
                "timeZone": "Asia/Kolkata",
            },
            "end": {
                "dateTime": end_dt.isoformat(),
                "timeZone": "Asia/Kolkata",
            },
            "attendees": attendees,
            "conferenceData": {
                "createRequest": {
                    "requestId": str(uuid.uuid4()),
                    "conferenceSolutionKey": {
                        "type": "hangoutsMeet"
                    }
                }
            }
        }

        event = service.events().insert(
            calendarId="primary",
            body=event_body,
            conferenceDataVersion=1,
            sendUpdates="all"   # ensures invites are emailed
        ).execute()

        meet_link = event.get("hangoutLink")

        print("Calendar event created.")
        print("Meet link:", meet_link)

        return meet_link

    except Exception as e:
        print("Calendar event failed:", e)
        return None
