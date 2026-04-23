import csv
import secrets
from dataclasses import dataclass
from pathlib import Path


REVIEW_CSV_IN = Path(
    "output/partnership_toolkit/initial/74bedff5a5284893b8e0adb4f024638b_Partnership-Agreement-Toolkit_0_0_review_file.csv"
).resolve()
OCR_WORDS_CSV = Path(
    "output/partnership_toolkit/initial/74bedff5a5284893b8e0adb4f024638b_Partnership-Agreement-Toolkit_0_0_ocr_results_with_words_local_ocr.csv"
).resolve()

WORK_DIR = Path("output/partnership_toolkit/review_cycle").resolve()
REVIEW_CSV_OUT = WORK_DIR / REVIEW_CSV_IN.name.replace("_review_file.csv", "_review_file_edited.csv")


@dataclass(frozen=True)
class WordBox:
    page: int
    line: int
    text: str
    x0: float
    y0: float
    x1: float
    y1: float


def clamp01(v: float) -> float:
    return 0.0 if v < 0.0 else 1.0 if v > 1.0 else v


def padded_union(a, b, pad=0.002):
    x0 = clamp01(min(a[0], b[0]) - pad)
    y0 = clamp01(min(a[1], b[1]) - pad)
    x1 = clamp01(max(a[2], b[2]) + pad)
    y1 = clamp01(max(a[3], b[3]) + pad)
    return x0, y0, x1, y1


def read_words(path: Path) -> list[WordBox]:
    out: list[WordBox] = []
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        for row in r:
            out.append(
                WordBox(
                    page=int(row["page"]),
                    line=int(row["line"]),
                    text=row["word_text"],
                    x0=float(row["word_x0"]),
                    y0=float(row["word_y0"]),
                    x1=float(row["word_x1"]),
                    y1=float(row["word_y1"]),
                )
            )
    return out


def infer_image_path(existing_any_image: str, page: int) -> str:
    # Existing pattern: "...pdf_2.png" where suffix is (page-1)
    # Keep same directory + basename prefix, swap the page index.
    if not existing_any_image:
        return f"placeholder_image_{max(page - 1, 0)}.png"
    if existing_any_image.endswith(".png") and "_pdf_" in existing_any_image:
        head, tail = existing_any_image.rsplit("_", 1)
        # tail is like "2.png"
        return f"{head}_{page - 1}.png"
    return existing_any_image


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
            "id": secrets.token_hex(6),
            "text": text,
        }
    )


def main():
    WORK_DIR.mkdir(parents=True, exist_ok=True)

    with REVIEW_CSV_IN.open("r", newline="", encoding="utf-8-sig") as f:
        orig_rows = list(csv.DictReader(f))
    if not orig_rows:
        raise RuntimeError("No rows in review CSV")
    fieldnames = list(orig_rows[0].keys())

    # Remove: Rudy Giuliani mentions (explicit requirement)
    filtered = [r for r in orig_rows if "giuliani" not in (r.get("text", "") or "").lower()]

    # Remove: "general country names" redactions (heuristic)
    country_terms = {
        "usa",
        "u.s.a",
        "u.a.e",
        "ecuador",
        "texas",
        "chicago",
        "shenyang",
        "houston",
        "abu dhabi",
        "california",
    }
    filtered2 = []
    for r in filtered:
        t = (r.get("text", "") or "").strip().lower()
        if t in country_terms:
            continue
        filtered2.append(r)

    existing_any_image = (filtered2[0].get(fieldnames[0]) or "").strip()

    # Build existing boxes set to avoid duplicates
    existing_boxes = set()
    for r in filtered2:
        try:
            existing_boxes.add(
                (
                    int(float(r.get("page", "0") or 0)),
                    round(float(r["xmin"]), 5),
                    round(float(r["ymin"]), 5),
                    round(float(r["xmax"]), 5),
                    round(float(r["ymax"]), 5),
                )
            )
        except Exception:
            continue

    words = read_words(OCR_WORDS_CSV)
    # Index by page+line preserving order
    by_page_line: dict[tuple[int, int], list[WordBox]] = {}
    for w in words:
        by_page_line.setdefault((w.page, w.line), []).append(w)

    # Add redactions for "London"
    for w in words:
        if w.text.strip().lower() == "london":
            box = padded_union((w.x0, w.y0, w.x1, w.y1), (w.x0, w.y0, w.x1, w.y1), pad=0.003)
            key = (w.page, round(box[0], 5), round(box[1], 5), round(box[2], 5), round(box[3], 5))
            if key in existing_boxes:
                continue
            add_row(filtered2, fieldnames, infer_image_path(existing_any_image, w.page), w.page, "CUSTOM", box, "London")
            existing_boxes.add(key)

    # Add redactions for "Sister City" phrase + SisterCities logo word
    for (p, ln), ws in by_page_line.items():
        for i in range(len(ws)):
            a = ws[i]
            if a.text.strip().lower() == "sistercities":
                box = padded_union((a.x0, a.y0, a.x1, a.y1), (a.x0, a.y0, a.x1, a.y1), pad=0.003)
                key = (p, round(box[0], 5), round(box[1], 5), round(box[2], 5), round(box[3], 5))
                if key not in existing_boxes:
                    add_row(filtered2, fieldnames, infer_image_path(existing_any_image, p), p, "CUSTOM", box, "SisterCities")
                    existing_boxes.add(key)
            # phrase "Sister" + "City"
            if i + 1 < len(ws) and a.text.strip().lower() == "sister":
                b = ws[i + 1]
                if b.text.strip().lower() == "city":
                    box = padded_union((a.x0, a.y0, a.x1, a.y1), (b.x0, b.y0, b.x1, b.y1), pad=0.003)
                    key = (p, round(box[0], 5), round(box[1], 5), round(box[2], 5), round(box[3], 5))
                    if key in existing_boxes:
                        continue
                    add_row(filtered2, fieldnames, infer_image_path(existing_any_image, p), p, "CUSTOM", box, "Sister City")
                    existing_boxes.add(key)

    # Add signature boxes (manual, from visual inspection of the page exports)
    signature_boxes = [
        # page 4: two signatures bottom area
        (4, (0.29, 0.745, 0.48, 0.81), "SIGNATURE"),
        (4, (0.69, 0.745, 0.90, 0.81), "SIGNATURE"),
        # page 5: two large signatures across bottom
        (5, (0.08, 0.735, 0.42, 0.88), "SIGNATURE"),
        (5, (0.55, 0.735, 0.96, 0.88), "SIGNATURE"),
        # page 6: signatures around name lines
        (6, (0.52, 0.78, 0.86, 0.89), "SIGNATURE"),
        (6, (0.52, 0.69, 0.86, 0.78), "SIGNATURE"),
        # page 7: two signatures bottom
        (7, (0.12, 0.80, 0.46, 0.92), "SIGNATURE"),
        (7, (0.55, 0.80, 0.92, 0.92), "SIGNATURE"),
    ]
    for page, box, label_text in signature_boxes:
        key = (page, round(box[0], 5), round(box[1], 5), round(box[2], 5), round(box[3], 5))
        if key in existing_boxes:
            continue
        add_row(filtered2, fieldnames, infer_image_path(existing_any_image, page), page, "CUSTOM", box, label_text)
        existing_boxes.add(key)

    # Stable ordering by (page, ymin, xmin)
    def sort_key(r):
        try:
            return (
                int(float(r.get("page", "0") or 0)),
                float(r.get("ymin", "0") or 0),
                float(r.get("xmin", "0") or 0),
            )
        except Exception:
            return (9999, 1.0, 1.0)

    filtered2.sort(key=sort_key)

    with REVIEW_CSV_OUT.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(filtered2)

    print("Wrote edited review CSV:", REVIEW_CSV_OUT)
    print("Rows:", len(orig_rows), "->", len(filtered2))


if __name__ == "__main__":
    main()

