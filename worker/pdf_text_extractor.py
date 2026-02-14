import pdfplumber
import fitz  # PyMuPDF
from PIL import Image
import pytesseract
import io


# -----------------------------------------
# TEXT EXTRACTION FROM PDF
# -----------------------------------------
def extract_text_from_pdf(pdf_path: str) -> str:
    all_text = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                all_text.append(text)

    return "\n".join(all_text)


# -----------------------------------------
# OCR FROM IMAGES INSIDE PDF (IN MEMORY)
# -----------------------------------------
def extract_text_from_images(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    ocr_texts = []

    for page_index in range(len(doc)):
        page = doc[page_index]
        images = page.get_images(full=True)

        for img in images:
            xref = img[0]
            base_image = doc.extract_image(xref)

            image_bytes = base_image["image"]

            try:
                image = Image.open(io.BytesIO(image_bytes))
                text = pytesseract.image_to_string(image)

                if text.strip():
                    ocr_texts.append(text.strip())

            except Exception:
                continue

    return "\n".join(ocr_texts)


# -----------------------------------------
# COMBINED PIPELINE
# -----------------------------------------
def extract_pdf_content(pdf_path: str) -> str:
    slide_text = extract_text_from_pdf(pdf_path)
    image_text = extract_text_from_images(pdf_path)

    combined_text = slide_text + "\n\n=== OCR TEXT ===\n\n" + image_text
    return combined_text
