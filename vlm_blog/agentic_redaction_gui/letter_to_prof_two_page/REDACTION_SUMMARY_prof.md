# Redaction Summary — example_of_emails_sent_to_a_professor_before_applying.pdf

## Document Info

- **Pages:** 2
- **Source:** `/home/user/app/workspace/j60wvqcbcji/example_of_emails_sent_to_a_professor_before_applying.pdf`
- **Backend:** `http://host.docker.internal:7861` (Local PII + Local selectable text extraction)

## User Redaction Requirements

| Requirement | Status |
|-------------|--------|
| Remove any redaction boxes related to Dr Kornbluth | ✅ Done — removed TITLES box for "Dr" before Kornbluth; name preserved in output |
| Redact references to Dr Hyde / Dr Hyde's lab | ✅ Done — all 6 occurrences of "Hyde"/"Hyde's"/"Hyde lab"/"Dr David R. Hyde" redacted across pages 1 and 2 (second email) |
| Redact references to Lauren / Lauren Lilley | ✅ Done — "--Lauren Lilley" redacted on pages 1 and 2 |
| Redact all mentions of Universities and their names | ✅ Done — "University of Notre Dame" redacted at all 4 occurrences on page 1 (second email also references same university) |

## Processing Steps

### Phase 1 — Initial Redaction (`/doc_redact`)
- OCR method: `Local model - selectable text`
- PII method: `Local`
- Entities: PERSON, EMAIL_ADDRESS, PHONE_NUMBER, STREETNAME, UKPOSTCODE, TITLES, CUSTOM
- Deny list: "Hyde's lab", "Hyde lab"
- Allow list: "Kornbluth"

### Phase 2 — Pass 1 Review (CSV edits)
- **Removed:** 1 box (TITLES "Dr" before Kornbluth at page 1, y=0.161)
- **Added:** 4 CUSTOM boxes for "University of Notre Dame" (not auto-detected by PII pipeline)
- Final review CSV: 27 rows

### Phase 3 — Apply (`/review_apply`)
- Original PDF + edited review CSV → PyMuPDF redaction applied
- Deliverable: `*_redacted.pdf` (text layer stripped)

### Phase 4 — Post-Apply Verification (`POST /agent/verify_redaction_coverage`)

| Metric | Result |
|--------|--------|
| `coverage_pass` | ✅ true |
| `coverage_pass_strict` | ✅ true |
| `coverage_pass_with_cleanup` | ✅ true |
| Pages with policy issues | 0 |
| Pages flagged for VLM (Pass 2) | None needed — Pass 2 not required; all coverage checks passed strictly; no text-layer leaks, pixel failures, or uncovered terms detected. Prune step removed 3 redundant standalone "Dr" TITLES boxes subsumed by larger compound boxes. |
| Suspicious rows pruned | 3 (redundant standalone "Dr" TITLES boxes) |

## Deliverable Files

All under: `/home/user/app/workspace/j60wvqcbcji/redact/example_of_emails_sent_to_a_professor_before_applying.pdf/review/output_review_final/`

| File | Purpose |
|------|---------|
| `*_redacted.pdf` (18,892 bytes) | **Deliverable** — final redacted PDF with text layer stripped |
| `*_redactions_for_review.pdf` (31,006 bytes) | Review copy with visual overlays (text retained — not for delivery) |
| `*_review_file.csv` (2,685 bytes) | Applied review CSV (pre-prune) |
| `pruned_review_file.csv` (2,446 bytes) | Pruned review CSV after suspicious-row cleanup |

## Coverage Report

Saved to: `/home/user/app/workspace/j60wvqcbcji/redact/example_of_emails_sent_to_a_professor_before_applying.pdf/review/coverage_report.json`
