import csv
from pathlib import Path

# Read final review CSV
OUTPUT_DIR = Path("output_final")
FINAL_CSV = list(OUTPUT_DIR.glob("*_review_file.csv"))[0]

print(f"Verifying final redactions: {FINAL_CSV.name}\n")

with FINAL_CSV.open("r", newline="", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

print(f"Total redactions: {len(rows)}\n")

# Group by page
by_page = {}
for r in rows:
    page = int(float(r.get("page", "0") or 0))
    by_page.setdefault(page, []).append(r)

# Print summary
print("=" * 70)
print("FINAL REDACTION SUMMARY BY PAGE")
print("=" * 70)

for page in sorted(by_page.keys()):
    rows = by_page[page]
    print(f"\nPage {page} ({len(rows)} redactions):")
    for r in rows:
        text = r.get("text", "")[:40]
        label = r.get("label", "")
        print(f"  - [{label:12}] '{text}'")

# Verify rules
print("\n" + "=" * 70)
print("RULE VERIFICATION")
print("=" * 70)

# Rule 1: No country names redacted
print("\n1. Country names removed (if any were redacted):")
country_terms = ["UK", "United Kingdom", "USA", "America", "Australia"]
country_found = False
for r in rows:
    text = r.get("text", "").lower()
    for term in country_terms:
        if term.lower() in text:
            print(f"  WARNING: Found '{term}' in redaction: '{r.get('text')}'")
            country_found = True
if not country_found:
    print("  PASS - No country names in redactions")

# Rule 2: No Giuliani redactions
print("\n2. Rudy Giuliani redactions removed:")
giuliani_found = False
for r in rows:
    text = r.get("text", "").lower()
    if "giuliani" in text or "rudy" in text:
        print(f"  WARNING: Found Giuliani in redaction: '{r.get('text')}'")
        giuliani_found = True
if not giuliani_found:
    print("  PASS - No Giuliani redactions found")

# Rule 3: London redactions added
print("\n3. London mentions redacted:")
london_count = 0
for r in rows:
    text = r.get("text", "").lower()
    if "london" in text:
        print(f"  FOUND: '{r.get('text')}' on page {r.get('page')}")
        london_count += 1
print(f"  Total London redactions: {london_count}")

# Rule 4: Sister City redactions added
print("\n4. Sister City mentions redacted:")
sister_count = 0
for r in rows:
    text = r.get("text", "").lower()
    if "sister" in text:
        print(f"  FOUND: '{r.get('text')}' on page {r.get('page')}")
        sister_count += 1
print(f"  Total Sister City redactions: {sister_count}")

# Rule 5: Signatures added
print("\n5. Signature areas redacted:")
sig_count = 0
for r in rows:
    label = r.get("label", "").lower()
    text = r.get("text", "").lower()
    if "signature" in label or "signature" in text:
        print(f"  FOUND: Page {r.get('page')} - '{r.get('text')}'")
        sig_count += 1
print(f"  Total signature redactions: {sig_count}")

# Summary by label
print("\n" + "=" * 70)
print("REDACTIONS BY LABEL TYPE")
print("=" * 70)

by_label = {}
for r in rows:
    label = r.get("label", "UNKNOWN")
    by_label.setdefault(label, []).append(r)

for label in sorted(by_label.keys()):
    count = len(by_label[label])
    print(f"  {label}: {count}")

print("\n" + "=" * 70)
print("VERIFICATION COMPLETE")
print("=" * 70)
