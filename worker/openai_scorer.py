import os
import json
import re
from openai import OpenAI

from pdf_text_extractor import extract_pdf_content
from prompt import SCORING_RULES, build_prompt

from dotenv import load_dotenv


load_dotenv()
# Initialize OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# -----------------------------
# JSON EXTRACTION HELPER
# -----------------------------
def extract_json_from_text(text: str) -> dict:
    """
    Extract first valid JSON object from model output.
    Prevents duplication or formatting issues.
    """
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON found in model response")

    json_str = match.group(0)
    return json.loads(json_str)


# -----------------------------
# DECISION LOGIC
# -----------------------------
def calculate_total_and_decision(scores: dict) -> dict:
    total_score = (
        scores["Founder_and_Team"]
        + scores["Problem_and_Market"]
        + scores["Solution_and_Product"]
        + scores["Traction_and_Validation"]
        + scores["Business_Model_and_Scalability"]
        + scores["Incubation_Fit"]
    )

    # Category gates
    if scores["Traction_and_Validation"] < 5:
        decision = "Reject"
    elif scores["Solution_and_Product"] < 5:
        decision = "Reject"
    elif scores["Founder_and_Team"] < 8:
        decision = "Reject"
    else:
        if total_score >= 85:
            decision = "Auto-select"
        elif total_score >= 70:
            decision = "Incubate with conditions"
        elif total_score >= 55:
            decision = "Pre-incubation"
        else:
            decision = "Reject"

    scores["Total_Score"] = total_score
    scores["Decision"] = decision
    return scores


# -----------------------------
# OPENAI EVALUATION
# -----------------------------
def evaluate_startup(pdf_path: str) -> dict:
    print("Extracting content from PDF...")
    content = extract_pdf_content(pdf_path)

    prompt = SCORING_RULES + build_prompt(content)

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
        temperature=0.2
    )

    output_text = response.output[0].content[0].text.strip()

    # Safe JSON extraction
    scores = extract_json_from_text(output_text)

    # Apply decision logic
    final_result = calculate_total_and_decision(scores)

    return final_result


# -----------------------------
# TEST BLOCK (optional)
# -----------------------------
if __name__ == "__main__":
    PDF_PATH = r"C:\Users\CHAITANYA SATHE\Desktop\evaluator_app\worker\processed_pdfs\6_kbsd.pdf"

    if not os.path.exists(PDF_PATH):
        print("PDF not found:", PDF_PATH)
        exit()

    result = evaluate_startup(PDF_PATH)

    print("\n===== FINAL RESULT =====\n")
    print(json.dumps(result, indent=2))
