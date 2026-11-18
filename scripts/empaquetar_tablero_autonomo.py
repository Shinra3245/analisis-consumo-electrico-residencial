#!/usr/bin/env python3
"""Genera un HTML autónomo del tablero y sus tablas Gold para S3 privado/presigned.

No descarga ni modifica las entradas. Valida cada byte y SHA-256 contra manifest.json.
El archivo resultante incluye CSS, módulos JavaScript y los JSON Gold del directorio indicado.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def safe_inline_json(value):
    # Evita que texto contenido en los datos cierre accidentalmente el elemento script.
    return (json.dumps(value, ensure_ascii=False, separators=(",", ":"))
            .replace("<", "\\u003c").replace(">", "\\u003e")
            .replace("&", "\\u0026").replace("\u2028", "\\u2028")
            .replace("\u2029", "\\u2029"))


def build(web, data, output):
    web, data, output = web.resolve(), data.resolve(), output.resolve()
    if not (web / "index.html").is_file() or not (data / "manifest.json").is_file():
        raise SystemExit("Se requieren index.html y manifest.json en las rutas indicadas.")
    manifest_raw = (data / "manifest.json").read_bytes()
    manifest = json.loads(manifest_raw)
    if str(manifest.get("schema_version", manifest.get("manifest_version", ""))) != "1.0":
        raise SystemExit("El manifiesto Gold debe usar el esquema 1.0.")

    files = {"manifest.json": manifest_raw.decode("utf-8")}
    for table, entry in manifest.get("tables", {}).items():
        rel = Path(entry["file"])
        if rel.is_absolute() or ".." in rel.parts:
            raise SystemExit(f"Ruta inválida en el manifiesto: {table}")
        raw = (data / rel).read_bytes()
        if len(raw) != entry.get("bytes") or sha256(raw) != entry.get("sha256"):
            raise SystemExit(f"Integridad fallida: {table}")
        rows = json.loads(raw)
        if not isinstance(rows, list) or len(rows) != entry.get("rows"):
            raise SystemExit(f"Conteo/formato inválido: {table}")
        files[rel.as_posix()] = raw.decode("utf-8")

    html = (web / "index.html").read_text(encoding="utf-8")
    css = (web / "css/styles.css").read_text(encoding="utf-8")
    js_files = ["js/config.js", "js/data.js", "js/charts.js", "js/iso.js", "js/main.js"]
    js = "\n".join((web / name).read_text(encoding="utf-8") for name in js_files)
    js = re.sub(r"^\s*import\s+.*?;\s*$", "", js, flags=re.M)
    js = re.sub(r"\bexport\s+(?=(?:(?:async\s+)?function|const|let|var|class)\b)", "", js)
    if re.search(r"^\s*(?:import|export)\s", js, flags=re.M):
        raise SystemExit("Quedó una declaración de módulo sin resolver.")

    css_link = re.compile(r'<link\s+rel="stylesheet"\s+href="css/styles\.css"\s*>', re.I)
    script_tag = re.compile(r'<script\s+type="module"\s+src="js/main\.js"\s*>\s*</script>', re.I)
    html, n_css = css_link.subn(lambda _: "<style>\n" + css + "\n</style>", html, count=1)
    payload = ("<script>window.__GOLD_DATA_BUNDLE__=" + safe_inline_json(files) + ";"
               "const __goldFetch=window.fetch.bind(window);window.fetch=async(input,init)=>{"
               "const u=new URL(typeof input==='string'?input:input.url,location.href);"
               "const key=decodeURIComponent(u.pathname.split('/').pop());"
               "const raw=window.__GOLD_DATA_BUNDLE__[key];"
               "return raw===undefined?__goldFetch(input,init):new Response(raw,{status:200,"
               "headers:{'Content-Type':key.endsWith('.json')?'application/json':'text/plain'}});};"
               "</script>\n")
    inline = payload + "<script type=\"module\">\n" + js + "\n</script>"
    html, n_js = script_tag.subn(lambda _: inline, html, count=1)
    if n_css != 1 or n_js != 1:
        raise SystemExit("No se encontraron los enlaces CSS/JS esperados en index.html.")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    print(json.dumps({"output": str(output), "bytes": output.stat().st_size,
                      "tables": len(manifest["tables"]), "rows": sum(e["rows"] for e in manifest["tables"].values()),
                      "sha256": sha256(output.read_bytes())}, indent=2, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--web", type=Path, default=ROOT / "tablero")
    ap.add_argument("--datos", type=Path, default=ROOT / "tablero/data/v1")
    ap.add_argument("--salida", type=Path, default=Path("/tmp/consumo-residencial-autonomo.html"))
    a = ap.parse_args()
    build(a.web, a.datos, a.salida)


if __name__ == "__main__":
    main()
