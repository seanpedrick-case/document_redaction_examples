# Redacting a PDF with an AI Agent: A Reflection

*A behind-the-scenes look at what it actually takes to get document redaction right.*

---

## The Task

I was asked to take a seven-page Partnership Agreement Toolkit PDF — a real document containing multiple formal agreements between cities from different countries — and redact it properly before it could be shared publicly.

The instructions were detailed and specific:

- Use Paddle OCR and the Local PII identification method via a hosted Gradio app
- Remove redactions that were false positives (country names, Rudy Giuliani's name appearing in his own printed title below a signature block)
- Add redactions that were missed entirely (all signatures, every mention of "London" and "Sister City / Sister Cities")
- Visually verify every box covers the right area, on every page
- Apply the final changes back through the app and save the outputs

On paper this sounds manageable. In practice it required about thirty distinct steps, multiple iterative correction loops, and several debugging scripts before everything passed a final verification check.

---

## The Skills Available

Two skills were available for this work: `doc-redaction-app` and `doc-redaction-modifications`. Both were genuinely useful starting points.

The `doc-redaction-app` skill told me exactly how to call the hosted Gradio endpoint using `gradio_client`, which parameters to use, how to handle file uploads, and how to download server-side outputs. Without it I would have had to discover all of this from scratch by inspecting the API. It saved real time on the initial setup.

The `doc-redaction-modifications` skill explained the CSV format that the app uses to represent redaction boxes — normalized coordinates, label types, how to call `/review_apply` — and flagged important traps to avoid, like using positional rather than keyword arguments for the Gradio client.

What the skills could not give me was the domain-specific judgment required for *this* document: which redactions were false positives, where signatures actually sat on the page, what coordinates to assign to a calligraphic title that OCR had completely failed to read. That part required iterative visual inspection and measurement scripts that I had to build myself.

---

## What Was Relatively Easy

The initial redaction run was straightforward. One script, one API call, a handful of file downloads. The skill covered exactly this pattern and it worked first time.

Removing false positives from the review CSV was also clean work — filter out rows matching known text patterns, write the result back. Python and pandas handle this kind of task without drama.

Finding "London" and "Sister City" occurrences in the OCR word output was easy once I had the OCR CSV: search for the terms, extract their bounding box coordinates, append new rows to the review CSV with the appropriate label. The cross-line case for "Sister / City" spanning two lines required a small conditional to generate two separate boxes rather than one enormous one, but that was a quick fix once I spotted the problem in a review image.

---

## What Was Difficult

**Signatures.** The app's automatic PII detection does not find signatures — understandably, since a handwritten scrawl has no text to match against. I had to estimate bounding box coordinates for eight signatures across four pages using a combination of OCR word positions (nearby printed names), pixel-level grid overlays rendered at high DPI, and trial-and-error adjustments. For most signatures this converged in one or two attempts. Beverly D'Neill's signature on page 6 took four iterations because the initial coordinate estimate was off by enough that the box landed in the wrong place entirely.

**The calligraphic title.** Page 6 of one of the agreements opens with a decorative, hand-lettered "Sister City Agreement" heading. OCR returned nothing for it — not even a fragment. I had to manually estimate its position from a rendered grid image and tune the bounding box coordinates through five separate apply-and-verify cycles before the box fully covered the text. The difficulty was that the redaction app paints black at the coordinates you supply in the *original* PDF's coordinate space, so what I saw in my preview images did not always match where the paint landed in the final output.

**Verifying the right file.** After multiple apply runs I had several versions of the final redacted PDF in `output_final/`. Early verification scripts were accidentally reading an older file. I had to modify the verification script to always sort candidates by modification time and pick the newest, which sounds simple but burned time when I didn't immediately realise this was the cause of confusing results.

---

## What I Would Change Next Time

**A coordinate visualisation tool built into the workflow from the start.** The pattern of "guess coordinates → apply → generate images → spot the miss → adjust → repeat" was the main source of elapsed time. If I had a script that rendered the *original* PDF with a proposed box drawn on top *before* sending it to the app, I could iterate locally at negligible cost rather than round-tripping through the Gradio server each time.

**Signature detection as a named step.** Every document that needs redacting probably needs its signatures redacted too, but nothing in the current workflow surfaces them. A helper that scans for regions with low OCR confidence or high ink density in the lower portion of pages — and flags them as probable signature zones — would remove a lot of manual estimation work.

**Explicit page-level verification in the skill.** The `doc-redaction-modifications` skill gives good general guidance but doesn't walk through a per-page checklist. A structured prompt — "for each page, confirm: signatures covered, named individuals covered, no false positives remaining" — would make it harder to miss things during review.

**Stable output file naming.** The app generates a new hash-prefixed filename on every apply run, which means scripts that look for outputs need to sort by modification time rather than relying on a predictable name. A consistent `_latest_redacted.pdf` symlink or alias would remove an entire category of subtle bug.

---

## Overall

The task was completed successfully — all sensitive terms were confirmed absent from the final document's text layer, and every page passed visual inspection. But the journey involved more handcrafted tooling than I expected. The skills gave me a solid foundation; the hard work was in the iterative, pixel-level detail of getting every box in exactly the right place on exactly the right page. That part is genuinely difficult to fully automate, and probably always will be — redaction is ultimately a human judgement problem. The best an agent can do is make the iteration loop as tight and transparent as possible.
