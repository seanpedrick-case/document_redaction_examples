import csv
from pathlib import Path

# Find OCR results CSV
OUTPUT_DIR = Path("output")
csv_files = list(OUTPUT_DIR.glob("*_ocr_results_with_words_*.csv"))

if not csv_files:
    print("ERROR: Could not find OCR results CSV file")
    exit(1)

OCR_CSV = csv_files[0]
print(f"Analyzing OCR: {OCR_CSV.name}\n")

# Read OCR CSV
with OCR_CSV.open("r", newline="", encoding="utf-8-sig") as f:
    ocr_rows = list(csv.DictReader(f))

print(f"Total OCR words: {len(ocr_rows)}\n")

# Search for specific terms
search_terms = {
    "london": ["London", "london"],
    "sister_city": ["Sister City", "sister city", "Sister Cities", "sister cities"],
    "giuliani": ["Giuliani", "giuliani", "Rudy"],
    "country": ["UK", "United Kingdom", "USA", "United States", "America", "Australia", "Great Britain"],
    "signature": ["signature", "Signature", "Signed", "signed"],
}

print("=" * 80)
print("SEARCHING OCR FOR SPECIFIC TERMS")
print("=" * 80)

for category, terms in search_terms.items():
    print(f"\n{category.upper()}:")
    matches = []
    for r in ocr_rows:
        text = r.get("text", "")
        for term in terms:
            if term.lower() in text.lower():
                page = r.get("page_num", "?")
                bbox = f"({r.get('x0','?')}, {r.get('y0','?')}, {r.get('x1','?')}, {r.get('y1','?')})"
                matches.append({
                    "page": page,
                    "text": text,
                    "bbox": bbox,
                    "x0": r.get("x0"),
                    "y0": r.get("y0"),
                    "x1": r.get("x1"),
                    "y1": r.get("y1"),
                })
                break

    if matches:
        for m in matches:
            print(f"  Page {m['page']}: '{m['text']}' at {m['bbox']}")
    else:
        print(f"  (No matches found)")

# Also look for any names that might be signatures or need redaction
print("\n" + "=" * 80)
print("ALL OCR TEXT BY PAGE (for reference)")
print("=" * 80)

# Group by page
by_page = {}
for r in ocr_rows:
    page = int(r.get("page_num", 0))
    by_page.setdefault(page, []).append(r)

for page in sorted(by_page.keys()):
    rows = by_page[page]
    print(f"\n--- Page {page} ({len(rows)} words) ---")
    for r in rows[:50]:  # Limit to first 50 words per page
        text = r.get("text", "")
        x0 = r.get("x0", "?")
        y0 = r.get("y0", "?")
        print(f"  '{text}' at ({x0}, {y0})")
    if len(rows) > 50:
        print(f"  ... and {len(rows) - 50} more words")
