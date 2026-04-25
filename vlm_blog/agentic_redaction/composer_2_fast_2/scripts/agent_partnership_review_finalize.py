"""
Build edited *_review_file.csv from OCR + rules, then /review_apply and download to output_final/.
"""
from __future__ import annotations

import csv
import json
import os
import re
import secrets
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote

import httpx
from gradio_client import Client, handle_file

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
FINAL = ROOT / "output_final"
FINAL.mkdir(parents=True, exist_ok=True)

BASE_URL = os.environ.get(
    "DOC_REDACTION_BASE_URL", "https://seanpedrickcase-document-redaction.hf.space"
).rstrip("/")
HF_TOKEN = os.environ.get("HF_TOKEN")

PREFIX = "28d81c34644447cbbc348989f7e266ca_Partnership-Agreement-Toolkit_0_0"
OCR_CSV = OUT / f"{PREFIX}_ocr_results_with_words_local_ocr.csv"
REVIEW_IN = OUT / f"{PREFIX}_review_file.csv"
PDF_IN = OUT / "Partnership-Agreement-Toolkit_0_0.pdf"
REVIEW_OUT = OUT / f"{PREFIX}_review_file_edited.csv"

DROP_IDS = {
    "RinA7wZmWN2H",
    "pkxKnFAwdMT3",
    "6u94pIzND74P",
    "bNj4hH3YIgMl",
    "Q2iZYusuZGEp",
    "ufGMU8iqpJKe",
}
DROP_PAGE4_IDS = {"XnXTYFCFJebX", "znGBWn1zHSR1", "VFsTFW8UNKsD"}
GIULIANI_ROW_IDS = {"UqXWbbuWBCu2", "NYCKqegoXz25"}
PHONE_REPLACE_IDS = {"UbOgCPa1TGUr", "J7SuWqGLPqzG"}


def norm_token(w: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (w or "").lower())


def pad_box(x0: float, y0: float, x1: float, y1: float, p: float = 0.004) -> tuple[float, float, float, float]:
    return (
        max(0.0, x0 - p),
        max(0.0, y0 - p),
        min(1.0, x1 + p),
        min(1.0, y1 + p),
    )


def load_ocr_by_page_line(path: Path) -> dict[tuple[int, int], list[dict]]:
    by_pl: dict[tuple[int, int], list[dict]] = defaultdict(list)
    with path.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            pg = int(row["page"])
            ln = int(row["line"])
            by_pl[(pg, ln)].append(row)
    for k in by_pl:
        by_pl[k].sort(key=lambda r: float(r["word_x0"]))
    return by_pl


def _sister_follows_city_phrase(n2: str) -> bool:
    if n2 in ("city", "cety", "cities"):
        return True
    # e.g. city/county/state -> citycountystate; city/sister -> citysister
    if n2.startswith("city") and len(n2) <= 24:
        return True
    return False


def iter_sister_city_boxes(by_pl) -> list[tuple[int, str, tuple[float, float, float, float]]]:
    """Return (page, text, bbox) for Sister+City bigrams and SisterCities token."""
    out: list[tuple[int, str, tuple[float, float, float, float]]] = []
    for (page, _ln), words in by_pl.items():
        for i, w in enumerate(words):
            t = w["word_text"]
            nt = norm_token(t)
            x0, y0 = float(w["word_x0"]), float(w["word_y0"])
            x1, y1 = float(w["word_x1"]), float(w["word_y1"])
            if nt == "sistercities":
                out.append((page, "SisterCities", pad_box(x0, y0, x1, y1)))
                continue
            if nt != "sister" or i + 1 >= len(words):
                continue
            n2 = norm_token(words[i + 1]["word_text"])
            if _sister_follows_city_phrase(n2):
                w2 = words[i + 1]
                bx0 = min(x0, float(w2["word_x0"]))
                by0 = min(y0, float(w2["word_y0"]))
                bx1 = max(x1, float(w2["word_x1"]))
                by1 = max(y1, float(w2["word_y1"]))
                out.append((page, "Sister City", pad_box(bx0, by0, bx1, by1)))
    return out


def iter_london_boxes(ocr_path: Path) -> list[tuple[int, str, tuple[float, float, float, float]]]:
    out: list[tuple[int, str, tuple[float, float, float, float]]] = []
    with ocr_path.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            t = row["word_text"]
            tl = t.lower()
            if "london" in tl or tl == "city-london":
                x0, y0 = float(row["word_x0"]), float(row["word_y0"])
                x1, y1 = float(row["word_x1"]), float(row["word_y1"])
                out.append((int(row["page"]), t, pad_box(x0, y0, x1, y1)))
    return out


def new_row(
    image: str,
    page: int,
    label: str,
    bbox: tuple[float, float, float, float],
    text: str,
) -> dict[str, str]:
    x0, y0, x1, y1 = bbox
    return {
        "image": image,
        "page": str(page),
        "label": label,
        "color": "(0, 0, 0)",
        "xmin": f"{x0:.6f}",
        "ymin": f"{y0:.6f}",
        "xmax": f"{x1:.6f}",
        "ymax": f"{y1:.6f}",
        "id": secrets.token_hex(6),
        "text": text,
    }


def pick_image_for_page(rows: list[dict], page: int) -> str:
    for r in rows:
        if int(float(r.get("page", 0))) == page and r.get("image"):
            return r["image"]
    for r in rows:
        if r.get("image"):
            return r["image"]
    return ""


def build_edited_csv() -> None:
    with REVIEW_IN.open(newline="", encoding="utf-8-sig") as f:
        orig = list(csv.DictReader(f))
    fieldnames = list(orig[0].keys())

    kept: list[dict] = []
    for r in orig:
        rid = r.get("id", "")
        txt = (r.get("text") or "").lower()
        if rid in DROP_IDS or rid in DROP_PAGE4_IDS:
            continue
        if rid in GIULIANI_ROW_IDS:
            continue
        if "giuliani" in txt:
            continue
        if rid in PHONE_REPLACE_IDS:
            continue
        if rid == "0gcmcpxO33Qx":
            continue
        kept.append(r)

    by_pl = load_ocr_by_page_line(OCR_CSV)
    img_template = pick_image_for_page(orig, 1)

    extras: list[dict] = []

    # Page 4: two name lines + signature
    extras.append(
        new_row(
            pick_image_for_page(orig, 4),
            4,
            "PERSON",
            pad_box(0.246275, 0.807576, 0.612157, 0.817576),
            "Sheikh Mohammed bin Butti Al Hamed",
        )
    )
    extras.append(
        new_row(
            pick_image_for_page(orig, 4),
            4,
            "PERSON",
            pad_box(0.730588, 0.80697, 0.848235, 0.816667),
            "Lee P. Brown",
        )
    )
    extras.append(
        new_row(
            pick_image_for_page(orig, 4),
            4,
            "HANDWRITING",
            pad_box(0.32, 0.765, 0.44, 0.805),
            "signature",
        )
    )

    # Page 5: Ken Livingston (exclude Giuliani); signature column
    extras.append(
        new_row(
            pick_image_for_page(orig, 5),
            5,
            "PERSON",
            pad_box(0.67, 0.8765, 0.798, 0.892),
            "Ken Livingston",
        )
    )
    # Cover ink above printed mayoral lines (~0.878+); keep typed names/titles visible.
    extras.append(
        new_row(
            pick_image_for_page(orig, 5),
            5,
            "HANDWRITING",
            pad_box(0.155, 0.752, 0.395, 0.864),
            "signature",
        )
    )
    extras.append(
        new_row(
            pick_image_for_page(orig, 5),
            5,
            "HANDWRITING",
            pad_box(0.515, 0.748, 0.835, 0.864),
            "signature",
        )
    )

    # Page 6: signature band (OCR noise line)
    extras.append(
        new_row(
            pick_image_for_page(orig, 6),
            6,
            "HANDWRITING",
            pad_box(0.42, 0.625, 0.73, 0.668),
            "signature",
        )
    )

    # Page 7: two signature zones above printed names
    extras.append(
        new_row(
            pick_image_for_page(orig, 7),
            7,
            "HANDWRITING",
            pad_box(0.14, 0.708, 0.5, 0.828),
            "signature",
        )
    )
    extras.append(
        new_row(
            pick_image_for_page(orig, 7),
            7,
            "HANDWRITING",
            pad_box(0.5, 0.708, 0.9, 0.828),
            "signature",
        )
    )

    # Phone (202) + 347-8630 — two tight boxes
    extras.append(
        new_row(
            pick_image_for_page(orig, 3),
            3,
            "PHONE_NUMBER",
            pad_box(0.805, 0.7825, 0.854, 0.797),
            "(202)",
        )
    )
    extras.append(
        new_row(
            pick_image_for_page(orig, 3),
            3,
            "PHONE_NUMBER",
            pad_box(0.115, 0.7985, 0.195, 0.812),
            "347-8630",
        )
    )

    for page, phrase, bbox in iter_sister_city_boxes(by_pl):
        extras.append(new_row(pick_image_for_page(orig, page), page, "CUSTOM", bbox, phrase))

    for page, wtxt, bbox in iter_london_boxes(OCR_CSV):
        extras.append(new_row(pick_image_for_page(orig, page), page, "ADDRESS", bbox, wtxt))

    merged = kept + extras
    with REVIEW_OUT.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(merged)
    print("Wrote", REVIEW_OUT, "rows", len(merged))


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
        for v in obj.values():
            extract_paths(v, out)
    elif isinstance(obj, (list, tuple)):
        for x in obj:
            extract_paths(x, out)


def apply_and_download() -> None:
    httpx_kwargs = {
        "timeout": httpx.Timeout(connect=120.0, read=1800.0, write=120.0, pool=120.0),
    }
    client = (
        Client(BASE_URL, hf_token=HF_TOKEN, httpx_kwargs=httpx_kwargs)
        if HF_TOKEN
        else Client(BASE_URL, httpx_kwargs=httpx_kwargs)
    )
    result = client.predict(
        handle_file(str(PDF_IN)),
        handle_file(str(REVIEW_OUT)),
        None,
        api_name="/review_apply",
    )
    paths: list[str] = []
    extract_paths(result, paths)
    msg = str(result[-1]) if result else ""
    print("review_apply message:", msg)
    print("paths:", len(paths))

    headers = {}
    if HF_TOKEN:
        headers["Authorization"] = f"Bearer {HF_TOKEN.strip()}"

    manifest = []
    with httpx.Client(timeout=httpx_kwargs["timeout"], headers=headers) as http:
        for p in paths:
            url = f"{BASE_URL}/gradio_api/file={quote(p, safe='')}"
            dest = FINAL / Path(p).name
            r = http.get(url)
            r.raise_for_status()
            dest.write_bytes(r.content)
            manifest.append({"server_path": p, "local": str(dest), "size": dest.stat().st_size})
            print("saved", dest.name)

    (FINAL / "apply_manifest.json").write_text(
        json.dumps({"message": msg, "artifacts": manifest}, indent=2), encoding="utf-8"
    )


def main() -> None:
    build_edited_csv()
    apply_and_download()


if __name__ == "__main__":
    main()
