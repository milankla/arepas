"""
Serve a side-by-side preview of original vs cropped building images.

Usage
─────
    python scripts/preview_crops.py
    python scripts/preview_crops.py --manifest crops/data2/crop_manifest.csv
    python scripts/preview_crops.py --image-root . --out-root crops/data2 --port 8080 --limit 50

Opens http://localhost:8000 in your browser automatically.
Stop with Ctrl-C.
"""

import argparse
import os
import sys
import threading
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

import pandas as pd

# ── HTML template ─────────────────────────────────────────────────────────────

_HTML_HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Crop Preview</title>
<style>
  body { font-family: system-ui, sans-serif; background: #111; color: #eee; margin: 0; padding: 16px; }
  h1   { font-size: 1.2rem; margin: 0 0 12px; color: #aaa; }
  .stats { font-size: 0.85rem; color: #888; margin-bottom: 20px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(480px, 1fr)); gap: 12px; }
  .card { background: #1e1e1e; border-radius: 8px; overflow: hidden; }
  .card-header { padding: 6px 10px; font-size: 0.72rem; color: #888;
                 white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .card-header .method-detected   { color: #4caf50; font-weight: bold; }
  .card-header .method-fallback   { color: #ff9800; }
  .card-header .method-error      { color: #f44336; }
  .pair { display: flex; gap: 2px; }
  .pair figure { flex: 1; margin: 0; }
  .pair figure figcaption { text-align: center; font-size: 0.68rem; color: #666;
                             padding: 3px 0 5px; }
  .pair img { width: 100%; height: auto; display: block; }
  .pair img.missing { background: #2a2a2a; height: 200px; }
</style>
</head>
<body>
<h1>Crop Preview</h1>
"""

_HTML_FOOT = "</div></body></html>\n"


def method_class(method: str) -> str:
    if method == "detected":
        return "method-detected"
    if "fallback" in method:
        return "method-fallback"
    return "method-error"


def build_html(
    manifest_path: Path,
    image_root: Path,
    out_root: Path,
    limit: int,
) -> str:
    df = pd.read_csv(manifest_path)
    if limit:
        df = df.head(limit)

    total     = len(df)
    n_det     = (df["method"] == "detected").sum()
    n_fall    = df["method"].str.contains("fallback", na=False).sum()
    n_err     = total - n_det - n_fall

    stats = (
        f"{total} images &nbsp;|&nbsp; "
        f"<span style='color:#4caf50'>{n_det} detected</span> &nbsp;|&nbsp; "
        f"<span style='color:#ff9800'>{n_fall} fallback</span> &nbsp;|&nbsp; "
        f"<span style='color:#f44336'>{n_err} errors/missing</span>"
    )

    parts = [_HTML_HEAD, f'<div class="stats">{stats}</div>\n<div class="grid">\n']

    workspace = image_root  # image_root is already the workspace root

    for _, row in df.iterrows():
        img_abs   = image_root / row["image_path"]
        crop_rel  = row.get("cropped_path", "")
        crop_abs  = out_root / crop_rel if crop_rel else None
        method    = str(row.get("method", ""))
        conf      = float(row.get("confidence", 0))
        label_cls = method_class(method)
        name      = Path(row["image_path"]).name

        # Use root-relative URLs (leading /) so the browser resolves them
        # from the server root (workspace), not from /crops/ where the HTML lives.
        orig_src = "/" + str(img_abs.relative_to(image_root))  if img_abs.exists()               else ""
        crop_src = "/" + str(crop_abs.relative_to(image_root)) if (crop_abs and crop_abs.exists()) else ""

        conf_txt = f"  conf={conf:.2f}" if conf else ""
        header   = (
            f'<div class="card-header">'
            f'<span class="{label_cls}">[{method}]</span>{conf_txt} &nbsp; {name}'
            f'</div>'
        )

        def img_tag(src, caption):
            if src:
                return f'<figure><img src="{src}" loading="lazy"><figcaption>{caption}</figcaption></figure>'
            return f'<figure><div class="pair img missing"></div><figcaption>{caption} (missing)</figcaption></figure>'

        parts.append(
            f'<div class="card">{header}'
            f'<div class="pair">'
            f'{img_tag(orig_src, "original")}'
            f'{img_tag(crop_src, "crop")}'
            f'</div></div>\n'
        )

    parts.append(_HTML_FOOT)
    return "".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Serve side-by-side crop preview in the browser.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--manifest", default="crops/data2/crop_manifest.csv",
        help="Path to crop_manifest.csv",
    )
    parser.add_argument("--image-root", default=".", help="Root for image_path values")
    parser.add_argument("--out-root",   default="crops/data2", help="Root for cropped_path values")
    parser.add_argument("--port",  type=int, default=8000)
    parser.add_argument("--limit", type=int, default=200, help="Max rows to show (0 = all)")
    args = parser.parse_args()

    workspace = Path(__file__).parent.parent
    manifest  = workspace / args.manifest
    if not manifest.exists():
        print(f"Manifest not found: {manifest}", file=sys.stderr)
        sys.exit(1)

    html = build_html(
        manifest_path=manifest,
        image_root=workspace / args.image_root,
        out_root=workspace / args.out_root,
        limit=args.limit or None,
    )

    preview_path = workspace / "crops" / "preview.html"
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    preview_path.write_text(html, encoding="utf-8")
    print(f"Preview written to {preview_path}")

    # Serve from workspace root so relative image paths resolve correctly
    os.chdir(workspace)

    url = f"http://localhost:{args.port}/crops/preview.html"

    # Open browser after a short delay so server is ready
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    print(f"Serving at {url}  (Ctrl-C to stop)")
    try:
        HTTPServer(("", args.port), SimpleHTTPRequestHandler).serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
