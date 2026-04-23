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
OUT_DIR = Path("output/partnership_toolkit/initial").resolve()


def extract_file_like_paths(value):
    out = []
    if isinstance(value, str) and value.startswith("/"):
        out.append(value)
    elif isinstance(value, dict):
        for v in value.values():
            out.extend(extract_file_like_paths(v))
    elif isinstance(value, (list, tuple)):
        for v in value:
            out.extend(extract_file_like_paths(v))
    return out


def download_server_paths(server_paths, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    headers = {}
    if HF_TOKEN:
        headers["Authorization"] = f"Bearer {HF_TOKEN.strip()}"
    manifest = []
    timeout = httpx.Timeout(connect=120.0, read=1800.0, write=120.0, pool=120.0)
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


def run_doc_redact(ocr_method: str):
    httpx_kwargs = {
        "timeout": httpx.Timeout(connect=120.0, read=1800.0, write=120.0, pool=120.0),
    }
    client = (
        Client(BASE_URL, hf_token=HF_TOKEN, httpx_kwargs=httpx_kwargs)
        if HF_TOKEN
        else Client(BASE_URL, httpx_kwargs=httpx_kwargs)
    )
    paths, message = client.predict(
        api_name="/doc_redact",
        document_file=handle_file(str(PDF_PATH)),
        output_dir=None,
        ocr_method=ocr_method,
        pii_method="Local",
    )
    return extract_file_like_paths(paths), message


def run_redact_document(local_ocr_model: str):
    httpx_kwargs = {
        "timeout": httpx.Timeout(connect=120.0, read=3600.0, write=120.0, pool=120.0),
    }
    client = (
        Client(BASE_URL, hf_token=HF_TOKEN, httpx_kwargs=httpx_kwargs)
        if HF_TOKEN
        else Client(BASE_URL, httpx_kwargs=httpx_kwargs)
    )
    result = client.predict(
        api_name="/redact_document",
        file_paths=[handle_file(str(PDF_PATH))],
        combined_out_message="",
        ocr_review_files=[],
        chosen_local_ocr_model=local_ocr_model,
        pii_identification_method="Local",
        text_extraction_method="Local OCR model - PDFs without selectable text",
        chosen_llm_entities=["PERSON_NAME"],  # must be non-empty even in Local mode
        output_folder="/home/user/app/output/",
        input_folder="/home/user/app/input/",
        annotate_max_pages=9999,
        save_page_ocr_visualisations=True,
    )
    return extract_file_like_paths(result), result


def main():
    if not PDF_PATH.exists():
        raise FileNotFoundError(f"Missing PDF at {PDF_PATH}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    ocr_attempts = ["paddle", "tesseract"]
    last_err = None
    for ocr in ocr_attempts:
        try:
            server_paths, message = run_doc_redact(ocr)
            if not server_paths:
                raise RuntimeError(f"/doc_redact returned no artifacts ({message})")
            (OUT_DIR / "run_metadata.json").write_text(
                json.dumps(
                    {
                        "base_url": BASE_URL,
                        "pdf_path": str(PDF_PATH),
                        "ocr_method": ocr,
                        "pii_method": "Local",
                        "message": message,
                        "server_paths": server_paths,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            download_server_paths(server_paths, OUT_DIR)
            print(f"OK: {ocr=} {message}")
            print(f"Downloaded {len(server_paths)} artifacts to {OUT_DIR}")
            return
        except Exception as e:
            last_err = e
            print(f"Failed with ocr_method={ocr}: {e}")

    print("Falling back to /redact_document for stable artifacts.")
    for local_ocr in ocr_attempts:
        try:
            server_paths, raw_result = run_redact_document(local_ocr)
            (OUT_DIR / "run_metadata.json").write_text(
                json.dumps(
                    {
                        "base_url": BASE_URL,
                        "pdf_path": str(PDF_PATH),
                        "ocr_method": local_ocr,
                        "pii_method": "Local",
                        "endpoint": "/redact_document",
                        "server_paths": server_paths,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            (OUT_DIR / "raw_result_preview.json").write_text(
                json.dumps(raw_result[:5] if isinstance(raw_result, list) else str(type(raw_result)), indent=2),
                encoding="utf-8",
            )
            download_server_paths(server_paths, OUT_DIR)
            print(f"OK: endpoint=/redact_document ocr={local_ocr}")
            print(f"Downloaded {len(server_paths)} artifacts to {OUT_DIR}")
            return
        except Exception as e:
            last_err = e
            print(f"Failed fallback with local_ocr={local_ocr}: {e}")

    raise RuntimeError("All OCR methods failed (including fallback)") from last_err


if __name__ == "__main__":
    main()
