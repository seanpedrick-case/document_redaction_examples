"""Generate review images showing current redaction boxes overlaid on each PDF page."""
import csv
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont

PDF_PATH = next(Path("output").glob("*_redacted.pdf"))
REVIEW_CSV = next(Path("output").glob("*_review_file.csv"))
ORIG_PDF = Path("Partnership-Agreement-Toolkit_0_0.pdf")
OUT_DIR = Path("output/review_images")
OUT_DIR.mkdir(parents=True, exist_ok=True)

print(f"PDF: {PDF_PATH.name}")
print(f"CSV: {REVIEW_CSV.name}")

with REVIEW_CSV.open("r", newline="", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

rows_by_page = {}
for r in rows:
    p = int(float(r.get("page", "0") or 0))
    rows_by_page.setdefault(p, []).append(r)

# Use original PDF for clearer images
doc = fitz.open(str(ORIG_PDF))
print(f"Generating images for {doc.page_count} pages...")

for p in range(1, doc.page_count + 1):
    pix = doc[p - 1].get_pixmap(dpi=180)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    # Downscale for vision compatibility
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
        draw.rectangle([x0, y0, x1, y1], outline="red", width=3)
        label = r.get("label", "")
        text = r.get("text", "")[:20]
        draw.text((x0, max(0, y0 - 14)), f"{label}:{text}", fill="red")

    out_path = OUT_DIR / f"page_{p:03d}.png"
    img.save(out_path)
    n_boxes = len(rows_by_page.get(p, []))
    print(f"  Page {p}: {n_boxes} boxes -> {out_path.name}")

print(f"\nImages saved to: {OUT_DIR}")
