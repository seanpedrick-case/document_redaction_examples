"""One-off: download PDF, call /doc_redact, save artifacts to output/."""
from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import quote

import httpx
from gradio_client import Client, handle_file

BASE_URL = os.environ.get(
    "DOC_REDACTION_BASE_URL", "https://seanpedrickcase-document-redaction.hf.space"
).rstrip("/")
HF_TOKEN = os.environ.get("HF_TOKEN")
# raw.githubusercontent.com serves Git LFS pointer for this file; use GitHub /raw/ URL.
PDF_URL = (
    "https://github.com/seanpedrick-case/doc_redaction/raw/main/"
    "example_data/Partnership-Agreement-Toolkit_0_0.pdf"
)
WORK = Path(__file__).resolve().parents[1] / "output"
WORK.mkdir(parents=True, exist_ok=True)
PDF_LOCAL = WORK / "Partnership-Agreement-Toolkit_0_0.pdf"


def download_pdf() -> None:
    if PDF_LOCAL.exists() and PDF_LOCAL.read_bytes()[:4] == b"%PDF" and PDF_LOCAL.stat().st_size > 10000:
        print("PDF already present:", PDF_LOCAL)
        return
    headers = {}
    if HF_TOKEN:
        headers["Authorization"] = f"Bearer {HF_TOKEN.strip()}"
    with httpx.Client(timeout=120.0, follow_redirects=True, headers=headers) as http:
        r = http.get(PDF_URL)
        r.raise_for_status()
        PDF_LOCAL.write_bytes(r.content)
    print("Downloaded:", PDF_LOCAL, "bytes", PDF_LOCAL.stat().st_size)


def extract_paths(obj, out: list) -> None:
    if obj is None:
        return
    if isinstance(obj, str):
        low = obj.lower()
        if obj.startswith("/") and low.endswith((".pdf", ".csv", ".json", ".png", ".zip")):
            if obj not in out:
                out.append(obj)
        return
    if isinstance(obj, dict):
        p = obj.get("path")
        if isinstance(p, str):
            extract_paths(p, out)
        for v in obj.values():
            extract_paths(v, out)
    elif isinstance(obj, (list, tuple)):
        for x in obj:
            extract_paths(x, out)


def main() -> None:
    download_pdf()
    httpx_kwargs = {
        "timeout": httpx.Timeout(connect=120.0, read=1800.0, write=120.0, pool=120.0),
    }
    client = (
        Client(BASE_URL, hf_token=HF_TOKEN, httpx_kwargs=httpx_kwargs)
        if HF_TOKEN
        else Client(BASE_URL, httpx_kwargs=httpx_kwargs)
    )

    ocr_try = ["paddle", "tesseract"]
    last_msg = ""
    paths: list[str] = []
    for ocr in ocr_try:
        print("Calling /doc_redact with ocr_method=", repr(ocr))
        result = client.predict(
            api_name="/doc_redact",
            document_file=handle_file(str(PDF_LOCAL)),
            redact_entities=None,
            output_dir=None,
            ocr_method=ocr,
            pii_method="Local",
            allow_list=None,
            deny_list=None,
            page_min=None,
            page_max=None,
            llm_instruction="",
        )
        raw_paths = result[0] if result else []
        paths = []
        extract_paths(result, paths)
        last_msg = str(result[1]) if len(result) > 1 else ""
        print("message:", last_msg)
        print("paths count:", len(paths))
        if not paths:
            print("raw result repr:", repr(result)[:2000])
        if paths:
            break
        print("Empty paths, retrying with next OCR if any...")

    headers = {}
    if HF_TOKEN:
        headers["Authorization"] = f"Bearer {HF_TOKEN.strip()}"

    manifest = []
    with httpx.Client(timeout=httpx_kwargs["timeout"], headers=headers) as http:
        for p in paths:
            url = f"{BASE_URL}/gradio_api/file={quote(p, safe='')}"
            dest = WORK / Path(p).name
            r = http.get(url)
            r.raise_for_status()
            dest.write_bytes(r.content)
            manifest.append({"server_path": p, "local": str(dest), "size": dest.stat().st_size})
            print("saved", dest.name)

    (WORK / "redact_manifest.json").write_text(
        json.dumps({"message": last_msg, "artifacts": manifest}, indent=2), encoding="utf-8"
    )
    if not paths:
        raise SystemExit("No artifacts returned from /doc_redact")


if __name__ == "__main__":
    main()
