"""Generate review images from the EDITED CSV to verify positions before applying."""
import csv
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image, ImageDraw

ORIG_PDF = Path("Partnership-Agreement-Toolkit_0_0.pdf")
EDITED_CSV = next(Path("output").glob("*_review_file_edited.csv"))
OUT_DIR = Path("output/review_images_edited")
OUT_DIR.mkdir(parents=True, exist_ok=True)

print(f"CSV: {EDITED_CSV.name}")

with EDITED_CSV.open("r", newline="", encoding="utf-8-sig") as f:
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

doc = fitz.open(str(ORIG_PDF))
print(f"Generating images for {doc.page_count} pages...")

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
        label = r.get("label", "")
        text = r.get("text", "")[:15]
        draw.text((x0, max(0, y0 - 12)), f"{label}:{text}", fill=color)

    out_path = OUT_DIR / f"page_{p:03d}.png"
    img.save(out_path)
    n_boxes = len(rows_by_page.get(p, []))
    print(f"  Page {p}: {n_boxes} boxes -> {out_path.name}")

print(f"\nEdited review images saved to: {OUT_DIR}")
