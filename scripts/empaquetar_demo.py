#!/usr/bin/env python3
"""Empaqueta la demo estática en un único HTML apto para cargar a S3."""

from __future__ import annotations

import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = ROOT / "demo"


def build_html() -> str:
    html = (DEMO_DIR / "index.html").read_text(encoding="utf-8")
    css = (DEMO_DIR / "styles.css").read_text(encoding="utf-8")
    js = (DEMO_DIR / "app.js").read_text(encoding="utf-8")

    css_link = '<link rel="stylesheet" href="styles.css">'
    script_link = '<script src="app.js"></script>'
    if html.count(css_link) != 1 or html.count(script_link) != 1:
        raise ValueError("No se encontraron exactamente los recursos CSS y JS esperados en demo/index.html")
    if "</style" in css.lower():
        raise ValueError("El CSS contiene un cierre de style que requiere escape manual")
    if "</script" in js.lower():
        raise ValueError("El JavaScript contiene un cierre de script que requiere escape manual")

    html = html.replace(css_link, f"<style>\n{css}\n</style>")
    html = html.replace(script_link, f"<script>\n{js}\n</script>")
    if "styles.css" in html or 'src="app.js"' in html:
        raise ValueError("El documento todavía referencia archivos externos")
    return html


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("dist/consumo-residencial.html"),
        help="archivo HTML autónomo de salida (predeterminado: dist/consumo-residencial.html)",
    )
    args = parser.parse_args()
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build_html(), encoding="utf-8")
    print(f"HTML autónomo escrito: {output} ({output.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
