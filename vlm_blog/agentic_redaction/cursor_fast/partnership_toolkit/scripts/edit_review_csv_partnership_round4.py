import csv
import secrets
from dataclasses import dataclass
from pathlib import Path


REVIEW_CSV_IN = Path(
    "output/partnership_toolkit/after_apply_003/7063335af801487c9964185e51ac2065_Partnership-Agreement-Toolkit_0_0.pdf_review_file.csv"
).resolve()
OCR_WORDS_CSV = Path(
    "output/partnership_toolkit/initial/74bedff5a5284893b8e0adb4f024638b_Partnership-Agreement-Toolkit_0_0_ocr_results_with_words_local_ocr.csv"
).resolve()

WORK_DIR = Path("output/partnership_toolkit/review_cycle").resolve()
REVIEW_CSV_OUT = WORK_DIR / "partnership_review_file_round4.csv"


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


def norm_text(s: str) -> str:
    return (s or "").strip().lower()


def page_image_value(rows: list[dict], image_col: str, page_num: int) -> str:
    for r in rows:
        try:
            if int(float(r.get("page", "0") or 0)) == page_num and (r.get(image_col) or "").strip():
                return (r.get(image_col) or "").strip()
        except Exception:
            continue
    return f"placeholder_image_{max(page_num - 1, 0)}.png"


def add_custom_row(
    rows: list[dict],
    image_col: str,
    image_value: str,
    page_num: int,
    label: str,
    xmin: float,
    ymin: float,
    xmax: float,
    ymax: float,
    text: str,
):
    rows.append(
        {
            image_col: image_value,
            "page": str(page_num),
            "label": label,
            "color": "(0, 0, 0)",
            "xmin": f"{xmin:.6f}",
            "ymin": f"{ymin:.6f}",
            "xmax": f"{xmax:.6f}",
            "ymax": f"{ymax:.6f}",
            "text": text,
            "id": secrets.token_hex(6),
        }
    )


def norm_word(s: str) -> str:
    s = (s or "").strip().lower()
    return "".join(ch for ch in s if ch.isalpha())


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


def padded_box(x0, y0, x1, y1, pad=0.003):
    return (
        clamp01(x0 - pad),
        clamp01(y0 - pad),
        clamp01(x1 + pad),
        clamp01(y1 + pad),
    )


def union(a, b, pad=0.003):
    return padded_box(min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]), pad=pad)


def main():
    WORK_DIR.mkdir(parents=True, exist_ok=True)

    with REVIEW_CSV_IN.open("r", newline="", encoding="utf-8-sig") as f:
        base_rows = list(csv.DictReader(f))
    if not base_rows:
        raise SystemExit(f"No rows found in {REVIEW_CSV_IN}")

    fieldnames = list(base_rows[0].keys())
    image_col = fieldnames[0]

    # Remove Giuliani and previously-generated custom rows we will regenerate.
    regen_texts = {"sister city", "sister cities", "sistercities", "london"}
    kept: list[dict] = []
    for r in base_rows:
        t = norm_text(r.get("text", ""))
        if "giuliani" in t:
            continue
        if (r.get("label") or "").upper() == "CUSTOM" and t in regen_texts:
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
                    norm_text(r.get("text", "")),
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

    def is_city_like(norm: str) -> bool:
        return norm.startswith("city") or norm.startswith("cities")

    # Add London + Sister City/Cities + SisterCities brand word
    for w in words:
        if w.norm == "london":
            box = padded_box(w.x0, w.y0, w.x1, w.y1, pad=0.003)
            key = (w.page, round(box[0], 5), round(box[1], 5), round(box[2], 5), round(box[3], 5), "london")
            if key not in existing:
                add_custom_row(
                    kept, image_col, page_image_value(kept, image_col, w.page), w.page, "CUSTOM", *box, "London"
                )
                existing.add(key)
        if w.norm == "sistercities":
            box = padded_box(w.x0, w.y0, w.x1, w.y1, pad=0.003)
            key = (
                w.page,
                round(box[0], 5),
                round(box[1], 5),
                round(box[2], 5),
                round(box[3], 5),
                "sistercities",
            )
            if key not in existing:
                add_custom_row(
                    kept,
                    image_col,
                    page_image_value(kept, image_col, w.page),
                    w.page,
                    "CUSTOM",
                    *box,
                    "SisterCities",
                )
                existing.add(key)

    for (p, ln), ws in by_page_line.items():
        for i, a in enumerate(ws[:-1]):
            if a.norm != "sister":
                continue
            b = ws[i + 1]
            if not is_city_like(b.norm):
                continue
            phrase = "Sister Cities" if b.norm.startswith("cities") else "Sister City"
            box = union((a.x0, a.y0, a.x1, a.y1), (b.x0, b.y0, b.x1, b.y1), pad=0.003)
            key = (p, round(box[0], 5), round(box[1], 5), round(box[2], 5), round(box[3], 5), norm_text(phrase))
            if key not in existing:
                add_custom_row(kept, image_col, page_image_value(kept, image_col, p), p, "CUSTOM", *box, phrase)
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

