import os
import sys
import hashlib
import json
from pathlib import Path
from urllib.parse import quote

import httpx
from gradio_client import Client, handle_file

# Configuration
BASE_URL = "https://seanpedrickcase-document-redaction.hf.space"
PDF_PATH = Path("Partnership-Agreement-Toolkit_0_0.pdf").resolve()
REVIEW_CSV = Path("modified_review_file.csv").resolve()
OUTPUT_DIR = Path("output_final").resolve()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print(f"Applying review modifications...")
print(f"PDF: {PDF_PATH.name}")
print(f"Review CSV: {REVIEW_CSV.name}")
print(f"Output dir: {OUTPUT_DIR}")

# Long timeout for cold start and long jobs
httpx_kwargs = {
    "timeout": httpx.Timeout(connect=120.0, read=1800.0, write=120.0, pool=120.0),
}

print(f"\nConnecting to {BASE_URL}...")
client = Client(BASE_URL, httpx_kwargs=httpx_kwargs)

# Call /review_apply with positional arguments (as per skill guidance)
print(f"\nUploading and applying review CSV...")
result = client.predict(
    handle_file(str(PDF_PATH)),
    handle_file(str(REVIEW_CSV)),
    None,  # output_dir - None to use server default
    api_name="/review_apply",
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
    manifest = []

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

                manifest.append({
                    "server_path": p,
                    "local_file": str(dest),
                    "size": dest.stat().st_size,
                    "sha256": hashlib.sha256(dest.read_bytes()).hexdigest(),
                })
            except Exception as e:
                print(f"    -> ERROR: {e}")

    # Save manifest
    manifest_path = OUTPUT_DIR / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nManifest saved to: {manifest_path}")
    print("\nDone!")
else:
    print("\nWARNING: No paths returned. The apply may have failed or returned empty results.")
    sys.exit(1)
