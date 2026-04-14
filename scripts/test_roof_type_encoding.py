"""Smoke test: verify roof_type single-label encoding is correct."""
import sys
sys.path.insert(0, ".")

from src.loader.architectural_dataset import make_splits, normalize_roof_type_label
from src.models.model_config import ModelConfig

# Unit test the helper
cases = [
    ("Hipped",                          "Hipped"),
    ("Front Gable",                     "Front Gable"),
    ("Hipped; Front Gable",             "Compound"),
    ("Front Gable; Hipped",             "Compound"),
    ("Compound Roof",                   "Compound"),
    ("Compound Roof; Hipped; Side Gable", "Compound"),
    ("Flat",                            "Flat"),
]
print("=== normalize_roof_type_label() ===")
all_ok = True
for inp, expected in cases:
    got = normalize_roof_type_label(inp)
    status = "✓" if got == expected else "✗"
    if got != expected:
        all_ok = False
    print(f"  {status}  '{inp}' → '{got}'  (expected '{expected}')")
print()

# Dataset integration test
cfg = ModelConfig.from_json("config/models/resnet50.json")
train, val, test = make_splits.__wrapped__(  # bypass cache if wrapped
    "data2/image_label_mapping_phase1.csv",
) if hasattr(make_splits, "__wrapped__") else (
    lambda: make_splits(
        csv_path="data2/image_label_mapping_phase1.csv",
        model_config=cfg,
    )
)()

print("=== roof_type encoder classes ===")
enc = train.label_encoders["roof_type"]
print(f"  Type: {type(enc).__name__}")
print(f"  Classes ({len(enc.classes_)}): {list(enc.classes_)}")
print()

# Verify no semicolons in the encoded classes
bad = [c for c in enc.classes_ if ";" in c]
if bad:
    print(f"  ✗ BAD: semicolons found in classes: {bad}")
    all_ok = False
else:
    print("  ✓ No semicolons in encoded classes")

# Sample a few rows and verify encoding works
import pandas as pd
df = pd.read_csv("data2/image_label_mapping_phase1.csv")
raw_samples = df["roof_type"].dropna().unique()[:10]
print()
print("=== Sample encoding ===")
from src.loader.architectural_dataset import normalize_roof_type_label
from src.loader.csv_parser import normalize_value

for raw in raw_samples:
    val = normalize_roof_type_label(normalize_value(raw))
    idx = enc.transform([val])[0]
    print(f"  '{raw}' → '{val}' → class {idx}")

print()
print("All OK" if all_ok else "FAILURES DETECTED")
