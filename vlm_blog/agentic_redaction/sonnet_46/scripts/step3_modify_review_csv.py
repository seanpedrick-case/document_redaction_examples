"""
Comprehensive review CSV modification for Partnership Agreement Toolkit redaction.

Changes:
1. Remove Giuliani-related detections (page 5)
2. Remove false positive detections (page 6: Tas, patel cea, a patel, cea, se Digger)
3. Remove duplicate overlapping boxes (pages 4, 7)
4. Fix incomplete boxes (page 4: Lee -> Lee P.Brown)
5. Add signature boxes (pages 4, 5, 6, 7)
6. Add London redactions (page 5)
7. Add Sister City/Cities redactions (pages 1-7)
"""
import csv
import secrets
from pathlib import Path

REVIEW_CSV = next(Path("output").glob("*_review_file.csv"))
OCR_CSV = next(Path("output").glob("*_ocr_results_with_words_*.csv"))
OUT_CSV = Path("output") / REVIEW_CSV.name.replace("_review_file.csv", "_review_file_edited.csv")

# ── Load existing review CSV ─────────────────────────────────────────────────
with REVIEW_CSV.open("r", newline="", encoding="utf-8-sig") as f:
    existing_rows = list(csv.DictReader(f))
fieldnames = list(existing_rows[0].keys())
image_col = fieldnames[0]

# Image value pattern: /home/user/app/input/f7e18b91/bf1c2a..._{page-1}.png
base_hash = "bf1c2a623775423b8347fd997ac98985"
run_id = "f7e18b91"
IMAGE_BASE = f"/home/user/app/input/{run_id}/{base_hash}_Partnership-Agreement-Toolkit_0_0.pdf_"

def image_for_page(page_num):
    """Return image path for given 1-based page number."""
    return f"{IMAGE_BASE}{page_num - 1}.png"

# Get existing image values for pages that already have rows
existing_image_by_page = {}
for r in existing_rows:
    pg = int(float(r.get("page", 0) or 0))
    if pg not in existing_image_by_page and r.get(image_col):
        existing_image_by_page[pg] = r[image_col]

def get_image(page_num):
    return existing_image_by_page.get(page_num, image_for_page(page_num))

def make_row(page, label, xmin, ymin, xmax, ymax, text="", color="(0, 0, 0)"):
    return {
        image_col: get_image(page),
        "page": str(page),
        "label": label,
        "color": color,
        "xmin": f"{xmin:.6f}",
        "ymin": f"{ymin:.6f}",
        "xmax": f"{xmax:.6f}",
        "ymax": f"{ymax:.6f}",
        "id": secrets.token_hex(6),
        "text": text,
    }

# ── Load OCR words CSV ────────────────────────────────────────────────────────
with OCR_CSV.open("r", newline="", encoding="utf-8-sig") as f:
    ocr_rows = list(csv.DictReader(f))

# ── Step 1: Filter existing rows ─────────────────────────────────────────────
# Remove text (strip quotes/punctuation for matching)
def clean(s):
    return s.strip().strip('"\'').strip().lower()

REMOVE_TEXTS = {
    # Giuliani-related (page 5)
    "jy w",
    "w. giuliani ken livingston",
    "w . giuliani",
    # Page 6 false positives
    "tas",
    "patel cea",
    "a patel",
    "cea",
    "se digger",
    # Duplicate boxes - page 4 (keep the combined one, fix it)
    "lee",                              # standalone "Lee" duplicate
    "mohammed bin butti al hamed",      # partial duplicate
}

def should_remove(row):
    t = clean(row.get("text", ""))
    pg = row.get("page", "")
    # Remove Giuliani rows on page 5
    if pg == "5" and t in {"jy w", "w. giuliani ken livingston", "w . giuliani"}:
        return True
    # Remove page 6 false positives
    if pg == "6" and t in {"tas", "patel cea", "a patel", "cea", "se digger"}:
        return True
    # Remove duplicate boxes on page 4
    if pg == "4" and t == "lee":
        return True
    if pg == "4" and t == "mohammed bin butti al hamed":
        return True
    return False

kept_rows = [r for r in existing_rows if not should_remove(r)]

# ── Step 2: Modify existing rows ─────────────────────────────────────────────
for r in kept_rows:
    pg = r.get("page", "")
    t = clean(r.get("text", ""))
    # Page 4: extend combined box to include "P.Brown" (xmax 0.764314 -> 0.848235)
    if pg == "4" and t == "mohammed bin butti al hamed lee":
        r["xmax"] = "0.848235"
    # Page 7: partial boxes - extend RONGMAO to include ZHANG too
    # Note: We keep all 6 page-7 rows; they cover different specific mentions
    # but some are partial. Fix RONGMAO (at sig line) to start at ZHANG position
    if pg == "7" and t == "rongmao":
        # Extend left to cover "ZHANG RONGMAO" in the signature line
        r["xmin"] = "0.730980"

new_rows = list(kept_rows)

# ── Step 3: Add signature boxes ──────────────────────────────────────────────
# Page 4: Abu Dhabi-Houston
new_rows.append(make_row(4, "SIGNATURE", 0.158, 0.770, 0.460, 0.808, "Sheikh signature"))
new_rows.append(make_row(4, "SIGNATURE", 0.685, 0.770, 0.905, 0.808, "Mayor Brown signature"))

# Page 5: NYC-London (Giuliani + Ken Livingstone)
# Giuliani signature covers the large scrollwork area (OCR 'a' from 0.179-0.332, y 0.795-0.896)
new_rows.append(make_row(5, "SIGNATURE", 0.170, 0.795, 0.440, 0.878, "Giuliani signature"))
# Ken Livingstone signature (right side, above Ken Livingston name at y=0.878)
new_rows.append(make_row(5, "SIGNATURE", 0.560, 0.795, 0.840, 0.878, "Livingstone signature"))

# Page 6: Long Beach - Beverly D'Neill + Jorge O. Zambrano
# Calligraphic "Sister City Agreement" title (OCR-invisible, add manually)
new_rows.append(make_row(6, "CUSTOM", 0.170, 0.165, 0.750, 0.390, "Sister City Agreement calligraphic"))
# Beverly D'Neill signature at ~y=0.71-0.76 (above printed name at y~0.77)
new_rows.append(make_row(6, "SIGNATURE", 0.330, 0.700, 0.730, 0.765, "Beverly D Neill signature"))
# Beverly D'Neill printed name (below signature, above Mayor title)
new_rows.append(make_row(6, "PERSON", 0.355, 0.757, 0.660, 0.778, "Beverly D Neill"))
# Jorge O. Zambrano signature (above "Ing. Jorge O. Zambrano" at y~0.826)
new_rows.append(make_row(6, "SIGNATURE", 0.390, 0.775, 0.720, 0.825, "Jorge Zambrano signature"))

# Page 7: Chicago-Shenyang - Richard M. Daley + Zhang Rongmao
# Daley signature (above THE HONORABLE RICHARD M. DALEY at y~0.822)
new_rows.append(make_row(7, "SIGNATURE", 0.178, 0.748, 0.448, 0.820, "Richard Daley signature"))
# Zhang Rongmao signature (above THE HONORABLE ZHANG RONGMAO at y~0.820)
new_rows.append(make_row(7, "SIGNATURE", 0.558, 0.748, 0.900, 0.820, "Zhang Rongmao signature"))

# ── Step 4: Add London redactions from OCR ────────────────────────────────────
# Only page 5 has "London" mentions based on OCR search
LONDON_OCCURRENCES = [
    # (page, x0, y0, x1, y1, text)
    (5, 0.43098,  0.356364, 0.572549, 0.366970, "CITY-LONDON"),   # title: CITY-LONDON
    (5, 0.652549, 0.403333, 0.712549, 0.413030, "London"),         # body text
    (5, 0.657255, 0.481515, 0.718431, 0.491212, "London"),         # body text
    (5, 0.610588, 0.640909, 0.670196, 0.650606, "London"),         # body text
    (5, 0.200392, 0.721212, 0.261176, 0.731212, "London"),         # "Mayor of London"
    (5, 0.703529, 0.910000, 0.763529, 0.920000, "London"),         # sig label "London"
]
for pg, x0, y0, x1, y1, text in LONDON_OCCURRENCES:
    new_rows.append(make_row(pg, "LOCATION", x0, y0, x1, y1, text))

# ── Step 5: Add Sister City/Cities redactions ─────────────────────────────────
# Find all Sister+City/Cities pairs in OCR (excluding logo and email)
SISTER_SKIP_TEXTS = {"sistercities"}  # logo token

sister_city_pairs = []
for i, r in enumerate(ocr_rows):
    word = r["word_text"]
    if not ("sister" in word.lower()):
        continue
    word_clean = word.lower().strip('"')
    if word_clean in SISTER_SKIP_TEXTS:
        continue
    if "sister-cities.org" in word.lower():
        continue  # skip email
    # Check next word
    if i + 1 >= len(ocr_rows):
        continue
    next_r = ocr_rows[i + 1]
    next_word = next_r["word_text"].lower().strip('"')
    if not (next_word.startswith("city") or next_word.startswith("cities") or next_word.startswith("cety")):
        continue
    # Check they're on same page
    if r["page"] != next_r["page"]:
        continue
    pg = int(r["page"])
    sy0, sy1 = float(r["word_y0"]), float(r["word_y1"])
    cy0, cy1 = float(next_r["word_y0"]), float(next_r["word_y1"])
    combined_text = f"{word} {next_r['word_text']}"
    # Detect cross-line pairs (y differ > 0.01): create two separate boxes
    if abs(sy0 - cy0) > 0.01:
        # Box 1: "Sister" word alone
        sister_city_pairs.append((pg, float(r["word_x0"]), sy0, float(r["word_x1"]), sy1, word))
        # Box 2: "City/Cities" word alone
        sister_city_pairs.append((pg, float(next_r["word_x0"]), cy0, float(next_r["word_x1"]), cy1, next_r["word_text"]))
        print(f"  Sister+City (cross-line split): page {pg} '{word}' + '{next_r['word_text']}'")
    else:
        x0 = min(float(r["word_x0"]), float(next_r["word_x0"]))
        y0 = min(sy0, cy0)
        x1 = max(float(r["word_x1"]), float(next_r["word_x1"]))
        y1 = max(sy1, cy1)
        sister_city_pairs.append((pg, x0, y0, x1, y1, combined_text))
        print(f"  Sister+City: page {pg} '{combined_text}' ({x0:.3f},{y0:.3f} -> {x1:.3f},{y1:.3f})")

for pg, x0, y0, x1, y1, text in sister_city_pairs:
    new_rows.append(make_row(pg, "CUSTOM", x0, y0, x1, y1, text))

# ── Step 6: Add extra redaction - "Sister Cities" in page 1 heading ──────────
# Also handle the "Sister City Relationship" heading text
# Check for any missed Sisters where next word isn't immediately 'city'
# (e.g. standalone "Sister Cities International" where Cities is already covered)
# This is handled by the above loop.

# ── Sort rows by page then ymin ───────────────────────────────────────────────
def sort_key(r):
    pg = int(float(r.get("page", 0) or 0))
    y = float(r.get("ymin", 0) or 0)
    x = float(r.get("xmin", 0) or 0)
    return (pg, y, x)

new_rows.sort(key=sort_key)

# ── Write modified CSV ────────────────────────────────────────────────────────
with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(new_rows)

print(f"\nOriginal rows: {len(existing_rows)}")
print(f"Modified rows: {len(new_rows)}")
print(f"Written to: {OUT_CSV}")

# Summary by page
by_page = {}
for r in new_rows:
    pg = r["page"]
    by_page.setdefault(pg, []).append(r)
print("\nRows by page:")
for pg in sorted(by_page.keys(), key=lambda x: int(x)):
    labels = [r["label"] for r in by_page[pg]]
    print(f"  Page {pg}: {len(labels)} rows {labels}")
