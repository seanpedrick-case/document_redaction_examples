import csv
from pathlib import Path

csv_path = next(Path("output_final").glob("*_review_file.csv"))
with csv_path.open("r", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

fields = list(rows[0].keys())
print("Fields:", fields)
print()

print("All rows by page:")
for r in rows:
    pg = r["page"]
    img = r.get(fields[0], "")[:50]
    label = r["label"]
    text = r.get("text", "")[:30]
    print(f"  Page {pg} | {label} | {text} | img={img}")
