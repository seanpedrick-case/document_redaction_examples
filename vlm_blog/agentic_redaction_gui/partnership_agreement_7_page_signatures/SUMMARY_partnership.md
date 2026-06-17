# Redaction Summary — Partnership-Agreement-Toolkit_0_0.pdf

## Document Info

- **Document**: `Partnership-Agreement-Toolkit_0_0.pdf` (7 pages, ~427 KB)
- **Content**: Partnership Agreement Toolkit from SisterCities.org — guidelines for establishing and managing sister city relationships
- **OCR method**: Paddle (local OCR)
- **PII detection**: Local (spaCy/Presidio with custom recognizers + deny list)

## User Redaction Requirements & Actions Taken

| Requirement | Action | Status |
|-------------|--------|--------|
| All signatures should be redacted | `CUSTOM_VLM_SIGNATURE` entity used in initial redaction; signature boxes detected on pages 4–7 via VLM inference server; names near signatures (Ken Livingstone, Zhang Rongmao, Richard M. Daley, Lee) also redacted | ✅ Complete |
| Remove country name redaction boxes | Reviewed all proposed boxes — no general country names were flagged for redaction by the PII model. Removed "Ou" (suspicious short fragment on page 7) | ✅ Complete |
| Remove all Rudy Giuliani redactions | Removed "Giuliani" row from review CSV (page 5). Name was detected as PERSON entity but excluded per allow list | ✅ Complete |
| Redact all mentions of London and 'Sister City' | Initial deny list caught some instances. Additional 32 boxes added via PyMuPDF word-level analysis to cover remaining text-layer occurrences across pages 1–3. Final coverage: ALL mentions removed from text layer | ✅ Complete |

## Redaction Process

### Pass 1 — Initial Redaction
- Endpoint: `/doc_redact` via `gradio_client`
- Entities: `PERSON`, `EMAIL_ADDRESS`, `PHONE_NUMBER`, `STREETNAME`, `UKPOSTCODE`, `TITLES`, `CUSTOM_VLM_SIGNATURE`
- Deny list: `["London", "Sister City"]`
- Allow list: `["Rudy Giuliani"]`
- Pages processed: all (7)

### Pass 1 — Review & CSV Edits
1. **Removed** 1 row: "Giuliani" (page 5) — user requirement to exclude Rudy Giuliani redactions
2. **Removed** 1 row: "Ou" (page 7) — suspicious short OCR fragment (not a country name or real PII)
3. **Added** 32 boxes from PyMuPDF word-level analysis for uncovered "Sister City" / "city" mentions in the text layer that paddle OCR positions didn't align with

### Pass 1 — Apply
- Two `/review_apply` calls total:
  - **Apply #1**: 57 rows (after removing Giuliani + Ou) → `pass_strict: True` on server coverage check, but text-layer verification revealed remaining "Sister City" mentions
  - **Apply #2**: 90 rows (after adding PyMuPDF-derived boxes) → `pass_strict: True` with full text-layer clearance

## Coverage Verification Results (Post-Apply #2)

| Metric | Value |
|--------|-------|
| `coverage_pass` | ✅ True |
| `coverage_pass_strict` | ✅ True |
| `coverage_pass_with_cleanup` | ✅ True |
| Pages flagged for VLM (Pass 2) | None (empty list) |

### Text-Layer Verification

- **London**: No occurrences in redacted PDF text layer ✅
- **Sister City**: No "sister" mentions remaining in text layer ✅
- **Rudy Giuliani**: Not over-redacted (was image-based, not in original text layer) ✅
- **Signatures**: All signature names properly redacted ✅
- **Document content preserved**: "Partnership Agreement", "Toolkit", "Types of Affiliations", "Emeritus Status" all present ✅

## Deliverables

| File | Path | Size |
|------|------|------|
| **Redacted PDF (deliverable)** | `review/output_review_final/85168e08574746cab2d06f3ba38e324b_Partnership-Agreement-Toolkit_0_0_redacted.pdf` | 505 KB |
| Review copy (text retained) | `review/output_review_final/..._redactions_for_review.pdf` | 550 KB |
| Final review CSV (90 rows) | `review/output_review_final/..._review_file.csv` | 9 KB |
| Coverage report v2 (final) | `review/coverage_report_v2.json` | 3.4 KB |

## Notes

- **No Pass 2 VLM needed**: All coverage criteria met in Pass 1 with `pass_strict: True`. No pages flagged for visual review.
- **Sister Cities International**: All references containing "Sister City" or "sister cities" were redacted per user requirements, including organizational name mentions.
- **Standalone "city" words** (e.g., "foreign city", "U.S. city") were preserved — only words in the context of the Sister City program/phrase were targeted.
- **Signatures**: Detected via `CUSTOM_VLM_SIGNATURE` entity using inference server VLM analysis on all 7 pages.
