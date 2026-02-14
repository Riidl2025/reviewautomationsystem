import datetime
import pickle
from googleapiclient.discovery import build

# Load credentials
with open("token.pickle", "rb") as token:
    creds = pickle.load(token)

service = build("calendar", "v3", credentials=creds)

# Event details
event = {
    "summary": "Test Incubation Meeting",
    "description": "This is a test event created by the incubation system.",
    "start": {
        "dateTime": (datetime.datetime.utcnow() + datetime.timedelta(minutes=5)).isoformat() + "Z",
        "timeZone": "UTC",
    },
    "end": {
        "dateTime": (datetime.datetime.utcnow() + datetime.timedelta(minutes=35)).isoformat() + "Z",
        "timeZone": "UTC",
    },
    "attendees": [
        {"email": "avinash.dp@somaiya.edu"},
        {"email": "chaitanya.sathe@somaiya.edu"} # replace with any email to test invites
    ],
    "conferenceData": {
        "createRequest": {
            "requestId": "test-meeting-123",
            "conferenceSolutionKey": {"type": "hangoutsMeet"},
        }
    },
}

event = service.events().insert(
    calendarId="primary",
    body=event,
    conferenceDataVersion=1,
    sendUpdates="all"
).execute()

print("Event created!")
print("Meet link:", event.get("hangoutLink"))
