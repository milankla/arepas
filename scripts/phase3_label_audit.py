#!/usr/bin/env python3
"""Rank Phase 3 candidate fields on image-bearing data2 buildings.

The audit uses data2/image_label_mapping_phase1.csv because it already contains
one row per image with the deferred schema fields copied onto image-bearing
buildings. Counts are deduplicated by building_id so buildings with multiple
photos do not inflate label coverage.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_CSV = Path("data2/image_label_mapping_phase1.csv")
DEFAULT_OUTPUT_DIR = Path("outputs/phase3_label_audit")
DEFAULT_DOC_PATH = Path("docs/PHASE3_LABEL_AUDIT.md")

ACTIVE_FIELDS = [
    "architectural_style",
    "building_form",
    "roof_type",
    "primary_cladding",
    "stories",
    "setting",
    "chimney_present",
]

PHASE3_VISUAL_CORE_FIELDS = [
    "wall_features",
    "landscape_features",
    "window",
    "entrance",
    "associated_buildings",
]

PHASE3_IMBALANCE_FIELDS = [
    "building_category",
    "current_use",
    "roof_materials",
    "original_use",
]

PHASE3_FIELDS = PHASE3_VISUAL_CORE_FIELDS + PHASE3_IMBALANCE_FIELDS

BASIC_SURVEY_COVERAGE = {
    "wall_features": "Yes: field is Basic + Full Survey.",
    "landscape_features": "Yes: field is Major Alterations + Basic + Full Survey.",
    "window": "Partial: Window, Window Type, and Window Features are Basic + Full; Window Location and Window Material are Full-only.",
    "entrance": "Partial: Entrance, Entrance Type, and Entrance Location are Basic + Full; Entrance Features and Door Type are Full-only.",
    "associated_buildings": "Partial: Associated Building/Object Type and Notes are Basic + Full; Location is Full-only.",
    "building_category": "Yes: field is Major Alterations + Basic + Full Survey.",
    "current_use": "Yes: field is Less than 30 years + Major Alterations + Basic + Full Survey.",
    "roof_materials": "Yes: field is Basic + Full Survey.",
    "original_use": "Yes: field is Less than 30 years + Major Alterations + Basic + Full Survey.",
}


@dataclass(frozen=True)
class CandidateField:
    name: str
    label: str
    parser: str
    visibility_score: float
    complement_score: float
    readiness_score: float
    notes: str


CANDIDATE_FIELDS = [
    CandidateField(
        "wall_features",
        "Wall Features",
        "multi",
        18.0,
        15.0,
        9.0,
        "Strong facade-detail candidate; likely complementary to cladding, style, and form.",
    ),
    CandidateField(
        "landscape_features",
        "Landscape Features",
        "multi",
        14.0,
        13.0,
        9.0,
        "Context task; useful for setting, category, and broader site interpretation.",
    ),
    CandidateField(
        "building_category",
        "Building Category",
        "single",
        16.0,
        14.0,
        10.0,
        "Broad auxiliary classifier; useful if enough non-residential examples exist.",
    ),
    CandidateField(
        "entrance",
        "Entrance",
        "multipart",
        16.0,
        11.0,
        6.0,
        "Promising if grouped around broad entrance type and location.",
    ),
    CandidateField(
        "window",
        "Window",
        "multipart",
        14.0,
        10.0,
        5.0,
        "Promising but visually smaller/noisier than entrance; needs grouping.",
    ),
    CandidateField(
        "associated_buildings",
        "Associated Buildings and Objects",
        "multipart",
        11.0,
        9.0,
        5.0,
        "Context/object task; depends strongly on image angle and full-view coverage.",
    ),
    CandidateField(
        "roof_features",
        "Roof Features",
        "multi",
        10.0,
        9.0,
        8.0,
        "Conceptually useful, but many atomics are expected to be sparse.",
    ),
    CandidateField(
        "roof_materials",
        "Roof Materials",
        "multi",
        7.0,
        5.0,
        8.0,
        "Often dominated by asphalt/unknown and hard to verify from street-level photos.",
    ),
    CandidateField(
        "additional_cladding",
        "Additional Cladding",
        "multi",
        8.0,
        6.0,
        8.0,
        "Secondary material task; likely sparse and better deferred unless counts surprise.",
    ),
    CandidateField(
        "current_use",
        "Current Use",
        "single",
        10.0,
        8.0,
        8.0,
        "Broad use categories may be visual; fine-grained use is context-heavy.",
    ),
    CandidateField(
        "original_use",
        "Original Use",
        "single",
        4.0,
        4.0,
        8.0,
        "Historical field; weak image-only target despite high label coverage.",
    ),
    CandidateField(
        "building_plan",
        "Building Plan",
        "single",
        5.0,
        6.0,
        8.0,
        "Usually needs aerial or multi-view information; front facade is often insufficient.",
    ),
]

MULTIPART_SUBFIELDS = {
    "window": ["Window Type", "Window Features", "Window Location", "Window Material"],
    "entrance": ["Entrance Type", "Entrance Location", "Entrance Features", "Door Type"],
    "associated_buildings": ["Building/Object Type", "Building/Object Location"],
}


def clean_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    text = str(value).strip()
    if text.lower() in {"", "nan", "none", "null"}:
        return ""
    return text


def split_multi(value: str) -> list[str]:
    return [part.strip() for part in value.split(";") if part.strip()]


def split_subfield_values(value: str) -> list[str]:
    parts: list[str] = []
    for chunk in re.split(r"\s+-\s+", value):
        chunk = chunk.strip()
        if chunk:
            parts.append(chunk)
    return parts or [value.strip()]


def parse_multipart(value: str, field_name: str) -> list[str]:
    labels: list[str] = []
    subfields = MULTIPART_SUBFIELDS.get(field_name, [])
    for record in re.split(r"\s+\|\s+", value):
        for subfield in subfields:
            pattern = rf"{re.escape(subfield)}:\s*(.*?)(?=;\s*[A-Z][A-Za-z/ ]+:|$)"
            match = re.search(pattern, record)
            if not match:
                continue
            raw = match.group(1).strip()
            for part in split_subfield_values(raw):
                labels.append(f"{subfield}: {part}")
    return labels


def parse_labels(value: Any, candidate: CandidateField) -> list[str]:
    text = clean_value(value)
    if not text:
        return []
    if candidate.parser == "single":
        return [text]
    if candidate.parser == "multi":
        return split_multi(text)
    if candidate.parser == "multipart":
        return parse_multipart(text, candidate.name)
    raise ValueError(f"Unknown parser: {candidate.parser}")


def score_coverage(coverage_pct: float) -> float:
    return round(min(20.0, 20.0 * (coverage_pct / 70.0)), 2)


def balance_multiplier(top_share: float, label_count: int) -> float:
    if label_count <= 1:
        return 0.20
    if top_share >= 0.90:
        return 0.35
    if top_share >= 0.80:
        return 0.55
    if top_share >= 0.65:
        return 0.75
    return 1.0


def score_atomics(counter: Counter[str], labeled_buildings: int) -> tuple[float, dict[str, int], float]:
    strong = sum(1 for count in counter.values() if count >= 300)
    usable = sum(1 for count in counter.values() if 100 <= count < 300)
    group = sum(1 for count in counter.values() if 30 <= count < 100)
    sparse = sum(1 for count in counter.values() if count < 30)
    raw_score = min(25.0, strong * 5.0 + usable * 3.0 + group * 1.25)
    top_count = counter.most_common(1)[0][1] if counter else 0
    top_share = top_count / labeled_buildings if labeled_buildings else 0.0
    score = raw_score * balance_multiplier(top_share, len(counter))
    bins = {"strong": strong, "usable": usable, "group": group, "sparse": sparse}
    return round(score, 2), bins, round(top_share * 100.0, 2)


def score_density(avg_labels: float, parser: str, coverage_pct: float) -> float:
    if coverage_pct < 5.0:
        return 2.0
    if parser == "single":
        return 8.0
    if avg_labels <= 0:
        return 0.0
    if 1.0 <= avg_labels <= 4.0:
        return 10.0
    if avg_labels <= 8.0:
        return 7.0
    return 4.0


def cramers_v(left: list[Any], right: list[Any]) -> float | None:
    pairs = [(clean_value(a), clean_value(b)) for a, b in zip(left, right)]
    pairs = [(a, b) for a, b in pairs if a and b]
    if len(pairs) < 10:
        return None
    left_values = sorted({a for a, _ in pairs})
    right_values = sorted({b for _, b in pairs})
    if len(left_values) < 2 or len(right_values) < 2:
        return None

    left_index = {value: idx for idx, value in enumerate(left_values)}
    right_index = {value: idx for idx, value in enumerate(right_values)}
    table = [[0 for _ in right_values] for _ in left_values]
    for a, b in pairs:
        table[left_index[a]][right_index[b]] += 1

    row_totals = [sum(row) for row in table]
    col_totals = [sum(table[row][col] for row in range(len(left_values))) for col in range(len(right_values))]
    total = sum(row_totals)
    chi2 = 0.0
    for row_idx, row_total in enumerate(row_totals):
        for col_idx, col_total in enumerate(col_totals):
            expected = row_total * col_total / total if total else 0.0
            if expected:
                chi2 += (table[row_idx][col_idx] - expected) ** 2 / expected
    min_dim = min(len(left_values) - 1, len(right_values) - 1)
    if min_dim <= 0 or total == 0:
        return None
    return round(math.sqrt(chi2 / (total * min_dim)), 3)


def max_association(df: pd.DataFrame, label_sets: list[set[str]], top_labels: list[str]) -> dict[str, Any]:
    best = {"field": "", "label": "", "cramers_v": 0.0}
    for label in top_labels[:10]:
        binary = ["Yes" if label in labels else "No" for labels in label_sets]
        if binary.count("Yes") < 30:
            continue
        for active_field in ACTIVE_FIELDS:
            if active_field not in df.columns:
                continue
            value = cramers_v(binary, df[active_field].tolist())
            if value is not None and value > best["cramers_v"]:
                best = {"field": active_field, "label": label, "cramers_v": value}
    return best


def audit_field(df: pd.DataFrame, candidate: CandidateField) -> dict[str, Any]:
    label_sets = [set(parse_labels(value, candidate)) for value in df[candidate.name].tolist()]
    labeled_sets = [labels for labels in label_sets if labels]
    total_buildings = len(df)
    labeled_buildings = len(labeled_sets)
    coverage_pct = (labeled_buildings / total_buildings * 100.0) if total_buildings else 0.0
    density_values = [len(labels) for labels in labeled_sets]
    avg_labels = sum(density_values) / len(density_values) if density_values else 0.0
    max_labels = max(density_values) if density_values else 0

    counter: Counter[str] = Counter()
    for labels in labeled_sets:
        counter.update(labels)

    atomic_score, bins, top_share_pct = score_atomics(counter, labeled_buildings)
    coverage_score = score_coverage(coverage_pct)
    density_score = score_density(avg_labels, candidate.parser, coverage_pct)
    total_score = round(
        coverage_score
        + atomic_score
        + candidate.visibility_score
        + density_score
        + candidate.complement_score
        + candidate.readiness_score,
        2,
    )
    top_labels = counter.most_common(15)
    association = max_association(df, label_sets, [label for label, _ in top_labels])

    return {
        "field": candidate.name,
        "label": candidate.label,
        "parser": candidate.parser,
        "phase3_score": total_score,
        "coverage_score": coverage_score,
        "atomic_score": atomic_score,
        "visibility_score": candidate.visibility_score,
        "density_score": density_score,
        "complement_score": candidate.complement_score,
        "readiness_score": candidate.readiness_score,
        "n_buildings_total": total_buildings,
        "n_buildings_with_label": labeled_buildings,
        "coverage_pct": round(coverage_pct, 2),
        "n_atomic_labels": len(counter),
        "n_strong_labels_300_plus": bins["strong"],
        "n_usable_labels_100_299": bins["usable"],
        "n_grouping_labels_30_99": bins["group"],
        "n_sparse_labels_under_30": bins["sparse"],
        "avg_labels_per_labeled_building": round(avg_labels, 2),
        "max_labels_per_building": max_labels,
        "top_label_share_pct": top_share_pct,
        "max_association_field": association["field"],
        "max_association_label": association["label"],
        "max_association_cramers_v": association["cramers_v"],
        "top_labels": [
            {"label": label, "positive_buildings": count, "coverage_pct": round(count / total_buildings * 100.0, 2)}
            for label, count in top_labels
        ],
        "notes": candidate.notes,
    }


def recommendation_for_field(field: str, rank: int) -> str:
    if field in PHASE3_VISUAL_CORE_FIELDS[:3]:
        return "phase3_core"
    if field in PHASE3_VISUAL_CORE_FIELDS:
        return "phase3_visual_expansion"
    if field in PHASE3_IMBALANCE_FIELDS:
        return "phase3_imbalance_expansion"
    return "phase4_later"


def write_markdown(path: Path, records: list[dict[str, Any]]) -> None:
    core = [r for r in records if r["recommendation"] == "phase3_core"]
    visual_expansion = [r for r in records if r["recommendation"] == "phase3_visual_expansion"]
    imbalance_expansion = [r for r in records if r["recommendation"] == "phase3_imbalance_expansion"]
    later = [r for r in records if r["recommendation"] == "phase4_later"]

    lines = [
        "# Phase 3 Label Audit",
        "",
        "This audit ranks candidate Phase 3 fields using only image-bearing data2 buildings.",
        "Counts are deduplicated by building_id, so multiple photos of one building count once.",
        "",
        "## Basic Survey Check",
        "",
        "All nine requested Phase 3 fields are included in Basic Survey at the top level. Multipart fields have partial Basic Survey coverage because some subfields are Full Survey only.",
        "",
        "| Field | Basic Survey status |",
        "|---|---|",
    ]
    for field in PHASE3_FIELDS:
        lines.append(f"| `{field}` | {BASIC_SURVEY_COVERAGE[field]} |")

    lines.extend([
        "",
        "## Phase 3 Training Plan",
        "",
        "### Core fields",
        "",
    ])
    for record in core:
        lines.append(f"- `{record['field']}` (rank {record['rank']}, score {record['phase3_score']})")
    lines.extend(["", "### Visual expansion fields", ""])
    for record in visual_expansion:
        lines.append(f"- `{record['field']}` (rank {record['rank']}, score {record['phase3_score']})")
    lines.extend(["", "### Imbalance expansion fields", ""])
    for record in imbalance_expansion:
        lines.append(f"- `{record['field']}` (rank {record['rank']}, score {record['phase3_score']})")
    lines.extend([
        "",
        "Training should start with the full nine-field Phase 3 scope, but report metrics in two tracks: visually direct tasks and imbalanced/use tasks. The incoming larger data drop should be used to raise minority-class counts before deciding whether any imbalance field needs grouping.",
        "",
    ])

    lines.extend([
        "## Ranked Fields",
        "",
        "| Rank | Field | Score | Coverage | Usable labels >=100 | Group labels 30-99 | Avg labels | Top label share | Recommendation |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---|",
    ])
    for record in records:
        usable = record["n_strong_labels_300_plus"] + record["n_usable_labels_100_299"]
        lines.append(
            "| {rank} | `{field}` | {score:.2f} | {coverage:.2f}% | {usable} | {group} | {avg:.2f} | {top:.2f}% | {rec} |".format(
                rank=record["rank"],
                field=record["field"],
                score=record["phase3_score"],
                coverage=record["coverage_pct"],
                usable=usable,
                group=record["n_grouping_labels_30_99"],
                avg=record["avg_labels_per_labeled_building"],
                top=record["top_label_share_pct"],
                rec=record["recommendation"],
            )
        )

    lines.extend(["", "## Top Labels By Field", ""])
    for record in records:
        lines.extend([f"### `{record['field']}`", ""])
        lines.append(record["notes"])
        lines.append("")
        lines.append("| Label | Positive buildings | Coverage |")
        lines.append("|---|---:|---:|")
        for label in record["top_labels"][:10]:
            lines.append(
                f"| {label['label']} | {label['positive_buildings']} | {label['coverage_pct']:.2f}% |"
            )
        lines.append("")

    lines.extend(["## Phase 4 / Later Fields", ""])
    for record in later:
        lines.append(f"- `{record['field']}`: rank {record['rank']}, score {record['phase3_score']}. {record['notes']}")
    lines.append("")
    path.write_text("\n".join(lines))


def run_audit(csv_path: Path, output_dir: Path, doc_path: Path) -> list[dict[str, Any]]:
    df = pd.read_csv(csv_path)
    df = df.drop_duplicates("building_id").copy()
    for candidate in CANDIDATE_FIELDS:
        if candidate.name not in df.columns:
            raise KeyError(f"Missing candidate field column: {candidate.name}")

    records = [audit_field(df, candidate) for candidate in CANDIDATE_FIELDS]
    records = sorted(records, key=lambda record: record["phase3_score"], reverse=True)
    for index, record in enumerate(records, start=1):
        record["rank"] = index
        record["recommendation"] = recommendation_for_field(record["field"], index)

    output_dir.mkdir(parents=True, exist_ok=True)
    rankings_csv = output_dir / "phase3_field_rankings.csv"
    summary_cols = [
        "rank",
        "field",
        "label",
        "phase3_score",
        "recommendation",
        "coverage_pct",
        "n_buildings_with_label",
        "n_atomic_labels",
        "n_strong_labels_300_plus",
        "n_usable_labels_100_299",
        "n_grouping_labels_30_99",
        "n_sparse_labels_under_30",
        "avg_labels_per_labeled_building",
        "max_labels_per_building",
        "top_label_share_pct",
        "max_association_field",
        "max_association_label",
        "max_association_cramers_v",
        "notes",
    ]
    pd.DataFrame(records)[summary_cols].to_csv(rankings_csv, index=False)

    details_path = output_dir / "phase3_label_audit.json"
    details_path.write_text(json.dumps({"csv_path": str(csv_path), "fields": records}, indent=2))
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    write_markdown(doc_path, records)
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="Rank Phase 3 candidate labels for data2.")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC_PATH)
    args = parser.parse_args()

    records = run_audit(args.csv, args.out, args.doc)
    print(f"Wrote Phase 3 audit to {args.out}")
    print(f"Wrote Phase 3 audit docs to {args.doc}")
    print("\nTop Phase 3 candidates:")
    for record in records[:5]:
        print(
            f"  {record['rank']:>2}. {record['field']:<22} "
            f"score={record['phase3_score']:<6.2f} "
            f"coverage={record['coverage_pct']:>6.2f}% "
            f"recommendation={record['recommendation']}"
        )


if __name__ == "__main__":
    main()
