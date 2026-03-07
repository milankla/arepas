"""
Attribute Dependency Analysis
Computes Cramér's V association matrix + conditional distributions
across key architectural attributes to inform multi-task training strategy.
"""
import sys
sys.path.insert(0, '.')

from src.loader.configurable_loader import ConfigurableDataLoader
from src.log_config import setup_logging
from collections import defaultdict, Counter
from loguru import logger
import numpy as np

setup_logging()


def get_val(rec, field):
    """Extract a clean scalar value, parsing composite Window/Entrance strings."""
    v = rec.get(field)
    if v is None or str(v).strip() in ('', 'None', 'nan'):
        return None
    v = str(v).strip()
    if field == 'Window' and 'Window Type:' in v:
        return v.split('Window Type:')[1].split(';')[0].split('|')[0].strip()
    if field == 'Entrance' and 'Entrance Type:' in v:
        return v.split('Entrance Type:')[1].split(';')[0].split('|')[0].strip()
    return v


def cramers_v(records, f1, f2):
    """Cramér's V association between two categorical fields (0=none, 1=perfect)."""
    xy = [(get_val(r, f1), get_val(r, f2)) for r in records]
    xy = [(a, b) for a, b in xy if a and b]
    if len(xy) < 10:
        return None
    n = len(xy)
    xs, ys = zip(*xy)
    xc, yc = sorted(set(xs)), sorted(set(ys))
    xi = {c: i for i, c in enumerate(xc)}
    yi = {c: i for i, c in enumerate(yc)}
    table = np.zeros((len(xc), len(yc)))
    for a, b in xy:
        table[xi[a]][yi[b]] += 1
    rs = table.sum(1, keepdims=True)
    cs = table.sum(0, keepdims=True)
    exp = rs * cs / n
    with np.errstate(divide='ignore', invalid='ignore'):
        chi2 = np.nansum((table - exp) ** 2 / np.where(exp == 0, np.inf, exp))
    k = min(len(xc), len(yc))
    return round(float(np.sqrt(chi2 / (n * (k - 1)))), 3) if k > 1 else None


def main():
    loader = ConfigurableDataLoader(config_path="config/data.json")
    all_datasets = loader.load_all_datasets()

    records = []
    for ds_name, nd in all_datasets.items():
        ds_cfg = loader.config.get_dataset(ds_name)
        style = ds_cfg.metadata.get('style', ds_name)
        for bid, bdata in nd.buildings.items():
            flat = {col: entry['value'] for col, entry in bdata.get('attributes', {}).items()}
            flat['_style'] = style
            flat['_num_images'] = len(bdata.get('images', []))
            records.append(flat)

    print(f"\nTotal buildings loaded: {len(records)}\n")

    # ── 1. Cramér's V association matrix ───────────────────────────────────────
    fields = ['Architectural Style', 'Building Form', 'Stories',
              'Roof Type', 'Primary Cladding', 'Setting']
    short  = ['Arch.Style', 'Bldg.Form', 'Stories', 'Roof Type', 'Cladding', 'Setting']

    print("=" * 72)
    print("CRAMÉR'S V ASSOCIATION MATRIX")
    print("  0=no association  |  1=perfect  |  >0.3 = meaningful dependency")
    print("=" * 72)
    print(f"{'':>16}" + "".join(f"{s:>12}" for s in short))
    for f1, s1 in zip(fields, short):
        row = [f"{s1:<16}"]
        for f2 in fields:
            v = 1.0 if f1 == f2 else cramers_v(records, f1, f2)
            cell = f"{v:.3f}" if v is not None else "  -  "
            row.append(f"{cell:>12}")
        print("".join(row))

    # ── 2. Arch Style → Roof Type ──────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("ARCHITECTURAL STYLE → ROOF TYPE")
    print("=" * 72)
    st_rt = defaultdict(Counter)
    for r in records:
        s, t = get_val(r, 'Architectural Style'), get_val(r, 'Roof Type')
        if s and t:
            st_rt[s][t] += 1
    for sty, cnt in sorted(st_rt.items(), key=lambda x: -sum(x[1].values())):
        total = sum(cnt.values())
        top = cnt.most_common(3)
        print(f"  {sty:<30} n={total:3d}  {', '.join(f'{v}({c})' for v, c in top)}")

    # ── 3. Arch Style → Primary Cladding ───────────────────────────────────────
    print("\n" + "=" * 72)
    print("ARCHITECTURAL STYLE → PRIMARY CLADDING")
    print("=" * 72)
    st_cl = defaultdict(Counter)
    for r in records:
        s, c = get_val(r, 'Architectural Style'), get_val(r, 'Primary Cladding')
        if s and c:
            st_cl[s][c] += 1
    for sty, cnt in sorted(st_cl.items(), key=lambda x: -sum(x[1].values())):
        total = sum(cnt.values())
        top = cnt.most_common(3)
        print(f"  {sty:<30} n={total:3d}  {', '.join(f'{v}({c})' for v, c in top)}")

    # ── 4. Building Form → Stories ─────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("BUILDING FORM → STORIES  (leakage risk: near-deterministic?)")
    print("=" * 72)
    bf_st = defaultdict(Counter)
    for r in records:
        bf, st = get_val(r, 'Building Form'), get_val(r, 'Stories')
        if bf and st:
            bf_st[bf][st] += 1
    for bf, cnt in sorted(bf_st.items(), key=lambda x: -sum(x[1].values())):
        total = sum(cnt.values())
        top_pct = [(v, c, round(100 * c / total)) for v, c in cnt.most_common(4)]
        print(f"  {bf:<25} n={total:3d}  {', '.join(f'{v}({c}, {p}%)' for v,c,p in top_pct)}")

    # ── 5. Alteration Level → sub-fields presence ─────────────────────────────
    print("\n" + "=" * 72)
    print("ALTERATION LEVEL → SUB-FIELD PRESENCE  (validate label consistency)")
    print("=" * 72)
    sub = ['Alterations-Additions', 'Alterations-Entrances', 'Alterations-Roof',
           'Alterations-Cladding', 'Alterations-Windows']
    al_data = defaultdict(lambda: {'total': 0, 'altered': 0})
    for r in records:
        al = get_val(r, 'Alteration Level')
        if not al:
            continue
        for sf in sub:
            v = get_val(r, sf)
            if v:
                al_data[al]['total'] += 1
                if v != 'None Visible':
                    al_data[al]['altered'] += 1
    for level in sorted(al_data.keys()):
        d = al_data[level]
        pct = 100 * d['altered'] / d['total'] if d['total'] else 0
        bar = '█' * int(pct / 5)
        print(f"  {level:<22}  {d['altered']:3d}/{d['total']:3d} altered ({pct:5.1f}%)  {bar}")

    # ── 6. Primary Cladding → Wall Features ────────────────────────────────────
    print("\n" + "=" * 72)
    print("PRIMARY CLADDING → TOP WALL FEATURES")
    print("=" * 72)
    cl_wf = defaultdict(Counter)
    for r in records:
        cl = get_val(r, 'Primary Cladding')
        wf = get_val(r, 'Wall Features')
        if cl and wf:
            for feat in wf.split(';'):
                feat = feat.strip()
                if feat:
                    cl_wf[cl][feat] += 1
    for cl, cnt in sorted(cl_wf.items(), key=lambda x: -sum(x[1].values())):
        total = sum(cnt.values())
        top = cnt.most_common(3)
        print(f"  {cl:<22} n={total:3d}  {', '.join(f'{v}({c})' for v, c in top)}")

    # ── 7. Roof Type → Roof Features ───────────────────────────────────────────
    print("\n" + "=" * 72)
    print("ROOF TYPE → TOP ROOF FEATURES")
    print("=" * 72)
    rt_rf = defaultdict(Counter)
    for r in records:
        rt = get_val(r, 'Roof Type')
        rf = get_val(r, 'Roof Features')
        if rt and rf:
            for feat in rf.split(';'):
                feat = feat.strip()
                if feat:
                    rt_rf[rt][feat] += 1
    for rt, cnt in sorted(rt_rf.items(), key=lambda x: -sum(x[1].values()))[:10]:
        total = sum(cnt.values())
        top = cnt.most_common(3)
        print(f"  {rt:<28} n={total:3d}  {', '.join(f'{v}({c})' for v, c in top)}")

    # ── 8. Summary: strong dependencies ────────────────────────────────────────
    print("\n" + "=" * 72)
    print("DEPENDENCY SUMMARY FOR TRAINING STRATEGY")
    print("=" * 72)
    all_fields = ['Architectural Style', 'Building Form', 'Stories',
                  'Roof Type', 'Primary Cladding', 'Setting']
    strong, moderate = [], []
    for i, f1 in enumerate(all_fields):
        for f2 in all_fields[i + 1:]:
            v = cramers_v(records, f1, f2)
            if v is not None:
                if v >= 0.5:
                    strong.append((f1, f2, v))
                elif v >= 0.3:
                    moderate.append((f1, f2, v))

    print("\n  STRONG (V≥0.5) — shared head features likely beneficial:")
    for f1, f2, v in sorted(strong, key=lambda x: -x[2]):
        print(f"    {f1}  ↔  {f2}  (V={v})")
    if not strong:
        print("    None")

    print("\n  MODERATE (0.3≤V<0.5) — auxiliary task benefit possible:")
    for f1, f2, v in sorted(moderate, key=lambda x: -x[2]):
        print(f"    {f1}  ↔  {f2}  (V={v})")
    if not moderate:
        print("    None")

    print("\n  WEAK (V<0.3) — independent heads preferred:")
    weak = [(f1, f2, cramers_v(records, f1, f2))
            for i, f1 in enumerate(all_fields)
            for f2 in all_fields[i + 1:]
            if cramers_v(records, f1, f2) is not None and cramers_v(records, f1, f2) < 0.3]
    for f1, f2, v in sorted(weak, key=lambda x: -x[2]):
        print(f"    {f1}  ↔  {f2}  (V={v})")

    print("\nDone.")


if __name__ == '__main__':
    main()
