import csv
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image, ImageDraw


FINAL_DIR = Path("output_final/partnership_toolkit/final_apply_002").resolve()


def pick_file(suffix: str) -> Path:
    matches = sorted(FINAL_DIR.glob(f"*{suffix}"))
    if not matches:
        raise FileNotFoundError(f"No file matching *{suffix} in {FINAL_DIR}")
    return matches[0]


def main():
    out_dir = FINAL_DIR / "review_images"
    out_dir.mkdir(parents=True, exist_ok=True)

    pdf_path = pick_file("_redacted.pdf")
    csv_path = pick_file("_review_file.csv")

    with csv_path.open("r", newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    rows_by_page: dict[int, list[dict]] = {}
    for r in rows:
        try:
            p = int(float(r.get("page", "0") or 0))
        except Exception:
            continue
        rows_by_page.setdefault(p, []).append(r)

    doc = fitz.open(pdf_path)
    for p in range(1, doc.page_count + 1):
        pix = doc[p - 1].get_pixmap(dpi=180)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        draw = ImageDraw.Draw(img)
        for r in rows_by_page.get(p, []):
            try:
                x0 = float(r["xmin"]) * pix.width
                y0 = float(r["ymin"]) * pix.height
                x1 = float(r["xmax"]) * pix.width
                y1 = float(r["ymax"]) * pix.height
            except Exception:
                continue
            draw.rectangle([x0, y0, x1, y1], outline="red", width=3)
        img.save(out_dir / f"page_{p:03d}.png")

    print("Wrote review images to:", out_dir)


if __name__ == "__main__":
    main()

