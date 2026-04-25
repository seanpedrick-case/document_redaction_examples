import csv
from pathlib import Path
import re

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
    reader = csv.DictReader(f)
    ocr_rows = list(reader)

print(f"Total OCR rows: {len(ocr_rows)}\n")

# Search patterns
patterns = {
    "sister_city": re.compile(r'sister\s*city|sister\s*cities', re.IGNORECASE),
    "london": re.compile(r'london', re.IGNORECASE),
    "giuliani": re.compile(r'giuliani|rudy', re.IGNORECASE),
    "signature": re.compile(r'signature|signed', re.IGNORECASE),
    "country": re.compile(r'uk|united\s*kingdom|united\s*states|america|australia|great\s*britain', re.IGNORECASE),
}

# Search for each pattern
results = {key: [] for key in patterns.keys()}

for row in ocr_rows:
    text = row.get("word_text", "") or ""
    line_text = row.get("line_text", "") or ""
    full_text = text + " " + line_text

    for key, pattern in patterns.items():
        if pattern.search(full_text):
            results[key].append({
                "page": row.get("page", "?"),
                "line": row.get("line", "?"),
                "text": text,
                "line_text": line_text,
                "word_x0": row.get("word_x0"),
                "word_y0": row.get("word_y0"),
                "word_x1": row.get("word_x1"),
                "word_y1": row.get("word_y1"),
            })

# Print results
print("=" * 80)
for key, matches in results.items():
    print(f"\n{key.upper().replace('_', ' ')} ({len(matches)} matches):")
    if matches:
        # Remove duplicates (same page/line/text)
        seen = set()
        unique_matches = []
        for m in matches:
            key_tuple = (m["page"], m["line"], m["text"])
            if key_tuple not in seen:
                seen.add(key_tuple)
                unique_matches.append(m)

        for m in unique_matches[:30]:  # Limit output
            print(f"  Page {m['page']}, Line {m['line']}: '{m['text']}' (line: '{m['line_text'][:40]}...')")
            print(f"    bbox: ({m['word_x0']}, {m['word_y0']}, {m['word_x1']}, {m['word_y1']})")
    else:
        print("  (No matches)")

# Save results for later use
import json
with open("ocr_search_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)
print("\n\nResults saved to ocr_search_results.json")
