import csv
import json
import secrets
from pathlib import Path

# Paths
OUTPUT_DIR = Path("output")
REVIEW_CSV = list(OUTPUT_DIR.glob("*_review_file.csv"))[0]
OUTPUT_CSV = Path("modified_review_file.csv")

print(f"Reading: {REVIEW_CSV.name}")

# Read current review CSV
with REVIEW_CSV.open("r", newline="", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    original_rows = list(reader)

print(f"Original redaction count: {len(original_rows)}")

# Load OCR search results
with open("ocr_search_results.json", "r", encoding="utf-8") as f:
    ocr_results = json.load(f)

# Filter out rows containing "Giuliani" (rule: remove all redactions for Rudy Giuliani)
filtered_rows = []
removed_count = 0
for row in original_rows:
    text = row.get("text", "").lower()
    if "giuliani" in text:
        print(f"  REMOVING: [{row.get('label')}] '{row.get('text')}' on page {row.get('page')}")
        removed_count += 1
    else:
        filtered_rows.append(row)

print(f"\nRemoved {removed_count} Giuliani-related redactions")
print(f"Remaining redactions: {len(filtered_rows)}")

# Add new redactions based on OCR results
new_redactions = []

# Helper to create a redaction row
def create_redaction_row(page, label, text, xmin, ymin, xmax, ymax, image_value=None):
    # Get image value from existing rows for same page if not provided
    if image_value is None:
        same_page = [r for r in original_rows if int(float(r.get("page", "0") or 0)) == int(page)]
        if same_page:
            image_value = same_page[0].get("image", "")
        else:
            image_value = f"placeholder_image_{max(int(page) - 1, 0)}.png"

    return {
        "image": image_value,
        "page": str(page),
        "label": label,
        "color": "(0, 0, 0)",
        "xmin": f"{xmin:.6f}",
        "ymin": f"{ymin:.6f}",
        "xmax": f"{xmax:.6f}",
        "ymax": f"{ymax:.6f}",
        "id": secrets.token_hex(8),
        "text": text,
    }

# 1. Add redactions for "London" mentions (Page 5)
print("\nAdding London redactions...")
london_matches = ocr_results.get("london", [])
for match in london_matches:
    page = int(match["page"])
    text = match["text"]
    # Add a small padding around the word
    x0 = float(match["word_x0"]) - 0.005
    y0 = float(match["word_y0"]) - 0.003
    x1 = float(match["word_x1"]) + 0.005
    y1 = float(match["word_y1"]) + 0.003

    row = create_redaction_row(page, "LOCATION", text, x0, y0, x1, y1)
    new_redactions.append(row)
    print(f"  Added: '{text}' on page {page}")

# 2. Add redactions for "SisterCities" header (Pages 1, 2, 3, 5, 6, 7)
print("\nAdding SisterCities redactions...")
sister_matches = ocr_results.get("sister_city", [])
seen_pages = set()
for match in sister_matches:
    page = int(match["page"])
    if page in seen_pages:
        continue
    seen_pages.add(page)

    text = match["text"]
    x0 = float(match["word_x0"]) - 0.01
    y0 = float(match["word_y0"]) - 0.005
    x1 = float(match["word_x1"]) + 0.01
    y1 = float(match["word_y1"]) + 0.005

    row = create_redaction_row(page, "CUSTOM", text, x0, y0, x1, y1)
    new_redactions.append(row)
    print(f"  Added: '{text}' on page {page}")

# 3. Add signature redactions (near "Signed" text areas)
# Based on typical document layout, signatures are usually near the bottom of pages
# Looking at the OCR, signed/signature appears at:
# Page 4, Line 30: 'Signed' at (0.222745, 0.733939)
# Page 5, Line 40: 'Signed' at (0.456863, 0.797273)
print("\nAdding signature redactions...")

# Signature zones based on typical document layout and "Signed" occurrences
signature_specs = [
    # Page 3 - near signed text at bottom
    {"page": 3, "zone": "bottom_left", "text": "signature area"},
    # Page 4 - Signed at line 30
    {"page": 4, "zone": "bottom_right", "text": "signature area"},
    # Page 5 - Signed at line 40
    {"page": 5, "zone": "bottom_left", "text": "signature area"},
    # Page 7 - near bottom signatures
    {"page": 7, "zone": "bottom_left", "text": "signature area"},
]

ZONE_PRESETS = {
    "top_left": (0.05, 0.08, 0.45, 0.18),
    "top_right": (0.55, 0.08, 0.95, 0.18),
    "mid_left": (0.05, 0.40, 0.45, 0.52),
    "mid_right": (0.55, 0.40, 0.95, 0.52),
    "bottom_left": (0.05, 0.78, 0.45, 0.90),
    "bottom_right": (0.55, 0.78, 0.95, 0.90),
}

for spec in signature_specs:
    page = spec["page"]
    zone_name = spec["zone"]
    text = spec["text"]
    xmin, ymin, xmax, ymax = ZONE_PRESETS[zone_name]

    row = create_redaction_row(page, "SIGNATURE", text, xmin, ymin, xmax, ymax)
    new_redactions.append(row)
    print(f"  Added: signature zone on page {page} ({zone_name})")

# Combine all redactions
all_rows = filtered_rows + new_redactions

# Write modified CSV
with OUTPUT_CSV.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(all_rows)

print(f"\n{'='*60}")
print(f"Modified review CSV written to: {OUTPUT_CSV}")
print(f"Total redactions: {len(all_rows)}")
print(f"  - Original (filtered): {len(filtered_rows)}")
print(f"  - New redactions: {len(new_redactions)}")
print(f"{'='*60}")

# Print summary by page
print("\nSummary by page:")
by_page = {}
for row in all_rows:
    page = int(float(row.get("page", "0") or 0))
    by_page.setdefault(page, []).append(row)

for page in sorted(by_page.keys()):
    rows = by_page[page]
    print(f"\nPage {page} ({len(rows)} redactions):")
    for r in rows:
        text = r.get("text", "")[:30]
        label = r.get("label", "")
        print(f"  - [{label:12}] '{text}'")
