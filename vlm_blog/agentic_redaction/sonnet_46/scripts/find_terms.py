"""Search OCR output for London and Sister City mentions."""
import csv
from pathlib import Path

ocr_path = next(Path("output").glob("*_ocr_results_with_words_*.csv"))
with ocr_path.open("r", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

print("=== LONDON mentions ===")
for r in rows:
    if "london" in r["word_text"].lower():
        print(f"  Page {r['page']}: text={repr(r['word_text'])} x0={r['word_x0']} y0={r['word_y0']} x1={r['word_x1']} y1={r['word_y1']}")

print()
print("=== SISTER mentions ===")
for i, r in enumerate(rows):
    if "sister" in r["word_text"].lower():
        # Also look at next word to see if it's 'City' or 'Cities'
        next_word = rows[i+1]["word_text"] if i+1 < len(rows) else ""
        print(f"  Page {r['page']}: text={repr(r['word_text'])} next={repr(next_word)} x0={r['word_x0']} y0={r['word_y0']} x1={r['word_x1']} y1={r['word_y1']}")

print()
print("=== CITY mentions adjacent to Sister ===")
for i, r in enumerate(rows):
    if "city" in r["word_text"].lower() or "cities" in r["word_text"].lower():
        prev_word = rows[i-1]["word_text"] if i > 0 else ""
        if "sister" in prev_word.lower():
            print(f"  Page {r['page']}: Sister+City text={repr(r['word_text'])} x0={r['word_x0']} y0={r['word_y0']} x1={r['word_x1']} y1={r['word_y1']}")
