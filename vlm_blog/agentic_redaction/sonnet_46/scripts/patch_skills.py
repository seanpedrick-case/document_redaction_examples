"""Patch doc-redaction skill files with lessons learned from the Partnership Agreement task."""
from pathlib import Path

# ── doc-redaction-app/SKILL.md ────────────────────────────────────────────────
app_skill = Path(r"C:\Users\Sean\.cursor\skills-cursor\doc-redaction-app\SKILL.md")
content = app_skill.read_text(encoding="utf-8")

PREVIEW_SECTION = """

### Pre-apply coordinate preview (saves round-trips)

Before sending a modified CSV to `/review_apply`, render the proposed boxes on the **original PDF locally**. This lets you confirm geometry without a server round-trip and is especially valuable for manually placed boxes (signatures, decorative text, stamps).

Add a percentage grid to measure where boxes land relative to page content:

```python
import csv, fitz
from pathlib import Path
from PIL import Image, ImageDraw

PDF = Path("input/document.pdf")
CSV = Path("output/document_review_file_edited.csv")
OUT = Path("output/preview"); OUT.mkdir(exist_ok=True)

with CSV.open(encoding="utf-8-sig") as f:
    rows = {}
    for r in csv.DictReader(f):
        rows.setdefault(int(float(r.get("page", 0) or 0)), []).append(r)

doc = fitz.open(str(PDF))
for p in range(1, doc.page_count + 1):
    pix = doc[p - 1].get_pixmap(dpi=150)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    draw = ImageDraw.Draw(img)
    for pct in range(0, 100, 5):           # percentage grid
        y = int(pct / 100 * pix.height)
        draw.line([(0, y), (60, y)], fill="red", width=1)
        draw.text((2, y), f"{pct}%", fill="red")
    for r in rows.get(p, []):
        draw.rectangle(
            [float(r["xmin"]) * pix.width, float(r["ymin"]) * pix.height,
             float(r["xmax"]) * pix.width, float(r["ymax"]) * pix.height],
            outline="orange", width=3,
        )
    img.save(OUT / f"page_{p:03d}.png")
```

Even a perfect local preview does not guarantee pixel-perfect alignment in the final redacted PDF — the server applies boxes in the original PDF coordinate space, which can render slightly differently to a local PyMuPDF render. Always verify the actual applied output after each apply run.

"""

marker = "Apply the same pattern to `*_review_file.csv` and `*_redactions_for_review.pdf`."
assert marker in content, f"Marker not found in {app_skill}"
content = content.replace(marker, marker + PREVIEW_SECTION)
app_skill.write_text(content, encoding="utf-8")
print(f"Patched: {app_skill}")

# ── doc-redaction-modifications/SKILL.md ─────────────────────────────────────
mod_skill = Path(r"C:\Users\Sean\.cursor\skills-cursor\doc-redaction-modifications\SKILL.md")
content = mod_skill.read_text(encoding="utf-8")

# 1) Update version
content = content.replace("version: 2.0.2", "version: 2.0.3")

# 2) Replace one-page loop with better guidance
OLD_LOOP = """## One-page execution loop

Run this loop for each page:
1. Edit only one target page in `*_review_file.csv`.
2. Apply with `/review_apply`.
3. Download outputs.
4. Verify page review export image visually.
5. Move to next page."""

NEW_LOOP = """## Execution loop

For a full document review, edit all pages in a single modified CSV and apply once. Use page-by-page apply only if you need to compare individual pages mid-session.

Recommended order:
1. Load the `*_review_file.csv` into a script (not manually).
2. Apply all removals, additions, and coordinate corrections programmatically.
3. Generate a local pre-apply preview (see `doc-redaction-app/SKILL.md` — Pre-apply coordinate preview) to check box positions without a server round-trip.
4. Apply the edited CSV via `/review_apply`.
5. Download and verify outputs — always sort by `st_mtime` to pick the newest file (see below).
6. If corrections are needed, update the script and repeat from step 2.

### Always sort outputs by modification time

Each `/review_apply` call generates a **new hash-prefixed filename**. After several iterations you will have multiple versions in the output folder. Always sort by `st_mtime` to pick the most recent:

```python
from pathlib import Path
latest_pdf = sorted(
    Path("output_final").glob("*_redacted.pdf"),
    key=lambda f: f.stat().st_mtime, reverse=True
)[0]
latest_csv = sorted(
    Path("output_final").glob("*_review_file.csv"),
    key=lambda f: f.stat().st_mtime, reverse=True
)[0]
```"""

assert OLD_LOOP in content, "One-page loop section not found"
content = content.replace(OLD_LOOP, NEW_LOOP)

# 3) Add signatures + OCR-invisible content sections before "Adding redactions on scanned/image pages"
SIGNATURES_SECTION = """## Signatures — always manual (never auto-detected)

The app's PII detection never finds handwritten signatures. Treat signature redaction as a **mandatory manual step** for any document that will be signed.

### Workflow
1. Render each page at high DPI and visually locate all signature zones.
2. Use nearby OCR words (printed name below the line, "Mayor", "Signed", etc.) as coordinate anchors.
3. Estimate `ymin`/`ymax` from a percentage-grid preview image.
4. Add a `SIGNATURE` row per signature and a separate `PERSON` row for the printed name beneath it if that name is also sensitive.
5. Verify with a local preview before applying.

Typical coordinate starting estimates (refine per document):
- Signature line area: `ymin = y_of_printed_name - 0.06`, `ymax = y_of_printed_name - 0.005`
- Printed name: `ymin = y_of_printed_name`, `ymax = y_of_printed_name + 0.02`

Expect 1-3 iterations before each signature is correctly covered.

## OCR-invisible content (calligraphic text, stamps, decorative headings)

OCR returns nothing for decorative or hand-lettered headings. Treat any visually prominent heading or stamp as a potential miss.

### Detection
- Render each page and look for text that is not reflected in `*_ocr_results_with_words_*.csv`.
- Common culprits: calligraphic section titles, official seals, watermarks, rubber stamps.

### Coordinate estimation
1. Render the page with a percentage grid overlay (5% intervals).
2. Read the approximate `ymin`/`ymax` from the grid for the undetected text block.
3. Add a `CUSTOM` row with those coordinates and a descriptive `text` value.
4. Preview locally, apply, verify. Expect 3-5 iterations for decorative text because local render ≠ server render exactly.

## Cross-line phrases ("Sister City", "Sister Cities")

When a two-word phrase spans two OCR lines (different `y` values), merging them into one box produces an oversized rectangle that covers unrelated text. Use a split-box approach instead:

```python
# r1 = OCR row for word 1 ("Sister"), r2 = OCR row for word 2 ("City")
if abs(float(r1["ymin"]) - float(r2["ymin"])) > 0.01:
    # words on different lines — two separate boxes
    new_rows.append(make_row(page, "CUSTOM", r1["xmin"], r1["ymin"], r1["xmax"], r1["ymax"], "Sister"))
    new_rows.append(make_row(page, "CUSTOM", r2["xmin"], r2["ymin"], r2["xmax"], r2["ymax"], "City"))
else:
    # same line — single merged box
    new_rows.append(make_row(page, "CUSTOM",
        min(r1["xmin"], r2["xmin"]), min(r1["ymin"], r2["ymin"]),
        max(r1["xmax"], r2["xmax"]), max(r1["ymax"], r2["ymax"]),
        "Sister City"))
```

"""

OLD_SCANNED = "## Adding redactions on scanned/image pages (no OCR boxes)"
assert OLD_SCANNED in content, "Scanned-page section not found"
content = content.replace(OLD_SCANNED, SIGNATURES_SECTION + OLD_SCANNED)

# 4) Add a per-page checklist before the Completion checklist
PER_PAGE_CHECKLIST = """## Per-page review checklist

Run through this for every page before signing off:

- [ ] All named individuals redacted (check `*_ocr_results_with_words_*.csv` for full names).
- [ ] All signatures redacted (handwritten lines, initials, flourishes).
- [ ] All printed names below signatures redacted.
- [ ] Target phrases redacted on this page (e.g. "London", "Sister City", email addresses).
- [ ] No false positives: country names, city names, organisation names not flagged as PII left unredacted.
- [ ] All boxes correctly sized — no box clips adjacent text or floats into wrong area.
- [ ] OCR-invisible content checked visually (decorative headings, stamps, seals).

"""

OLD_CHECKLIST = "## Completion checklist"
assert OLD_CHECKLIST in content, "Completion checklist not found"
content = content.replace(OLD_CHECKLIST, PER_PAGE_CHECKLIST + OLD_CHECKLIST)

mod_skill.write_text(content, encoding="utf-8")
print(f"Patched: {mod_skill}")
print("All done.")
