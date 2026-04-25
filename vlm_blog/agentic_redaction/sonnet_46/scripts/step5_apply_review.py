"""Apply the edited review CSV via /review_apply to generate final redacted outputs."""
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import quote

import httpx
from gradio_client import Client, handle_file

BASE_URL = "https://seanpedrickcase-document-redaction.hf.space"
PDF_PATH = Path(r"c:\Users\Sean\OneDrive - Lambeth Council\Apps\doc_redaction\Partnership-Agreement-Toolkit_0_0.pdf").resolve()
EDITED_CSV = next(Path("output").glob("*_review_file_edited.csv")).resolve()
OUT_DIR = Path("output_final").resolve()
OUT_DIR.mkdir(parents=True, exist_ok=True)

HF_TOKEN = os.environ.get("HF_TOKEN")

print(f"PDF: {PDF_PATH}")
print(f"Edited CSV: {EDITED_CSV}")
print(f"Output dir: {OUT_DIR}")

httpx_kwargs = {
    "timeout": httpx.Timeout(connect=120.0, read=1800.0, write=120.0, pool=120.0),
}

print("Connecting to Gradio client...")
if HF_TOKEN:
    client = Client(BASE_URL, hf_token=HF_TOKEN, httpx_kwargs=httpx_kwargs)
else:
    client = Client(BASE_URL, httpx_kwargs=httpx_kwargs)

print("Connected. Applying edited review CSV...")
# Use positional args as recommended by the skill
result = client.predict(
    handle_file(str(PDF_PATH)),
    handle_file(str(EDITED_CSV)),
    None,
    api_name="/review_apply",
)

print("Apply result:", result)
output_paths = result[0] if isinstance(result, (list, tuple)) else []
message = result[1] if isinstance(result, (list, tuple)) and len(result) > 1 else ""
print(f"Message: {message}")
print(f"Output paths ({len(output_paths)}): {output_paths}")

# Download all returned files
headers = {}
if HF_TOKEN:
    headers["Authorization"] = f"Bearer {HF_TOKEN.strip()}"

manifest = []
downloaded = []

def extract_paths_recursive(obj):
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

manifest_path = OUT_DIR / "apply_manifest.json"
manifest_path.write_text(json.dumps({"files": manifest, "message": str(message)}, indent=2), encoding="utf-8")

print(f"\nManifest written to: {manifest_path}")
print(f"\nDownloaded {len(downloaded)} files to: {OUT_DIR}")
for f in downloaded:
    print(f"  {Path(f).name}")
