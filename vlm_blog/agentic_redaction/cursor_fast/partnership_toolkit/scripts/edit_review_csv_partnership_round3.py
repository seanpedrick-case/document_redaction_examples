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
REVIEW_CSV_OUT = WORK_DIR / "partnership_review_file_round3.csv"


@dataclass(frozen=True)
class WordBox:
    page: int
    line: int
    norm: str
    x0: float
    y0: float
    x1: float
    y1: float


def clamp01(v: float) -> float:
    return 0.0 if v < 0.0 else 1.0 if v > 1.0 else v


def norm_word(s: str) -> str:
    s = (s or "").strip().lower()
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
            out.append(
                WordBox(
                    page=int(row["page"]),
                    line=int(row["line"]),
                    norm=norm_word(row["word_text"]),
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
    fieldnames = list(base_rows[0].keys())
    example_image = (base_rows[0].get(fieldnames[0]) or "").strip()

    # Remove Giuliani + prior Sister City/SisterCities custom rows + prior signature rows
    kept = []
    for r in base_rows:
        t = (r.get("text", "") or "").lower().strip()
        if "giuliani" in t:
            continue
        if (r.get("label") or "").upper() == "CUSTOM" and t in {"sister city", "sistercities", "signature"}:
            continue
        kept.append(r)

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
                    (r.get("text", "") or "").lower().strip(),
                )
            )
        except Exception:
            continue

    words = read_words(OCR_WORDS_CSV)
    by_page_line: dict[tuple[int, int], list[WordBox]] = {}
    for w in words:
        by_page_line.setdefault((w.page, w.line), []).append(w)
    for k in list(by_page_line.keys()):
        by_page_line[k] = sorted(by_page_line[k], key=lambda w: (w.x0, w.x1))

    # Add London
    for w in words:
        if w.norm == "london":
            box = padded_box(w.x0, w.y0, w.x1, w.y1, pad=0.003)
            key = (w.page, round(box[0], 5), round(box[1], 5), round(box[2], 5), round(box[3], 5), "london")
            if key not in existing:
                add_row(kept, fieldnames, infer_image_path(example_image, w.page), w.page, "CUSTOM", box, "London")
                existing.add(key)

    # Add Sister City (singular only)
    for (p, ln), ws in by_page_line.items():
        for i, a in enumerate(ws[:-1]):
            if a.norm != "sister":
                continue
            b = ws[i + 1]
            if b.norm == "city":
                box = union((a.x0, a.y0, a.x1, a.y1), (b.x0, b.y0, b.x1, b.y1), pad=0.003)
                key = (p, round(box[0], 5), round(box[1], 5), round(box[2], 5), round(box[3], 5), "sister city")
                if key not in existing:
                    add_row(kept, fieldnames, infer_image_path(example_image, p), p, "CUSTOM", box, "Sister City")
                    existing.add(key)

    # Signatures refined
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
        if key not in existing:
            add_row(kept, fieldnames, infer_image_path(example_image, page), page, "CUSTOM", box, "SIGNATURE")
            existing.add(key)

    def sort_key(r):
        return (
            int(float(r.get("page", "0") or 0)),
            float(r.get("ymin", "0") or 0),
            float(r.get("xmin", "0") or 0),
        )

    kept.sort(key=sort_key)

    with REVIEW_CSV_OUT.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(kept)

    print("Wrote:", REVIEW_CSV_OUT, "rows:", len(base_rows), "->", len(kept))


if __name__ == "__main__":
    main()

