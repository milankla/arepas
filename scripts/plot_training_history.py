"""
Generate b5_recovery_comparison.png — visual history of all training runs.

Three panels:
  1. Training curves (overall val accuracy per epoch) for key runs
  2. Best accuracy bar chart (all completed runs, grouped by backbone)
  3. Per-task accuracy comparison — best B5 vs best ResNet50
"""

import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Log parsing
# ---------------------------------------------------------------------------

def parse_log(path: Path) -> list[float]:
    """Return list of overall val accuracy (0–1) per epoch, in order."""
    accs = []
    for line in path.read_text(errors="replace").splitlines():
        m = re.search(r"Overall Acc:\s*([\d.]+)", line)
        if m:
            accs.append(float(m.group(1)))
    return accs


# ---------------------------------------------------------------------------
# Run registry
# ---------------------------------------------------------------------------

# Each entry: (label, log_path_relative, color, linestyle, marker, include_curve)
RUNS = [
    # ── ResNet50 baseline ──────────────────────────────────────────────────
    ("ResNet50 v7 (bs=32)",
     "outputs/data2/v7/train_phase1.log",
     "#2196F3", "-", "o", True),

    # ── B5 early failures ─────────────────────────────────────────────────
    ("B5 v1 (bs=4, no ES)",
     "outputs/data2/b5/v1/train_phase1.log",
     "#FF9800", ":", "x", True),
    ("B5 v2 (bs=4, WD=0.03)",
     "outputs/data2/b5/v2/train_phase1.log",
     "#F44336", "--", "x", True),
    ("B5 v3 (bs=4, WD=0.01)",
     "outputs/data2/b5/v3/train_phase1.log",
     "#E91E63", "-.", "x", True),

    # ── bs=8 recovery ────────────────────────────────────────────────────
    ("B5 v4 retry2 (bs=8, baseline)",
     "outputs/data2/b5/v4_bs8_retry2/train_phase1.log",
     "#9C27B0", "--", "s", True),
    ("B5 v5 (bs=8, WD=0.005)",
     "outputs/data2/b5/v5/train_phase1.log",
     "#673AB7", "-.", "s", True),
    ("B5 v6 (bs=8, 18-class cladding)",
     "outputs/data2/b5/v6/train_phase1.log",
     "#795548", ":", "D", True),

    # ── Grid winner ──────────────────────────────────────────────────────
    ("B5 grid winner (bs=8, lr=1.1e-4, WD=0.010)",
     "outputs/data2/grid/lr1.1e-4_wd0.010/train_phase1.log",
     "#4CAF50", "--", "^", True),

    # ── Best run ────────────────────────────────────────────────────────
    ("B5 v7_bs16 (bs=16, lr=1.5e-4) ★",
     "outputs/data2/b5/v7_bs16/train_phase1.log",
     "#F50057", "-", "o", True),

    # ── Cropped dataset runs ─────────────────────────────────────────────
    ("B5 cropped_v1 (interrupted ep1)",
     "outputs/data2/b5/cropped_v1/train_phase1.log",
     "#00BCD4", ":", "x", True),
    ("B5 cropped_v2 (bs=16, lr=1e-4) ✦",
     "outputs/data2/b5/cropped_v2/train_phase1.log",
     "#00E676", "-", "D", True),
]

# Bar chart — all completed runs with a known peak accuracy
BAR_RUNS = [
    # ResNet50
    ("ResNet50 v1", 69.83, "resnet"),
    ("ResNet50 v2", 77.54, "resnet"),   # misleading Brick shortcut
    ("ResNet50 v3", 77.21, "resnet"),   # misleading
    ("ResNet50 v5", 68.46, "resnet"),
    ("ResNet50 v6", 69.51, "resnet"),
    ("ResNet50 v7", 71.35, "resnet"),
    # B5
    ("B5 v1", 69.45, "b5"),
    ("B5 v2", 60.03, "b5"),
    ("B5 v3", 60.80, "b5"),
    ("B5 v4 retry2", 68.96, "b5"),
    ("B5 v5", 66.08, "b5"),
    ("B5 v6 (18-class)", 62.55, "b5"),
    ("Grid lr=1.0e-4 wd=0.008", 68.39, "b5_grid"),
    ("Grid lr=1.0e-4 wd=0.009", 65.93, "b5_grid"),
    ("Grid lr=1.0e-4 wd=0.010", 66.49, "b5_grid"),
    ("Grid lr=1.1e-4 wd=0.008", 65.74, "b5_grid"),
    ("Grid lr=1.1e-4 wd=0.009", 56.65, "b5_grid"),
    ("Grid lr=1.1e-4 wd=0.010 ★", 68.51, "b5_grid"),
    ("Grid lr=1.2e-4 wd=0.008", 67.65, "b5_grid"),
    ("Grid lr=1.2e-4 wd=0.009", 67.73, "b5_grid"),
    ("Grid lr=1.2e-4 wd=0.010", 67.32, "b5_grid"),
    ("B5 v7_bs16 ★★", 71.86, "b5_best"),
    # Cropped runs
    ("B5 cropped_v1 (ep1 only)", 49.54, "b5_crop"),
    ("B5 cropped_v2 ✦", 70.91, "b5_crop"),
]

# Per-task breakdown
TASK_LABELS  = ["stories", "roof_type", "cladding", "chimney", "setting", "arch_style", "bldg_form"]
RESNET_V7    = [73.11, 52.32, 55.50, 93.64, 81.30]
B5_V7_BS16   = [73.59, 52.81, 59.66, 92.42, 80.81]
B5_CROPPED_V2 = [75.31, 53.06, 54.03, 91.44, 80.73]

# Phase 2 per-task data (7 tasks)
PH2_TASK_LABELS = ["stories", "roof_type", "cladding", "chimney", "setting", "arch_style", "bldg_form"]
PH2_FULL        = [72.13, 54.52, 59.41, 92.67, 82.33, 59.66, 45.72]  # phase2_full (pre-crop)
PH2_CROP_V2     = [63.57, 54.28, 28.36, 89.00, 81.60, 58.68, 47.92]  # cropped_v2 ph2 (frozen heads)
PH2_CROP_V3     = [70.90, 46.21, 54.03, 91.93, 80.26, 57.46, 45.23]  # cropped_v3_phase2 (diff LR)

# ---------------------------------------------------------------------------
# Build figure
# ---------------------------------------------------------------------------

fig = plt.figure(figsize=(20, 18))
fig.patch.set_facecolor("#0D1117")

gs = fig.add_gridspec(3, 1, hspace=0.42, top=0.93, bottom=0.06, left=0.07, right=0.97)
ax1 = fig.add_subplot(gs[0])
ax2 = fig.add_subplot(gs[1])
ax3 = fig.add_subplot(gs[2])

DARK_BG   = "#0D1117"
PANEL_BG  = "#161B22"
GRID_COL  = "#21262D"
TEXT_COL  = "#C9D1D9"
TITLE_COL = "#F0F6FC"

for ax in (ax1, ax2, ax3):
    ax.set_facecolor(PANEL_BG)
    ax.tick_params(colors=TEXT_COL, labelsize=9)
    ax.spines[:].set_color(GRID_COL)
    ax.grid(color=GRID_COL, linewidth=0.6, zorder=0)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_color(TEXT_COL)

# ── Panel 1: Training curves ───────────────────────────────────────────────
ax1.set_title("Overall Val Accuracy per Epoch — All Key Runs",
              color=TITLE_COL, fontsize=12, fontweight="bold", pad=8)
ax1.set_xlabel("Epoch", color=TEXT_COL, fontsize=9)
ax1.set_ylabel("Overall Val Accuracy (%)", color=TEXT_COL, fontsize=9)

plotted = 0
for label, rel_path, color, ls, marker, include in RUNS:
    if not include:
        continue
    log_path = ROOT / rel_path
    if not log_path.exists():
        print(f"  [skip] {rel_path} not found", file=sys.stderr)
        continue
    accs = parse_log(log_path)
    if not accs:
        print(f"  [skip] {rel_path} — no accuracy lines", file=sys.stderr)
        continue
    pct = [a * 100 if a <= 1.0 else a for a in accs]
    lw = 2.5 if "v7_bs16" in rel_path or "v7/train" in rel_path else 1.2
    alpha = 1.0 if ("v7_bs16" in rel_path or "v7/train" in rel_path
                     or "grid/lr1.1e-4_wd0.010" in rel_path) else 0.65
    ax1.plot(range(1, len(pct) + 1), pct,
             color=color, linestyle=ls, linewidth=lw,
             marker=marker, markersize=4 if lw > 1.5 else 2.5,
             alpha=alpha, label=label, zorder=3 if lw > 1.5 else 2)
    plotted += 1

# Reference lines
ax1.axhline(71.86, color="#F50057", linewidth=0.8, linestyle="--", alpha=0.4, zorder=1)
ax1.axhline(71.35, color="#2196F3", linewidth=0.8, linestyle="--", alpha=0.4, zorder=1)
ax1.axhline(70.91, color="#00E676", linewidth=0.8, linestyle="--", alpha=0.4, zorder=1)
ax1.text(0.5, 71.86 + 0.3, "B5 v7_bs16 best: 71.86%",
         color="#F50057", fontsize=7.5, alpha=0.8)
ax1.text(0.5, 71.35 - 1.0, "ResNet50 v7 best: 71.35%",
         color="#2196F3", fontsize=7.5, alpha=0.8)
ax1.text(0.5, 70.91 - 2.2, "B5 cropped_v2 best: 70.91%",
         color="#00E676", fontsize=7.5, alpha=0.8)
ax1.set_ylim(30, 85)
leg = ax1.legend(loc="lower right", fontsize=7.5, framealpha=0.15,
                 labelcolor=TEXT_COL, facecolor=PANEL_BG, edgecolor=GRID_COL,
                 ncol=2)

# ── Panel 2: Bar chart (all runs) ─────────────────────────────────────────
ax2.set_title("Best Overall Accuracy — All Completed Runs",
              color=TITLE_COL, fontsize=12, fontweight="bold", pad=8)
ax2.set_ylabel("Best Val Accuracy (%)", color=TEXT_COL, fontsize=9)

COLOR_MAP = {
    "resnet":   "#2196F3",
    "b5":       "#9C27B0",
    "b5_grid":  "#4CAF50",
    "b5_best":  "#F50057",
    "b5_crop":  "#00E676",
}

labels_bar = [r[0] for r in BAR_RUNS]
values_bar = [r[1] for r in BAR_RUNS]
groups_bar = [r[2] for r in BAR_RUNS]
colors_bar = [COLOR_MAP[g] for g in groups_bar]

x = np.arange(len(labels_bar))
bars = ax2.bar(x, values_bar, color=colors_bar, alpha=0.85, edgecolor=GRID_COL,
               linewidth=0.5, zorder=3)

# Value labels on bars
for bar, val in zip(bars, values_bar):
    ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
             f"{val:.1f}", ha="center", va="bottom",
             color=TEXT_COL, fontsize=6.5, rotation=90)

ax2.set_xticks(x)
ax2.set_xticklabels(labels_bar, rotation=55, ha="right", fontsize=7)
ax2.set_ylim(40, 82)

# Note on misleading runs
ax2.axhline(71.86, color="#F50057", linewidth=1.0, linestyle="--", alpha=0.5)
ax2.text(len(labels_bar) - 0.5, 72.2, "71.86% best", color="#F50057",
         fontsize=7.5, ha="right", alpha=0.8)
ax2.annotate("⚠ Brick shortcut\n(F1 ~13%)", xy=(1, 77.54), xytext=(2.5, 79.5),
             color="#FFD54F", fontsize=7, arrowprops=dict(arrowstyle="->",
             color="#FFD54F", lw=0.8))

# Legend
patch_resnet = mpatches.Patch(color=COLOR_MAP["resnet"],   label="ResNet50")
patch_b5     = mpatches.Patch(color=COLOR_MAP["b5"],       label="B5 main runs")
patch_grid   = mpatches.Patch(color=COLOR_MAP["b5_grid"],  label="B5 grid search")
patch_best   = mpatches.Patch(color=COLOR_MAP["b5_best"],  label="B5 best (v7_bs16)")
patch_crop   = mpatches.Patch(color=COLOR_MAP["b5_crop"],  label="B5 cropped dataset")
ax2.legend(handles=[patch_resnet, patch_b5, patch_grid, patch_best, patch_crop],
           fontsize=8, framealpha=0.15, labelcolor=TEXT_COL,
           facecolor=PANEL_BG, edgecolor=GRID_COL, loc="lower right")

# ── Panel 3: Phase 2 per-task comparison ─────────────────────────────────
ax3.set_title(
    "Phase 2 Per-Task Accuracy — pre-crop vs frozen-heads vs diff-LR (7 tasks)",
    color=TITLE_COL, fontsize=12, fontweight="bold", pad=8)
ax3.set_ylabel("Accuracy / Jaccard (%)", color=TEXT_COL, fontsize=9)

xp = np.arange(len(PH2_TASK_LABELS))
w = 0.26
b_full = ax3.bar(xp - w, PH2_FULL,    width=w,
                  label="phase2_full (pre-crop, 66.63%) ★",
                  color="#F50057", alpha=0.85, edgecolor=GRID_COL, linewidth=0.5)
b_cv2  = ax3.bar(xp,     PH2_CROP_V2, width=w,
                  label="cropped_v2 ph2 (frozen heads, 60.49%)",
                  color="#FF9800", alpha=0.75, edgecolor=GRID_COL, linewidth=0.5)
b_cv3  = ax3.bar(xp + w, PH2_CROP_V3, width=w,
                  label="cropped_v3_phase2 (diff LR, 63.72%) ✦",
                  color="#00E676", alpha=0.85, edgecolor=GRID_COL, linewidth=0.5)

for bars_group in (b_full, b_cv2, b_cv3):
    for bar in bars_group:
        ax3.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                 f"{bar.get_height():.1f}%", ha="center", va="bottom",
                 color=TEXT_COL, fontsize=6.5, rotation=90)

ax3.set_xticks(xp)
ax3.set_xticklabels(PH2_TASK_LABELS, fontsize=10)
ax3.set_ylim(15, 120)

# Delta annotations: v3 vs v2 (frozen)
for i, (v2, v3) in enumerate(zip(PH2_CROP_V2, PH2_CROP_V3)):
    delta = v3 - v2
    col = "#4CAF50" if delta >= 0 else "#FF5722"
    sign = "+" if delta >= 0 else ""
    ax3.text(i + w / 2, max(v2, v3) + 8.0, f"{sign}{delta:.1f}pp",
             ha="center", color=col, fontsize=8, fontweight="bold")

# Annotate the cladding fix
ax3.annotate("Collapse\nfixed!",
             xy=(2 + w / 2, PH2_CROP_V3[2] + 8),
             xytext=(2 + w / 2 + 0.1, PH2_CROP_V3[2] + 26),
             color="#00E676", fontsize=8, ha="center", fontweight="bold",
             arrowprops=dict(arrowstyle="->", color="#00E676", lw=1.0))

leg3 = ax3.legend(fontsize=8.5, framealpha=0.15, labelcolor=TEXT_COL,
                  facecolor=PANEL_BG, edgecolor=GRID_COL)

# ── Figure title ─────────────────────────────────────────────────────────
fig.suptitle(
    "Arepas — B5 Training History & Phase 2 Results  |  data2/  |  May 2026",
    color=TITLE_COL, fontsize=14, fontweight="bold", y=0.975
)

# ── Save ─────────────────────────────────────────────────────────────────
out = ROOT / "charts" / "training_comparison_phase1.png"
out.parent.mkdir(exist_ok=True)
fig.savefig(out, dpi=150, bbox_inches="tight", facecolor=DARK_BG)
print(f"Saved → {out}")
