import pdfplumber
import pytesseract
from tqdm import tqdm
from pdf2image import convert_from_path
import os
import re
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---------- CONFIG ----------
PDF_DIR = "data/pdfs"
OUT_FILE = "data/documents.txt"
MAX_WORKERS = 3   # PC khỏe: 3–4, laptop thường: 2–3


# ---------- CHECK TESSERACT ----------
tesseract_path = shutil.which("tesseract")
if not tesseract_path:
    raise RuntimeError(
        "❌ Tesseract chưa được cài hoặc chưa nằm trong PATH.\n"
        "👉 Chạy: winget install UB-Mannheim.TesseractOCR\n"
        "👉 Sau đó mở terminal mới và chạy lại."
    )

pytesseract.pytesseract.tesseract_cmd = tesseract_path
print(f"✅ Using tesseract: {tesseract_path}")


# ---------- UTILS ----------

def clean_text(text):
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ---------- PDF TEXT ----------

def extract_text_pdfplumber(pdf_path):
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n\n"
    except Exception as e:
        print(f"❌ pdfplumber error ({os.path.basename(pdf_path)}): {e}")
    return text


def extract_text_ocr(pdf_path):
    text = ""
    try:
        images = convert_from_path(pdf_path)
        for img in images:
            text += pytesseract.image_to_string(img, lang="vie") + "\n\n"
    except Exception as e:
        print(f"❌ OCR error ({os.path.basename(pdf_path)}): {e}")
    return text


# ---------- MAIN PROCESS ----------

def process_pdf(pdf_path):
    name = os.path.basename(pdf_path)
    print(f"\n📄 Processing: {name}")

    text = extract_text_pdfplumber(pdf_path)

    used_ocr = False
    if len(text.strip()) < 800:
        print(f"⚠️ OCR needed: {name}")
        text = extract_text_ocr(pdf_path)
        used_ocr = True

    text = clean_text(text)

    if len(text) < 300:
        print(f"⚠️ Text yếu nhưng vẫn lưu: {name}")

    header = (
        f"\n\n=== PDF FILE ===\n"
        f"TITLE: {name}\n"
        f"SOURCE: local_pdf\n"
        f"OCR_USED: {used_ocr}\n\n"
    )

    print(f"✅ Done: {name} ({len(text)} chars)")
    return header + text


# ---------- RUN BATCH ----------

def run():
    pdf_files = [
        os.path.join(PDF_DIR, f)
        for f in os.listdir(PDF_DIR)
        if f.lower().endswith(".pdf")
    ]

    if not pdf_files:
        print("⚠️ Không tìm thấy PDF")
        return

    collected = ""

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(process_pdf, f): f
            for f in pdf_files
        }

        for future in tqdm(
            as_completed(futures),
            total=len(futures),
            desc="🚀 Tổng tiến trình PDF"
        ):
            try:
                result = future.result()
                if result:
                    collected += result
            except Exception as e:
                print(f"❌ Worker error: {e}")

    if collected:
        with open(OUT_FILE, "a", encoding="utf-8") as f:
            f.write(collected)
        print(f"\n🎉 DONE! Đã lưu vào {OUT_FILE}")
    else:
        print("\n⚠️ Không PDF nào trích xuất được")


if __name__ == "__main__":
    run()
