import os
import sys
from pathlib import Path
from urllib.parse import quote

import httpx
from gradio_client import Client, handle_file

# Configuration
BASE_URL = "https://seanpedrickcase-document-redaction.hf.space"
PDF_PATH = Path("Partnership-Agreement-Toolkit_0_0.pdf").resolve()
OUTPUT_DIR = Path("output").resolve()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Long timeout for cold start and long jobs
httpx_kwargs = {
    "timeout": httpx.Timeout(connect=120.0, read=1800.0, write=120.0, pool=120.0),
}

print(f"Connecting to {BASE_URL}...")
client = Client(BASE_URL, httpx_kwargs=httpx_kwargs)

# View API to see available endpoints
print("\nAvailable endpoints:")
print(client.view_api())

# Call /doc_redact with paddle OCR and Local PII
print(f"\nUploading and redacting {PDF_PATH.name}...")
print("Using: paddle OCR, Local PII identification")

result = client.predict(
    api_name="/doc_redact",
    document_file=handle_file(str(PDF_PATH)),
    ocr_method="paddle",
    pii_method="Local",
)

print(f"\nResult: {result}")

# Extract file paths from result
paths = result[0] if isinstance(result, (list, tuple)) else []
message = result[1] if isinstance(result, (list, tuple)) and len(result) > 1 else ""

print(f"\nMessage: {message}")
print(f"Paths returned: {paths}")

# Download files
if paths:
    print(f"\nDownloading {len(paths)} files to {OUTPUT_DIR}...")
    with httpx.Client(timeout=httpx_kwargs["timeout"]) as http:
        for p in paths:
            if not isinstance(p, str) or not p.startswith("/"):
                continue
            url = f"{BASE_URL}/gradio_api/file={quote(p, safe='')}"
            dest = OUTPUT_DIR / Path(p).name
            print(f"  Downloading {Path(p).name}...")
            try:
                r = http.get(url)
                r.raise_for_status()
                dest.write_bytes(r.content)
                print(f"    -> Saved to {dest} ({len(r.content)} bytes)")
            except Exception as e:
                print(f"    -> ERROR: {e}")
    print("\nDone!")
else:
    print("\nWARNING: No paths returned. The redaction may have failed or returned empty results.")
    sys.exit(1)
