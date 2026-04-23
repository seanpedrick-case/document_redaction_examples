import hashlib
import json
import os
from pathlib import Path
from urllib.parse import quote

import httpx
from gradio_client import Client, handle_file


BASE_URL = os.environ.get("DOC_REDACTION_BASE_URL", "https://seanpedrickcase-document-redaction.hf.space").rstrip(
    "/"
)
HF_TOKEN = os.environ.get("HF_TOKEN")

PDF_PATH = Path("input/Partnership-Agreement-Toolkit_0_0.pdf").resolve()
REVIEW_CSV = Path("output/partnership_toolkit/review_cycle/partnership_review_file_round2.csv").resolve()
OUT_DIR = Path("output/partnership_toolkit/after_apply_002").resolve()


def extract_paths(value):
    out = []
    if isinstance(value, str) and value.startswith("/"):
        out.append(value)
    elif isinstance(value, dict):
        for v in value.values():
            out.extend(extract_paths(v))
    elif isinstance(value, (list, tuple)):
        for v in value:
            out.extend(extract_paths(v))
    return out


def download(server_paths, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    headers = {}
    if HF_TOKEN:
        headers["Authorization"] = f"Bearer {HF_TOKEN.strip()}"
    timeout = httpx.Timeout(connect=120.0, read=1800.0, write=120.0, pool=120.0)
    manifest = []
    with httpx.Client(headers=headers, timeout=timeout) as http:
        for p in server_paths:
            url = f"{BASE_URL}/gradio_api/file={quote(p, safe='')}"
            r = http.get(url)
            r.raise_for_status()
            dest = out_dir / Path(p).name
            dest.write_bytes(r.content)
            manifest.append(
                {
                    "server_path": p,
                    "local_file": str(dest),
                    "size": dest.stat().st_size,
                    "sha256": hashlib.sha256(dest.read_bytes()).hexdigest(),
                }
            )
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    httpx_kwargs = {"timeout": httpx.Timeout(connect=120.0, read=1800.0, write=120.0, pool=120.0)}
    client = (
        Client(BASE_URL, hf_token=HF_TOKEN, httpx_kwargs=httpx_kwargs)
        if HF_TOKEN
        else Client(BASE_URL, httpx_kwargs=httpx_kwargs)
    )
    res = client.predict(handle_file(str(PDF_PATH)), handle_file(str(REVIEW_CSV)), None, api_name="/review_apply")
    server_paths = extract_paths(res)
    (OUT_DIR / "apply_metadata.json").write_text(
        json.dumps({"base_url": BASE_URL, "pdf": str(PDF_PATH), "review_csv": str(REVIEW_CSV), "server_paths": server_paths}, indent=2),
        encoding="utf-8",
    )
    download(server_paths, OUT_DIR)
    print("Downloaded", len(server_paths), "files to", OUT_DIR)


if __name__ == "__main__":
    main()

