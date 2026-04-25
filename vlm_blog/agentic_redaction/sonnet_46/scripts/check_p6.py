import csv
from pathlib import Path

csv_path = next(Path("output_final").glob("*_review_file.csv"))
with csv_path.open("r", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

print("Page 6 rows:")
for r in rows:
    if r["page"] == "6":
        print(f"  {r['label']} text={repr(r.get('text',''))[:40]} xmin={r['xmin']} ymin={r['ymin']} xmax={r['xmax']} ymax={r['ymax']}")
