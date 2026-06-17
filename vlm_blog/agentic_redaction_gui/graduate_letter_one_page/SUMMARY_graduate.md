# Redaction Summary — graduate-job-example-cover-letter.pdf

## Document Overview

- **Document:** `graduate-job-example-cover-letter.pdf` (1 page)
- **Type:** Cover letter applying for Community Health Development Officer role
- **Processing date:** 2026-06-17

## Redaction Policy Applied

| Requirement | Action |
|---|---|
| Redact any names and titles, apart from Mr Wilson | Removed redaction boxes for "Mr Mark Wilson" (address block) and "Mr" in "Dear Mr Wilson" (salutation). All other person names redacted. |
| Redact any organisation names | `UK Health Trust` (4 instances), `Health UK`, `Newcastle University`, `NU Sociology Society` — all redacted via CUSTOM deny-list matching. |
| Redact any place names | Addresses, cities, countries all redacted: Westmoreland Drive, Newcastle upon Tyne (+ "upon"), London (address + body), Ghana. Postcodes NE1 8LT and SW1 9LT also redacted. |

## Pass 1 Workflow

### Phase 1 — Initial Redaction
- **Endpoint:** `POST /doc_redact`
- **OCR method:** Local model - selectable text
- **PII method:** Local (spaCy/Presidio)
- **Entities:** PERSON, TITLES, LOCATION, STREETNAME, UKPOSTCODE, CUSTOM
- **Deny list:** UK Health Trust, Health UK, Newcastle University, NU Sociology Society
- **Allow list:** Mr Wilson

### Phase 2 — Pass 1 Review (CSV edits)

**Removed rows (6):**
- "Mr" × 2 — part of Mr Wilson references (keep visible)
- "Mr Mark Wilson" — keep full name visible per user requirement  
- "Mark Wilson" — keep visible per user requirement
- "UK" — redundant subset of larger UK Health Trust box
- "UK UK Health Trust" — duplicate box

**Added rows (2):**
- "upon" (LOCATION) — filled gap between Newcastle and Tyne in "Newcastle upon Tyne"
- "London" (LOCATION) — place name in recipient address block not initially detected

### Phase 3 — Apply
- **Endpoint:** `POST /review_apply` 
- **Input:** Original PDF + edited review CSV (19 rows)
- **Output:** Post-apply `_redacted.pdf` with text layer stripped via PyMuPDF redaction

## Coverage Verification Results (Post-Apply)

| Metric | Result |
|---|---|
| `pass_strict` | **true** ✓ |
| `pass_with_cleanup` | **true** ✓  |
| Uncovered terms | 0 (all must-redact terms covered) |
| Over-redactions | 0 (Mr Wilson correctly preserved) |
| Text layer leaks | 0 (no PII remaining in text layer) |
| Pixel failures | 0 (all visual redactions confirmed) |
| Suspicious rows pruned | 0 (all rows contain valid PII targets) |

## Term Verification

| Term | Status in Redacted PDF | Expected |
|---|---|---|
| Rachel Sullivan (sender name) | ✓ Removed | Must be redacted |
| UK Health Trust (org ×4) | ✓ Removed | Must be redacted |
| Health UK (org) | ✓ Removed  | Must be redacted 	|
| Newcastle University (org) 	| ✓ Removed 	| Must be redacted 	|
| NU Sociology Society (org)  	| ✓ Removed  	| Must be redacted  	|
| Westmoreland Drive (address) | ✓ Removed | Must be redacted |
| Newcastle upon Tyne (place)  | ✓ Removed  | Must be redacted 	|
| London (place, both instances) | ✓ Removed 	| Must be redacted  	|
| Ghana (place)               	| ✓ Removed               | Must be redacted     |
| Postcodes (NE1 8LT, SW1 9LT) | ✓ Removed               | Must be redacted     |
| Whitehall Square (address)  	| ✓ Removed               | Must be redacted     |
| Mr Wilson                   	| ✓ Visible             	| Must NOT be redacted 	|

## Deliverable Files

Located in `/home/user/app/workspace/hk8eu8kx3x6/redact/graduate-job-example-cover-letter.pdf/review/output_review_final/`:

- **`*_redacted.pdf`** — Final deliverable (text layer stripped, all PII redacted)
- **`*_redactions_for_review.pdf`** — Review copy with overlay boxes (text retained for QA only)  
- **`*_review_file.csv`** — Applied review CSV with 19 redaction boxes
- **`*_review_file_pruned.csv`** — Pruned version (no suspicious rows removed in this case)

## Pass 2 Assessment

Pass 2 (VLM visual review) is **not required**. Coverage report shows `pass_strict: true` with zero issues across all categories. No pages flagged for VLM review.
