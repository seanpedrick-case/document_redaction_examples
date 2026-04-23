import csv
import secrets
from dataclasses import dataclass
from pathlib import Path


REVIEW_CSV_IN = Path(
    "output/partnership_toolkit/after_apply_001/95664c60feb64fe69932bb501abb4343_Partnership-Agreement-Toolkit_0_0.pdf_review_file.csv"
).resolve()
OCR_WORDS_CSV = Path(
    "output/partnership_toolkit/initial/74bedff5a5284893b8e0adb4f024638b_Partnership-Agreement-Toolkit_0_0_ocr_results_with_words_local_ocr.csv"
).resolve()

WORK_DIR = Path("output/partnership_toolkit/review_cycle").resolve()
REVIEW_CSV_OUT = WORK_DIR / "partnership_review_file_round2.csv"


@dataclass(frozen=True)
class WordBox:
    page: int
    line: int
    raw: str
    norm: str
    x0: float
    y0: float
    x1: float
    y1: float


def clamp01(v: float) -> float:
    return 0.0 if v < 0.0 else 1.0 if v > 1.0 else v


def norm_word(s: str) -> str:
    s = (s or "").strip().lower()
    # keep letters only for matching (handles punctuation like "City," or quotes)
    return "".join(ch for ch in s if ch.isalpha())


def padded_box(x0, y0, x1, y1, pad=0.003):
    return (
        clamp01(x0 - pad),
        clamp01(y0 - pad),
        clamp01(x1 + pad),
        clamp01(y1 + pad),
    )


def union(a, b, pad=0.003):
    return padded_box(min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]), pad=pad)


def read_words(path: Path) -> list[WordBox]:
    out: list[WordBox] = []
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        for row in r:
            raw = row["word_text"]
            out.append(
                WordBox(
                    page=int(row["page"]),
                    line=int(row["line"]),
                    raw=raw,
                    norm=norm_word(raw),
                    x0=float(row["word_x0"]),
                    y0=float(row["word_y0"]),
                    x1=float(row["word_x1"]),
                    y1=float(row["word_y1"]),
                )
            )
    return out


def infer_image_path(example_image: str, page: int) -> str:
    if not example_image:
        return f"placeholder_image_{max(page - 1, 0)}.png"
    if example_image.endswith(".png") and "_pdf_" in example_image:
        head, _tail = example_image.rsplit("_", 1)
        return f"{head}_{page - 1}.png"
    return example_image


def add_row(rows: list[dict], fieldnames: list[str], image_value: str, page: int, label: str, box, text: str):
    image_col = fieldnames[0]
    rows.append(
        {
            image_col: image_value,
            "page": str(page),
            "label": label,
            "color": "(0, 0, 0)",
            "xmin": f"{box[0]:.6f}",
            "ymin": f"{box[1]:.6f}",
            "xmax": f"{box[2]:.6f}",
            "ymax": f"{box[3]:.6f}",
            "text": text,
            "id": secrets.token_hex(6),
        }
    )


def main():
    WORK_DIR.mkdir(parents=True, exist_ok=True)

    with REVIEW_CSV_IN.open("r", newline="", encoding="utf-8-sig") as f:
        base_rows = list(csv.DictReader(f))
    if not base_rows:
        raise RuntimeError("No rows in review CSV")
    fieldnames = list(base_rows[0].keys())

    # Keep rows except those we will regenerate/adjust.
    def should_keep(r):
        t = (r.get("text", "") or "").lower()
        if "giuliani" in t:
            return False
        if (r.get("label") or "").upper() == "CUSTOM" and t in {"sister city", "sistercities", "signature"}:
            return False
        return True

    kept = [r for r in base_rows if should_keep(r)]
    example_image = (base_rows[0].get(fieldnames[0]) or "").strip()

    # Existing boxes to avoid duplicates
    existing = set()
    for r in kept:
        try:
            existing.add(
                (
                    int(float(r.get("page", "0") or 0)),
                    round(float(r["xmin"]), 5),
                    round(float(r["ymin"]), 5),
                    round(float(r["xmax"]), 5),
                    round(float(r["ymax"]), 5),
                    (r.get("text", "") or "").strip().lower(),
                )
            )
        except Exception:
            continue

    words = read_words(OCR_WORDS_CSV)
    by_page_line: dict[tuple[int, int], list[WordBox]] = {}
    for w in words:
        by_page_line.setdefault((w.page, w.line), []).append(w)
    # Ensure left-to-right within each line
    for k in list(by_page_line.keys()):
        by_page_line[k] = sorted(by_page_line[k], key=lambda w: (w.x0, w.x1))

    # SisterCities single word
    for w in words:
        if w.norm == "sistercities":
            box = padded_box(w.x0, w.y0, w.x1, w.y1)
            key = (w.page, round(box[0], 5), round(box[1], 5), round(box[2], 5), round(box[3], 5), "sistercities")
            if key not in existing:
                add_row(kept, fieldnames, infer_image_path(example_image, w.page), w.page, "CUSTOM", box, "SisterCities")
                existing.add(key)

    # Sister + City/Cities phrases
    for (p, ln), ws in by_page_line.items():
        for i, a in enumerate(ws):
            if a.norm != "sister":
                continue
            if i + 1 >= len(ws):
                continue
            b = ws[i + 1]
            if b.norm in {"city", "cities"}:
                box = union((a.x0, a.y0, a.x1, a.y1), (b.x0, b.y0, b.x1, b.y1))
                phrase = "Sister City" if b.norm == "city" else "Sister Cities"
                key = (p, round(box[0], 5), round(box[1], 5), round(box[2], 5), round(box[3], 5), phrase.lower())
                if key not in existing:
                    add_row(kept, fieldnames, infer_image_path(example_image, p), p, "CUSTOM", box, phrase)
                    existing.add(key)

    # Manual signature boxes refined to avoid covering printed names where possible.
    signature_boxes = [
        (4, (0.30, 0.755, 0.47, 0.80)),
        (4, (0.70, 0.755, 0.90, 0.80)),
        (5, (0.05, 0.755, 0.30, 0.84)),
        (5, (0.58, 0.755, 0.95, 0.84)),
        (6, (0.56, 0.70, 0.88, 0.77)),
        (6, (0.56, 0.77, 0.88, 0.84)),
        (7, (0.08, 0.77, 0.47, 0.86)),
        (7, (0.52, 0.77, 0.92, 0.86)),
    ]
    for page, box in signature_boxes:
        key = (page, round(box[0], 5), round(box[1], 5), round(box[2], 5), round(box[3], 5), "signature")
        if key in existing:
            continue
        add_row(kept, fieldnames, infer_image_path(example_image, page), page, "CUSTOM", box, "SIGNATURE")
        existing.add(key)

    # Sort
    def sort_key(r):
        try:
            return (
                int(float(r.get("page", "0") or 0)),
                float(r.get("ymin", "0") or 0),
                float(r.get("xmin", "0") or 0),
            )
        except Exception:
            return (9999, 1.0, 1.0)

    kept.sort(key=sort_key)

    with REVIEW_CSV_OUT.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(kept)

    print("Wrote:", REVIEW_CSV_OUT, "rows:", len(base_rows), "->", len(kept))


if __name__ == "__main__":
    main()

