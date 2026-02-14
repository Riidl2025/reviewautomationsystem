from flask import Flask, request, render_template_string
import requests
import os
from datetime import datetime
from dotenv import load_dotenv
from calendar_helper import create_calendar_event

load_dotenv()

app = Flask(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# -----------------------------
# HTML TEMPLATE (Styled UI)
# -----------------------------

HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>riidl Meeting Booking</title>
    <style>
        body { font-family: Arial; background:#f4f6f9; padding:40px; }
        .container {
            max-width:600px;
            margin:auto;
            background:white;
            padding:30px;
            border-radius:10px;
            box-shadow:0px 4px 12px rgba(0,0,0,0.1);
        }
        h1 { color:#d11a2a; text-align:center; }
        select { width:100%; padding:10px; margin-top:10px; margin-bottom:20px; }
        button {
            width:100%; padding:12px;
            background:#2563eb; color:white;
            border:none; border-radius:6px;
            font-weight:bold; cursor:pointer;
        }
        button:hover { background:#1e4ed8; }
    </style>
</head>

<body>
<div class="container">

<h1>riidl SVU</h1>
<h3 style="text-align:center;">Book Your Review Meeting</h3>

<form method="post">
    <input type="hidden" name="company" value="{{company}}">
    <input type="hidden" name="email" value="{{email}}">

    <label>Select Available Slot</label>

    <select name="slot_time" required>
        {% for slot in slots %}
        <option value="{{slot.raw}}">{{slot.display}}</option>
        {% endfor %}
    </select>

    <button type="submit">Confirm Booking</button>
</form>

</div>
</body>
</html>
"""

SUCCESS_PAGE = """
<h2 style="text-align:center;">Meeting booked successfully.</h2>
<p style="text-align:center;">You will receive calendar invitation shortly.</p>
"""

# -----------------------------
# FETCH AVAILABLE SLOTS
# -----------------------------

def fetch_available_slots():
    url = f"{SUPABASE_URL}/rest/v1/meeting_slots?select=slot_time&is_booked=eq.false&slot_time=gte.now()&order=slot_time.asc"

    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()

    rows = response.json()

    formatted_slots = []

    for row in rows:
        raw_time = row["slot_time"]
        dt = datetime.fromisoformat(raw_time)

        formatted_slots.append({
            "raw": raw_time,
            "display": dt.strftime("%A, %d %B %Y — %I:%M %p")
        })

    return formatted_slots

# -----------------------------
# SAVE BOOKING + CALENDAR
# -----------------------------

def save_booking(company, email, slot_time):

    # Double booking protection
    check_url = f"{SUPABASE_URL}/rest/v1/meeting_slots?slot_time=eq.{slot_time}&is_booked=eq.false"
    check_response = requests.get(check_url, headers=HEADERS)
    check_response.raise_for_status()

    if not check_response.json():
        raise Exception("Slot already booked")

    # Insert booking
    booking_url = f"{SUPABASE_URL}/rest/v1/meeting_bookings"

    payload = {
        "companyname": company,
        "email": email,
        "slot_time": slot_time
    }

    requests.post(booking_url, json=payload, headers=HEADERS).raise_for_status()

    # Mark slot booked
    slot_url = f"{SUPABASE_URL}/rest/v1/meeting_slots?slot_time=eq.{slot_time}"
    requests.patch(slot_url, json={"is_booked": True}, headers=HEADERS).raise_for_status()

    print("Booking saved and slot locked.")

    # Create calendar event
    meet_link = create_calendar_event(company, email, slot_time)

    if meet_link:
        print("Meet link:", meet_link)

# -----------------------------
# ROUTE
# -----------------------------

@app.route("/book", methods=["GET", "POST"])
def book():

    company = request.args.get("company") or request.form.get("company")
    email = request.args.get("email") or request.form.get("email")

    if request.method == "POST":
        slot_time = request.form.get("slot_time")
        try:
            save_booking(company, email, slot_time)
            return SUCCESS_PAGE
        except Exception as e:
            return f"<h3>Error: {str(e)}</h3>"

    slots = fetch_available_slots()

    return render_template_string(
        HTML_PAGE,
        slots=slots,
        company=company,
        email=email
    )

# -----------------------------
# RUN SERVER
# -----------------------------

if __name__ == "__main__":
    app.run(debug=True)
