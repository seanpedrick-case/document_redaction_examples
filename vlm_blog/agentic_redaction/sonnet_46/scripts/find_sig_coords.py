"""Find signature area coordinates from OCR output."""
import csv
from pathlib import Path

ocr_path = next(Path("output").glob("*_ocr_results_with_words_*.csv"))
with ocr_path.open("r", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

for pg, threshold in [("4", 0.75), ("5", 0.78), ("6", 0.55), ("7", 0.73)]:
    print(f"=== Page {pg} near signature area (y>{threshold}) ===")
    for r in rows:
        if r["page"] == pg and float(r.get("word_y0", 0) or 0) > threshold:
            print(f"  text={repr(r['word_text'])} x0={r['word_x0']} y0={r['word_y0']} x1={r['word_x1']} y1={r['word_y1']}")
    print()
