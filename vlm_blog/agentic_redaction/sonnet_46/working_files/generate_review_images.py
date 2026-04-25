import csv
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image, ImageDraw

# Find files in output directory
OUTPUT_DIR = Path("output")
REVIEW_IMAGES_DIR = Path("review_images")
REVIEW_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# Find the relevant files
pdf_files = list(OUTPUT_DIR.glob("*_redacted.pdf"))
csv_files = list(OUTPUT_DIR.glob("*_review_file.csv"))

if not pdf_files or not csv_files:
    print("ERROR: Could not find PDF or CSV files in output directory")
    exit(1)

PDF_PATH = pdf_files[0]
REVIEW_CSV = csv_files[0]

print(f"Using PDF: {PDF_PATH.name}")
print(f"Using CSV: {REVIEW_CSV.name}")

# Read review CSV
with REVIEW_CSV.open("r", newline="", encoding="utf-8-sig") as f:
    review_rows = list(csv.DictReader(f))

print(f"\nTotal redaction boxes in CSV: {len(review_rows)}")

# Group rows by page
rows_by_page = {}
for r in review_rows:
    page = int(float(r.get("page", "0") or 0))
    rows_by_page.setdefault(page, []).append(r)

print(f"Pages with redactions: {sorted(rows_by_page.keys())}")

# Print summary of redactions
print("\n=== Redaction Summary ===")
for page in sorted(rows_by_page.keys()):
    rows = rows_by_page[page]
    print(f"\nPage {page} ({len(rows)} redactions):")
    for r in rows:
        text = r.get("text", "")[:40]
        label = r.get("label", "")
        print(f"  - [{label}] '{text}'")

# Generate review images
doc = fitz.open(PDF_PATH)
for p in range(1, doc.page_count + 1):
    page_obj = doc[p - 1]
    pix = page_obj.get_pixmap(dpi=180)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    draw = ImageDraw.Draw(img)
    page_rows = rows_by_page.get(p, [])

    for r in page_rows:
        x0 = float(r["xmin"]) * pix.width
        y0 = float(r["ymin"]) * pix.height
        x1 = float(r["xmax"]) * pix.width
        y1 = float(r["ymax"]) * pix.height
        draw.rectangle([x0, y0, x1, y1], outline="red", width=3)

    img.save(REVIEW_IMAGES_DIR / f"page_{p:03d}_review.png")
    print(f"Generated review image for page {p} ({len(page_rows)} boxes)")

print(f"\nReview images saved to: {REVIEW_IMAGES_DIR}")
