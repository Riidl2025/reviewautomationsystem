from datetime import datetime, timedelta
import requests
import os

from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}


# -----------------------------
# GET LATEST SLOT FROM DB
# -----------------------------
def get_latest_slot():
    url = f"{SUPABASE_URL}/rest/v1/meeting_slots?select=slot_time&order=slot_time.desc&limit=1"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()

    data = response.json()
    if not data:
        return datetime.now()

    return datetime.fromisoformat(data[0]["slot_time"])


# -----------------------------
# GENERATE TUE/THU DATES
# -----------------------------
def get_next_valid_dates(start_date, days_ahead=14):
    valid_dates = []
    current = start_date

    end_date = start_date + timedelta(days=days_ahead)

    while current <= end_date:
        if current.weekday() in [1, 3]:  # Tue, Thu
            valid_dates.append(current.date())
        current += timedelta(days=1)

    return valid_dates


# -----------------------------
# GENERATE TIME SLOTS
# -----------------------------
def generate_slots_for_date(date):
    slots = []
    hours = [10, 11, 12, 14, 15]  # skip 1PM

    for hour in hours:
        slot = datetime(date.year, date.month, date.day, hour, 0, 0)
        slots.append(slot.isoformat())

    return slots


# -----------------------------
# INSERT INTO DB
# -----------------------------
def insert_slots(slots):
    url = f"{SUPABASE_URL}/rest/v1/meeting_slots"

    payload = [{"slot_time": slot} for slot in slots]

    if payload:
        requests.post(url, json=payload, headers=HEADERS)


# -----------------------------
# MAIN AUTO EXTENDER
# -----------------------------
def main():
    print("Checking slots...")

    latest_slot = get_latest_slot()
    today = datetime.now()

    # Always keep slots 14 days ahead
    target_date = today + timedelta(days=14)

    if latest_slot >= target_date:
        print("Slots already sufficient.")
        return

    print("Generating new slots...")

    valid_dates = get_next_valid_dates(latest_slot + timedelta(days=1))

    all_slots = []
    for date in valid_dates:
        all_slots.extend(generate_slots_for_date(date))

    insert_slots(all_slots)

    print("Slots extended successfully.")


if __name__ == "__main__":
    main()
