import csv
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image, ImageDraw


PDF_PATH = Path(
    "output/partnership_toolkit/after_apply_001/95664c60feb64fe69932bb501abb4343_Partnership-Agreement-Toolkit_0_0_redacted.pdf"
).resolve()
REVIEW_CSV = Path(
    "output/partnership_toolkit/after_apply_001/95664c60feb64fe69932bb501abb4343_Partnership-Agreement-Toolkit_0_0.pdf_review_file.csv"
).resolve()
OUT_DIR = Path("output/partnership_toolkit/review_images_after_apply_001").resolve()


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with REVIEW_CSV.open("r", newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    rows_by_page = {}
    for r in rows:
        p = int(float(r.get("page", "0") or 0))
        rows_by_page.setdefault(p, []).append(r)

    doc = fitz.open(PDF_PATH)
    for p in range(1, doc.page_count + 1):
        pix = doc[p - 1].get_pixmap(dpi=180)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        draw = ImageDraw.Draw(img)
        for r in rows_by_page.get(p, []):
            x0 = float(r["xmin"]) * pix.width
            y0 = float(r["ymin"]) * pix.height
            x1 = float(r["xmax"]) * pix.width
            y1 = float(r["ymax"]) * pix.height
            draw.rectangle([x0, y0, x1, y1], outline="red", width=3)
        img.save(OUT_DIR / f"page_{p:03d}.png")

    print("Wrote review images to:", OUT_DIR)


if __name__ == "__main__":
    main()

