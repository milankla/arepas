"""Analyse roof_type label distribution in a CSV."""
import ast
import collections
import sys

import pandas as pd

csv = sys.argv[1] if len(sys.argv) > 1 else "data2/image_label_mapping_phase1.csv"
df = pd.read_csv(csv).drop_duplicates(subset="building_id")

labels_per_building = []
for v in df["roof_type"].dropna():
    try:
        items = ast.literal_eval(v)
        labels_per_building.append(tuple(sorted(items)))
    except Exception:
        labels_per_building.append((str(v),))

counter = collections.Counter(labels_per_building)
print("=== Most common roof_type combos (per unique building) ===")
for combo, n in counter.most_common(20):
    print(f"  {n:4d}  {list(combo)}")

one = sum(n for k, n in counter.items() if len(k) == 1)
two = sum(n for k, n in counter.items() if len(k) == 2)
thr = sum(n for k, n in counter.items() if len(k) >= 3)
total = one + two + thr
print()
print(f"Total buildings with roof_type: {total}")
print(f"  Single label : {one:4d} ({one/total:.0%})")
print(f"  Two labels   : {two:4d} ({two/total:.0%})")
print(f"  3+ labels    : {thr:4d} ({thr/total:.0%})")
print(f"  Distinct combos: {len(counter)}")

all_labels = [lbl for combo in labels_per_building for lbl in combo]
print()
print("=== Individual label frequency ===")
for lbl, n in collections.Counter(all_labels).most_common():
    print(f"  {n:4d}  {lbl}")
