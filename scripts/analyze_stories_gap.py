"""Analyze the 17pp val→test accuracy gap on the 'stories' task."""
import sys
import warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, '.')

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split

df = pd.read_csv('data2/image_label_mapping_phase1.csv')
buildings_df = (
    df.drop_duplicates('building_id')[['building_id', 'architectural_style', 'neighborhood']]
    .reset_index(drop=True)
)

train_bids, temp_df = train_test_split(buildings_df, test_size=0.30, random_state=42, stratify=None)
val_bids, test_bids = train_test_split(temp_df, test_size=0.50, random_state=42, stratify=None)

train_df = df[df['building_id'].isin(set(train_bids['building_id']))]
val_df   = df[df['building_id'].isin(set(val_bids['building_id']))]
test_df  = df[df['building_id'].isin(set(test_bids['building_id']))]

VAL_ACC  = 0.7213  # epoch 11
TEST_ACC = 0.5515
VAL_N    = len(val_df)   # 409
TEST_N   = len(test_df)  # 388
VAL_CORRECT  = round(VAL_ACC  * VAL_N)   # 295
TEST_CORRECT = round(TEST_ACC * TEST_N)   # 214

print("=" * 60)
print("STORIES TASK — 17pp VAL→TEST GAP ANALYSIS")
print("=" * 60)

# ── 1. Class distribution ─────────────────────────────────────────
print("\n[1] Class distribution across splits")
print(f"{'class':12s}  {'train':>12s}  {'val':>12s}  {'test':>12s}")
for cls in ['1', '1-1/2', '2', '2-1/2', '3', '4', '5-9', '10-19']:
    tc = (train_df['stories'] == cls).sum()
    vc = (val_df['stories']   == cls).sum()
    ec = (test_df['stories']  == cls).sum()
    tp = tc / len(train_df) * 100
    vp = vc / VAL_N * 100
    ep = ec / TEST_N * 100
    if tc + vc + ec > 0:
        print(f"  {cls:10s}  {tc:4d} ({tp:4.1f}%)  {vc:3d} ({vp:4.1f}%)  {ec:3d} ({ep:4.1f}%)  Δval→test={ep-vp:+.1f}pp")

# ── 2. Naive baselines ────────────────────────────────────────────
print("\n[2] Naive majority-class baseline vs actual model")
for split, sdf, n, actual in [('val', val_df, VAL_N, VAL_ACC), ('test', test_df, TEST_N, TEST_ACC)]:
    naive = sdf['stories'].value_counts().max() / n
    gap_vs_naive = actual - naive
    print(f"  [{split}] naive={naive:.3f}  model={actual:.3f}  delta={gap_vs_naive:+.3f}")

# ── 3. Critical finding: model is below naive on test ─────────────
print("\n[3] Correct count arithmetic")
print(f"  val:  {VAL_CORRECT}/{VAL_N} correct  ({VAL_ACC:.1%})")
print(f"  test: {TEST_CORRECT}/{TEST_N} correct  ({TEST_ACC:.1%})")
naive_test_correct = (test_df['stories'] == '1').sum()
print(f"  naive (always '1') correct on test: {naive_test_correct}/{TEST_N}  ({naive_test_correct/TEST_N:.1%})")
shortfall = naive_test_correct - TEST_CORRECT
print(f"  model FALLS SHORT of naive by: {shortfall} images ({shortfall/TEST_N:.1%})")
print("  ► The model is predicting minority classes for 1-story buildings.")

# ── 4. Per-class recall solve ─────────────────────────────────────
print("\n[4] Inferred per-class recall (numerical solve)")
print("  System: val:  263*R1 + 92*R1h + 46*R2 + 8*Rr = 295")
print("          test: 275*R1 + 85*R1h + 24*R2 + 4*Rr = 214")
solutions = []
for R1h in np.arange(0.3, 1.01, 0.05):
    for R2 in np.arange(0.3, 1.01, 0.05):
        for Rr in [0.0, 0.25, 0.5]:
            R1_val  = (295 - 92*R1h - 46*R2 - 8*Rr) / 263
            R1_test = (214 - 85*R1h - 24*R2 - 4*Rr) / 275
            if 0 <= R1_val <= 1 and 0 <= R1_test <= 1:
                # Consistent solution requires R1 to be similar
                if abs(R1_val - R1_test) < 0.02:
                    solutions.append((R1_val, R1h, R2, Rr))

if solutions:
    print("  Consistent solutions (R1_val ≈ R1_test, diff < 2pp):")
    for s in sorted(solutions)[:8]:
        R1, R1h, R2, Rr = s
        v_pred = 263*R1 + 92*R1h + 46*R2 + 8*Rr
        t_pred = 275*R1 + 85*R1h + 24*R2 + 4*Rr
        print(f"    R1={R1:.2f}  R1h={R1h:.2f}  R2={R2:.2f}  Rr={Rr:.2f}  "
              f"→ val={v_pred/VAL_N:.3f}  test={t_pred/TEST_N:.3f}")
else:
    print("  No consistent (same recall) solution exists.")
    print("  ► Recall differs between val and test — genuine distribution shift.")
    # Show the gap per class needed
    d1   = 275 - 263  # +12 more 1-story in test
    d1h  = 85  - 92   # -7 fewer 1.5-story in test
    d2   = 24  - 46   # -22 fewer 2-story in test
    dr   = 4   - 8    # -4 fewer rare in test
    print(f"\n  Class count shifts val→test: Δ1={d1:+d}  Δ1h={d1h:+d}  Δ2={d2:+d}  Δrare={dr:+d}")
    print(f"  Correct count shift val→test: {TEST_CORRECT} - {VAL_CORRECT} = {TEST_CORRECT - VAL_CORRECT}")
    print(f"\n  If recall were constant across splits:")
    for R1 in [0.75, 0.80, 0.85]:
        for R1h in [0.50, 0.60]:
            for R2 in [0.70, 0.80]:
                predicted_test = 275*R1 + 85*R1h + 24*R2 + 4*0.25
                predicted_val  = 263*R1 + 92*R1h + 46*R2 + 8*0.25
                if abs(predicted_val - VAL_CORRECT) < 10:
                    print(f"    R1={R1}  R1h={R1h}  R2={R2}  →  predicted_test_acc={predicted_test/TEST_N:.3f}  (actual={TEST_ACC:.3f})")

# ── 5. StreetcarCommercial anomaly ────────────────────────────────
print("\n[5] StreetcarCommercial split anomaly")
print("  (Only neighborhood with significant multi-story buildings)")
for split, sdf in [('val', val_df), ('test', test_df)]:
    sc = sdf[sdf['neighborhood'] == 'StreetcarCommercial']
    vc = sc['stories'].value_counts().to_dict()
    print(f"  [{split}] {len(sc)} images: {vc}")
print("  ► val got 15/16 multi-story SC images; test got 8/8 single-story SC images.")
print("    Model may have learned visual cues from SC buildings that fire on test.")

# ── 6. Missing classes in test ────────────────────────────────────
print("\n[6] Classes present in training but absent from test")
train_classes = set(train_df['stories'].unique())
test_classes  = set(test_df['stories'].unique())
missing = sorted(train_classes - test_classes)
print(f"  Missing from test: {missing}")
print("  If model predicts these for any test image → automatic miss.")
# Count how many training images belong to these classes
for mc in missing:
    n = (train_df['stories'] == mc).sum()
    print(f"    '{mc}': {n} train images — model has learned this class")

# ── 7. Summary ────────────────────────────────────────────────────
print("\n[7] Root cause summary")
print("""
  The 17pp gap is caused by MULTIPLE compounding factors:

  A) NON-STRATIFIED SPLIT (primary cause):
     - arch_style has rare classes (<3 buildings) → fell back to random split
     - Random split produced systematically different stories distributions
     - val: 64.3% 1-story | test: 70.9% 1-story  (+6.6pp shift)
     - val: 11.2% 2-story | test:  6.2% 2-story  (−5.1pp shift, 22 fewer images)

  B) MODEL IS BELOW NAIVE BASELINE ON TEST (secondary cause):
     - naive (predict 1-story always): val=64.3%, test=70.9%
     - model achieves: val=72.1%, test=55.2%
     - Model actively misclassifies 1-story buildings as minority classes
     - Shortfall vs naive: ~62 images the model gets wrong but naive gets right

  C) STREETCARCOMMERCIAL SPLIT BIAS (contributing):
     - 5 SC buildings in val: 1×1-story, 10×1.5-story, 5×2-story
     - 3 SC buildings in test: 8×1-story, 0×2-story
     - SC commercial visual features learned as "multi-story signals"
       may fire on the wrong test buildings

  D) RARE CLASSES ABSENT FROM TEST ('3', '4', '5-9', '10-19'):
     - Model trained on 8 classes; test only has 4
     - Any prediction of missing classes on test → automatic miss

  FIX OPTIONS:
  1. Stratify on 'stories' instead of (failed) arch_style — reduces split variance
  2. Add 'neighborhood' as secondary stratification key
  3. Treat stories as regression (ordinal) not 8-class classification
  4. Merge rare classes: [1, 1-1/2, 2, 2+] → 4 classes
""")
