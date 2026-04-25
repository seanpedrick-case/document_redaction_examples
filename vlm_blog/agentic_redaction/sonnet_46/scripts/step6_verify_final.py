"""Verify final redacted PDF: generate review images and check text extraction."""
import csv
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image, ImageDraw

# Use most recently modified redacted PDF
pdf_candidates = sorted(Path("output_final").glob("*_redacted.pdf"), key=lambda f: f.stat().st_mtime, reverse=True)
csv_candidates = sorted(Path("output_final").glob("*_review_file.csv"), key=lambda f: f.stat().st_mtime, reverse=True)

FINAL_PDF = pdf_candidates[0]
FINAL_CSV = csv_candidates[0]
OUT_DIR = Path("output_final/review_images")
OUT_DIR.mkdir(parents=True, exist_ok=True)

print(f"Final PDF: {FINAL_PDF.name}")
print(f"Final CSV: {FINAL_CSV.name}")

with FINAL_CSV.open("r", newline="", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

rows_by_page = {}
for r in rows:
    p = int(float(r.get("page", "0") or 0))
    rows_by_page.setdefault(p, []).append(r)

LABEL_COLORS = {
    "PERSON": "red",
    "EMAIL_ADDRESS": "blue",
    "PHONE_NUMBER": "blue",
    "LOCATION": "green",
    "SIGNATURE": "purple",
    "CUSTOM": "orange",
}

doc = fitz.open(str(FINAL_PDF))
print(f"\nGenerating review images for {doc.page_count} pages...")

for p in range(1, doc.page_count + 1):
    pix = doc[p - 1].get_pixmap(dpi=180)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    max_w = 1280
    if img.width > max_w:
        scale = max_w / img.width
        new_size = (max_w, int(img.height * scale))
        img = img.resize(new_size, Image.LANCZOS)

    draw = ImageDraw.Draw(img)
    scale_x = img.width / pix.width
    scale_y = img.height / pix.height

    for r in rows_by_page.get(p, []):
        x0 = float(r["xmin"]) * pix.width * scale_x
        y0 = float(r["ymin"]) * pix.height * scale_y
        x1 = float(r["xmax"]) * pix.width * scale_x
        y1 = float(r["ymax"]) * pix.height * scale_y
        color = LABEL_COLORS.get(r.get("label", ""), "red")
        draw.rectangle([x0, y0, x1, y1], outline=color, width=2)

    out_path = OUT_DIR / f"page_{p:03d}.png"
    img.save(out_path)
    n_boxes = len(rows_by_page.get(p, []))
    print(f"  Page {p}: {n_boxes} redaction boxes -> {out_path.name}")

print("\n=== Text extraction verification ===")
SENSITIVE_TERMS = [
    "Giuliani",
    "London",
    "Sister City", "Sister Cities", "sister city", "sister cities",
    "akaplan@sister-cities.org",
]

redacted_text = ""
doc2 = fitz.open(str(FINAL_PDF))
for pg in doc2:
    redacted_text += pg.get_text()

orig_doc = fitz.open("Partnership-Agreement-Toolkit_0_0.pdf")
orig_text = ""
for pg in orig_doc:
    orig_text += pg.get_text()

all_pass = True
for term in SENSITIVE_TERMS:
    orig_count = orig_text.lower().count(term.lower())
    redact_count = redacted_text.lower().count(term.lower())
    status = "PASS" if redact_count == 0 else "REVIEW"
    if redact_count > 0:
        all_pass = False
    print(f"[{status}] '{term}': {orig_count} in original -> {redact_count} in redacted")

print()
print("Overall:", "ALL PASS" if all_pass else "REVIEW NEEDED")
print(f"\nFinal review images saved to: {OUT_DIR}")
