import os
import re
import json
import subprocess
import tempfile
import shutil
import requests
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

from openai_scorer import evaluate_startup

load_dotenv()

# =========================
# CONFIG
# =========================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

BOOKING_LINK_BASE = os.getenv("BOOKING_LINK_BASE")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# =========================
# LIBREOFFICE DETECTION
# =========================

SOFFICE_PATH = shutil.which("soffice")

if SOFFICE_PATH is None:
    possible_path = r"C:\Program Files\LibreOffice\program\soffice.exe"
    if os.path.exists(possible_path):
        SOFFICE_PATH = possible_path

if SOFFICE_PATH is None:
    raise RuntimeError("LibreOffice not found.")

# =========================
# HELPERS
# =========================

def safe_text(text: str) -> str:
    text = text.lower().strip()
    return re.sub(r"[^a-z0-9]+", "_", text)


def safe_parse_json(result):
    """
    Ensures result is valid JSON dict.
    Retries or fixes common issues.
    """
    if isinstance(result, dict):
        return result

    try:
        return json.loads(result)
    except Exception:
        raise ValueError("Invalid JSON returned from scorer")


def fetch_unscreened_rows():
    url = f"{SUPABASE_URL}/rest/v1/form_responses?screened=eq.no"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json()


def mark_as_processing(row_id):
    url = f"{SUPABASE_URL}/rest/v1/form_responses?id=eq.{row_id}"
    requests.patch(url, json={"screened": "processing"}, headers=HEADERS)


def mark_as_screened(row_id):
    url = f"{SUPABASE_URL}/rest/v1/form_responses?id=eq.{row_id}"
    requests.patch(url, json={"screened": "yes"}, headers=HEADERS)


def mark_as_failed(row_id):
    url = f"{SUPABASE_URL}/rest/v1/form_responses?id=eq.{row_id}"
    requests.patch(url, json={"screened": "failed"}, headers=HEADERS)


def download_ppt(ppt_url, save_path):
    response = requests.get(ppt_url)
    response.raise_for_status()
    with open(save_path, "wb") as f:
        f.write(response.content)


def convert_ppt_to_pdf(ppt_path, output_dir):
    subprocess.run(
        [
            SOFFICE_PATH,
            "--headless",
            "--convert-to", "pdf",
            "--outdir", output_dir,
            ppt_path
        ],
        check=True
    )

# =========================
# STORE RESULT
# =========================

def store_result(result, row, pdf_filename):
    payload = {
        "startup_id": row["id"],
        "companyname": row.get("companyname"),
        "email": row.get("email"),
        "pdf_filename": pdf_filename,
        "scores_json": result,
        "total_score": result.get("Total_Score"),
        "decision": result.get("Decision"),
        "reasoning": result.get("Reasoning"),
        "email_sent": False
    }

    url = f"{SUPABASE_URL}/rest/v1/screening_results"
    requests.post(url, headers=HEADERS, json=payload).raise_for_status()

# =========================
# EMAIL SECTION
# =========================

def build_email(decision, company, email, row_id):

    booking_link = f"{BOOKING_LINK_BASE}/book?id={row_id}"

    if decision in ["Auto-select", "Incubate with conditions", "Pre-incubation"]:

        subject = "Startup Evaluation Result – Next Steps"

        body = f"""
Dear {company},

We are pleased to inform you that your startup has been selected for the next stage.

Please book a meeting using the link below:

{booking_link}

Regards,
Startup Evaluation Team
"""

    else:
        subject = "Startup Evaluation Result"

        body = f"""
Dear {company},

Thank you for applying.

After evaluation, we regret to inform you that your startup has not been selected at this time.

Regards,
Startup Evaluation Team
"""

    return subject, body


def send_email(to_email, subject, body):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_email

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)

# =========================
# MAIN WORKER
# =========================

def main():

    rows = fetch_unscreened_rows()
    print(f"Found {len(rows)} new submissions")

    for row in rows:
        row_id = row["id"]
        company = row.get("companyname", "unknown")
        ppt_url = row["ppt"]
        email = row.get("email")

        print("\nProcessing:", company)

        mark_as_processing(row_id)

        try:
            with tempfile.TemporaryDirectory() as tmpdir:

                ppt_filename = f"{row_id}_{safe_text(company)}.pptx"
                ppt_path = os.path.join(tmpdir, ppt_filename)

                print("Downloading PPT...")
                download_ppt(ppt_url, ppt_path)

                print("Converting PPT...")
                convert_ppt_to_pdf(ppt_path, tmpdir)

                pdf_filename = ppt_filename.replace(".pptx", ".pdf")
                pdf_path = os.path.join(tmpdir, pdf_filename)

                print("Scoring startup...")
                result = evaluate_startup(pdf_path)

                result = safe_parse_json(result)

                print(json.dumps(result, indent=2))

                print("Saving result...")
                store_result(result, row, pdf_filename)

                print("Sending email...")
                subject, body = build_email(result["Decision"], company, email, row_id)
                send_email(email, subject, body)

        except Exception as e:
            print("Error:", e)
            mark_as_failed(row_id)
            continue

        mark_as_screened(row_id)
        print("Completed:", company)


if __name__ == "__main__":
    main()
