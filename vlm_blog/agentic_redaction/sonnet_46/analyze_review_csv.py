import csv
import json
from pathlib import Path

# Find the review CSV in output directory
OUTPUT_DIR = Path("output")
csv_files = list(OUTPUT_DIR.glob("*_review_file.csv"))

if not csv_files:
    print("ERROR: Could not find review CSV file")
    exit(1)

REVIEW_CSV = csv_files[0]
print(f"Analyzing: {REVIEW_CSV.name}\n")

# Read review CSV
with REVIEW_CSV.open("r", newline="", encoding="utf-8-sig") as f:
    review_rows = list(csv.DictReader(f))

print(f"Total redaction boxes: {len(review_rows)}\n")

# Group rows by page
rows_by_page = {}
for r in review_rows:
    page = int(float(r.get("page", "0") or 0))
    rows_by_page.setdefault(page, []).append(r)

print(f"Pages with redactions: {sorted(rows_by_page.keys())}\n")

# Print detailed summary
print("=" * 80)
print("DETAILED REDACTION SUMMARY")
print("=" * 80)

for page in sorted(rows_by_page.keys()):
    rows = rows_by_page[page]
    print(f"\n--- Page {page} ({len(rows)} redactions) ---")
    for i, r in enumerate(rows):
        text = r.get("text", "")
        label = r.get("label", "")
        redaction_id = r.get("id", "")
        bbox = f"({r.get('xmin','?')}, {r.get('ymin','?')}, {r.get('xmax','?')}, {r.get('ymax','?')})"
        print(f"  [{i+1}] {redaction_id[:8]}... | {label:15} | '{text}'")
        print(f"       bbox: {bbox}")

# Summary by label
print("\n" + "=" * 80)
print("REDACTIONS BY LABEL TYPE")
print("=" * 80)

by_label = {}
for r in review_rows:
    label = r.get("label", "UNKNOWN")
    by_label.setdefault(label, []).append(r)

for label in sorted(by_label.keys()):
    rows = by_label[label]
    print(f"\n{label} ({len(rows)} redactions):")
    for r in rows:
        page = int(float(r.get("page", "0") or 0))
        text = r.get("text", "")[:50]
        print(f"  Page {page}: '{text}'")

# Check for specific terms
print("\n" + "=" * 80)
print("CHECKING FOR SPECIFIC TERMS")
print("=" * 80)

search_terms = {
    "country": ["UK", "United Kingdom", "Great Britain", "USA", "United States", "America", "Australia"],
    "giuliani": ["Giuliani", "Rudy", "rudy.giuliani"],
    "london": ["London"],
    "sister_city": ["Sister City", "Sister"],
    "signature": ["signature", "signed", "Signature"],
}

for category, terms in search_terms.items():
    print(f"\n{category.upper()}:")
    found = False
    for r in review_rows:
        text = r.get("text", "")
        for term in terms:
            if term.lower() in text.lower():
                page = int(float(r.get("page", "0") or 0))
                label = r.get("label", "")
                print(f"  Page {page} [{label}]: '{text}'")
                found = True
                break
    if not found:
        print(f"  (No redactions found matching {terms})")

# Save detailed analysis to JSON for reference
analysis = {
    "total_redactions": len(review_rows),
    "pages": sorted(rows_by_page.keys()),
    "by_page": {str(p): [{k: r[k] for k in r} for r in rows] for p, rows in rows_by_page.items()},
    "by_label": {label: [{k: r[k] for k in r} for r in rows] for label, rows in by_label.items()},
}

analysis_file = Path("review_analysis.json")
with open(analysis_file, "w", encoding="utf-8") as f:
    json.dump(analysis, f, indent=2)

print(f"\n\nFull analysis saved to: {analysis_file}")
