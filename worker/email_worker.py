import os
import requests
import smtplib
from email.mime.text import MIMEText

from dotenv import load_dotenv

load_dotenv()
# ---------------- CONFIG ----------------

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

# This is important:
# Local testing → http://127.0.0.1:5000
# Render later → https://your-app.onrender.com
BOOKING_BASE_URL = os.getenv("BOOKING_LINK_BASE")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}


# ----------------------------------------
# FETCH RESULTS WHERE EMAIL NOT SENT
# ----------------------------------------

def fetch_pending_emails():
    url = f"{SUPABASE_URL}/rest/v1/screening_results?email_sent=eq.false"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json()


# ----------------------------------------
# MARK EMAIL AS SENT
# ----------------------------------------

def mark_email_sent(row_id):
    url = f"{SUPABASE_URL}/rest/v1/screening_results?id=eq.{row_id}"
    payload = {"email_sent": True}

    response = requests.patch(url, json=payload, headers=HEADERS)
    response.raise_for_status()


# ----------------------------------------
# EMAIL CONTENT BUILDER
# ----------------------------------------

def build_email_content(decision, company_name, email):

    # Create booking link
    booking_link = f"{BOOKING_BASE_URL}/book?company={company_name}&email={email}"

    # ---------------- AUTO SELECT ----------------
    if decision == "Auto-select":

        subject = "Congratulations! Your Startup Has Been Selected for Incubation"

        body = f"""
Dear {company_name},

We are pleased to inform you that, based on our evaluation of your submitted pitch deck, your startup has been selected for incubation.

To proceed further, please schedule a review meeting using the link below:

{booking_link}

Kindly select a convenient time slot at your earliest convenience.

We congratulate you on this achievement and look forward to working with you.

Sincerely,  
Startup Evaluation Team
"""

    # ---------------- INCUBATE WITH CONDITIONS ----------------
    elif decision == "Incubate with conditions":

        subject = "Selection for Pre-Incubation Program"

        body = f"""
Dear {company_name},

Thank you for submitting your startup proposal for evaluation.

We are pleased to inform you that your startup has been selected for our Pre-Incubation program.

This indicates that your idea shows promising potential; however, certain areas require further development before full incubation.

To proceed further, please schedule a review meeting using the link below:

{booking_link}

The Pre-Incubation phase is designed to help startups strengthen key areas through mentoring and structured guidance.

We appreciate your efforts and look forward to supporting your progress.

Sincerely,  
Startup Evaluation Team
"""

    # ---------------- REJECT ----------------
    else:

        subject = "Update on Your Startup Application"

        body = f"""
Dear {company_name},

Thank you for submitting your startup proposal and for your interest in our incubation program.

After careful evaluation, we regret to inform you that your startup has not been selected for incubation at this time.

This decision does not diminish the effort and potential behind your work. We encourage you to continue refining your concept and to consider reapplying in the future.

We appreciate your time and interest in our program.

Sincerely,  
Startup Evaluation Team
"""

    return subject, body


# ----------------------------------------
# SEND EMAIL
# ----------------------------------------

def send_email(to_email, subject, body):

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_email

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)


# ----------------------------------------
# MAIN WORKER
# ----------------------------------------

def main():

    rows = fetch_pending_emails()
    print(f"Found {len(rows)} emails to send")

    for row in rows:
        try:
            row_id = row["id"]
            email = row["email"]
            company = row.get("companyname", "Founder")
            decision = row["decision"]

            subject, body = build_email_content(decision, company, email)

            print(f"Sending email to {email}...")
            send_email(email, subject, body)

            mark_email_sent(row_id)
            print("Email sent and marked.")

        except Exception as e:
            print("Error sending email:", e)


if __name__ == "__main__":
    main()
