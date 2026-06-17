# Redaction Summary — Sample letter 1000 pages.pdf

## Document Info

- **Document**: `Sample letter 1000 pages.pdf` (1,387,848 bytes)
- **Pages**: 1,000
- **Content type**: Social care plan letters (repetitive templates across 18 unique page patterns)

## Redaction Requirements

Redact:
- ✅ Names (PERSON): John Doe, Jane Smith, Robert Brown + surname references ("Doe")
- ✅ Phone numbers (PHONE_NUMBER): 01234 567890, 01234 567891
- ✅ Email addresses (EMAIL_ADDRESS): jane.smith@springfieldcouncil.gov.uk, robert.brown@springfieldcouncil.gov.uk

## Process

### Step 1 — Initial Redaction (`/doc_redact`)

- **OCR method**: paddle
- **PII method**: Local (spaCy/Presidio)
- **Entities selected**: PERSON, PHONE_NUMBER, EMAIL_ADDRESS
- **Duration**: ~5.6 minutes
- **Artifacts saved to**: `output_redact/`

### Step 2 — Review & Pruning (Pass 1)

| Action | Count |
|--------|-------|
| Initial review rows | 4,060 |
| False positive PHONE_NUMBER rows removed (section numbers like "1640", "1681") | -60 |
| Final review rows after pruning | 4,000 |

**Breakdown by entity type after pruning:**
- PERSON: 2,000 boxes (John Doe ×500, Doe ×500, Jane Smith ×500, Robert Brown ×532 + some pages with additional name references)
- PHONE_NUMBER: 1,068 boxes (corrected from 1,128 — removed section number false positives)
- EMAIL_ADDRESS: 932 boxes

**Pre-apply coverage**: ✅ `pass_strict: true` — all must-redact terms covered by review boxes.

### Step 3 — Apply (`/review_apply`)

- **Duration**: ~22 seconds
- **Deliverable**: `*_redacted.pdf` (28.2 MB) with text layer stripped
- Also produced: `*_redactions_for_review.pdf` (review copy), updated review CSV

### Step 4 — Post-Apply Verification

| Check | Result |
|-------|--------|
| `coverage_pass` | ✅ True |
| `coverage_pass_strict` | ✅ True |
| `coverage_pass_with_cleanup` | ✅ True |
| Text layer leaks (names/phones/emails) | ✅ None — all PII terms removed from text layer across all 1,000 pages |
| Pixel failures (sampled) | ✅ 0 — no visual leak detected |
| Pages flagged for VLM (Pass 2) | ✅ None needed |

## Deliverable Files

All saved under `/home/user/app/workspace/15hci5k8dt3/redact/Sample letter 1000 pages.pdf/review/output_review_final/`:

| File | Size | Description |
|------|------|-------------|
| `8d49b70c..._redacted.pdf` | 28.2 MB | **Deliverable** — redacted PDF with text stripped via PyMuPDF annotations |
| `8d49b70c..._redactions_for_review.pdf` | 30.6 MB | Review copy (text layer retained for QA) — not the deliverable |
| `8d49b70c..._review_file.csv` | 440 KB | Final review CSV used for apply |

## Notes

- **Pass 2 (VLM)**: Not required — all policy checks passed with Pass 1 alone.
- **Over-redaction risk**: Minimal — only PERSON, PHONE_NUMBER, and EMAIL_ADDRESS entities were selected; no TITLES, STREETNAME, or UKPOSTCODE entities included.
- **False positives handled**: 60 section-number false positives (e.g., "1640", "1681" from numbered list items) correctly identified and removed before apply.
