"""Step 1: Redact the Partnership Agreement PDF using paddle OCR + Local PII."""
import hashlib
import json
import os
import sys
from pathlib import Path
from urllib.parse import quote

import httpx

BASE_URL = "https://seanpedrickcase-document-redaction.hf.space"
PDF_PATH = Path(r"c:\Users\Sean\OneDrive - Lambeth Council\Apps\doc_redaction\Partnership-Agreement-Toolkit_0_0.pdf").resolve()
OUT_DIR = Path(r"c:\Users\Sean\OneDrive - Lambeth Council\Apps\doc_redaction\output").resolve()
OUT_DIR.mkdir(parents=True, exist_ok=True)

HF_TOKEN = os.environ.get("HF_TOKEN")

print(f"PDF path: {PDF_PATH}")
print(f"PDF exists: {PDF_PATH.exists()}")
print(f"Output dir: {OUT_DIR}")

# Try gradio_client first
try:
    import httpx as _httpx
    _httpx.Timeout(connect=120.0, read=1800.0, write=120.0, pool=120.0)
    from gradio_client import Client, handle_file

    httpx_kwargs = {
        "timeout": httpx.Timeout(connect=120.0, read=1800.0, write=120.0, pool=120.0),
    }

    print("Connecting to Gradio client...")
    if HF_TOKEN:
        client = Client(BASE_URL, hf_token=HF_TOKEN, httpx_kwargs=httpx_kwargs)
    else:
        client = Client(BASE_URL, httpx_kwargs=httpx_kwargs)

    print("Connected. Submitting redaction job with paddle OCR + Local PII...")
    result = client.predict(
        api_name="/doc_redact",
        document_file=handle_file(str(PDF_PATH)),
        ocr_method="paddle",
        pii_method="Local",
    )

    print("Job complete. Result type:", type(result))
    print("Result:", result)

    # Extract output paths
    output_paths = result[0] if isinstance(result, (list, tuple)) else []
    message = result[1] if isinstance(result, (list, tuple)) and len(result) > 1 else ""
    print(f"Message: {message}")
    print(f"Output paths ({len(output_paths)}): {output_paths}")

    if not output_paths:
        print("WARNING: No output paths returned. Trying /redact_document fallback...")
        result2 = client.predict(
            api_name="/redact_document",
            file_paths=[handle_file(str(PDF_PATH))],
            chosen_redact_entities=["PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "LOCATION", "DATE_TIME", "ORG"],
            chosen_redact_comprehend_entities=[],
            chosen_llm_entities=["PERSON"],
            ocr_review_files=[],
            combined_out_message="",
            output_folder="/tmp/gradio",
        )
        print("Fallback result:", result2)
        output_paths = []
        for item in result2:
            if isinstance(item, str) and item.lower().endswith((".pdf", ".csv", ".json")):
                output_paths.append(item)
            elif isinstance(item, list):
                output_paths.extend(
                    s for s in item
                    if isinstance(s, str) and s.lower().endswith((".pdf", ".csv", ".json"))
                )

    # Download all returned files
    headers = {}
    if HF_TOKEN:
        headers["Authorization"] = f"Bearer {HF_TOKEN.strip()}"

    manifest = []
    downloaded = []

    def extract_paths_recursive(obj):
        """Recursively extract file-like paths from nested result."""
        paths = []
        if isinstance(obj, str) and obj.startswith("/"):
            paths.append(obj)
        elif isinstance(obj, dict) and "path" in obj:
            paths.append(obj["path"])
        elif isinstance(obj, list):
            for item in obj:
                paths.extend(extract_paths_recursive(item))
        return paths

    all_paths = extract_paths_recursive(output_paths)
    print(f"Downloading {len(all_paths)} files...")

    with httpx.Client(timeout=httpx.Timeout(connect=120.0, read=600.0, write=120.0, pool=120.0), headers=headers) as http:
        for p in all_paths:
            if not isinstance(p, str) or not p.startswith("/"):
                continue
            url = f"{BASE_URL}/gradio_api/file={quote(p, safe='')}"
            dest = OUT_DIR / Path(p).name
            print(f"  Downloading {Path(p).name}...")
            resp = http.get(url)
            resp.raise_for_status()
            dest.write_bytes(resp.content)
            downloaded.append(str(dest))
            manifest.append({
                "server_path": p,
                "local_file": str(dest),
                "size": dest.stat().st_size,
                "sha256": hashlib.sha256(dest.read_bytes()).hexdigest(),
            })
            print(f"    Saved: {dest.name} ({dest.stat().st_size:,} bytes)")

    manifest_path = OUT_DIR / "redact_manifest.json"
    manifest_path.write_text(json.dumps({"files": manifest, "message": str(message)}, indent=2), encoding="utf-8")
    print(f"\nManifest written to: {manifest_path}")
    print(f"\nDownloaded {len(downloaded)} files to: {OUT_DIR}")
    for f in downloaded:
        print(f"  {Path(f).name}")

except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)
