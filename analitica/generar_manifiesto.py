#!/usr/bin/env python3
"""Genera analitica/salidas/manifiesto-gold.json: archivos gold, filas, bytes, SHA-256 y entradas usadas.

Uso (después de ejecutar pronostico_eia.py y anomalias_resstock.py):
    python analitica/generar_manifiesto.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

SCHEMA_VERSION = "1.0"

# archivo gold -> (script que lo produce, archivos de entrada en datos/, source_dataset_id)
LINEAGE = {
    "gold_eia_monthly.csv":               ("pronostico_eia.py",      ["eia_residencial_mensual.csv"], "eia861m_sales_monthly"),
    "gold_forecast_monthly.csv":          ("pronostico_eia.py",      ["eia_residencial_mensual.csv"], "eia861m_sales_monthly"),
    "gold_forecast_annual.csv":           ("pronostico_eia.py",      ["eia_residencial_mensual.csv"], "eia861m_sales_monthly"),
    "gold_forecast_metrics.csv":          ("pronostico_eia.py",      ["eia_residencial_mensual.csv"], "eia861m_sales_monthly"),
    "gold_resstock_profile_summary.csv":  ("anomalias_resstock.py",  ["resstock_perfiles_piloto.parquet", "resstock_seleccion_propuesta.csv"], "resstock_2025r1_amy2018_upgrade0"),
    "gold_resstock_monthly.csv":          ("anomalias_resstock.py",  ["resstock_perfiles_piloto.parquet", "resstock_seleccion_propuesta.csv"], "resstock_2025r1_amy2018_upgrade0"),
    "gold_resstock_pattern.csv":          ("anomalias_resstock.py",  ["resstock_perfiles_piloto.parquet", "resstock_seleccion_propuesta.csv"], "resstock_2025r1_amy2018_upgrade0"),
    "gold_anomaly_metrics.csv":           ("anomalias_resstock.py",  ["resstock_perfiles_piloto.parquet", "resstock_seleccion_propuesta.csv"], "resstock_2025r1_amy2018_upgrade0 (+eventos sintéticos)"),
    "gold_anomaly_sensitivity.csv":       ("anomalias_resstock.py",  ["resstock_perfiles_piloto.parquet", "resstock_seleccion_propuesta.csv"], "resstock_2025r1_amy2018_upgrade0 (+eventos sintéticos)"),
    "gold_anomaly_cases.csv":             ("anomalias_resstock.py",  ["resstock_perfiles_piloto.parquet", "resstock_seleccion_propuesta.csv"], "resstock_2025r1_amy2018_upgrade0 (+eventos sintéticos)"),
    "gold_anomaly_case_series.csv":       ("anomalias_resstock.py",  ["resstock_perfiles_piloto.parquet", "resstock_seleccion_propuesta.csv"], "resstock_2025r1_amy2018_upgrade0 (+eventos sintéticos)"),
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_version(root: Path) -> str:
    try:
        return subprocess.check_output(["git", "-C", str(root), "rev-parse", "--short", "HEAD"],
                                       text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "unversioned"


def main(root: Path) -> None:
    out = root / "analitica" / "salidas"
    datos = root / "datos"
    declared = {a["file"]: a["sha256"]
                for a in json.loads((datos / "manifiesto-integracion.json").read_text())["artifacts"]}
    inputs_cache, warnings = {}, []
    for name in {i for v in LINEAGE.values() for i in v[1]}:
        actual = sha256(datos / name)
        inputs_cache[name] = actual
        if declared.get(name) != actual:
            warnings.append(f"El SHA-256 de datos/{name} no coincide con manifiesto-integracion.json")

    transform = git_version(root)
    artifacts = []
    for name, (script, inputs, dsid) in LINEAGE.items():
        p = out / name
        if not p.exists():
            raise SystemExit(f"Falta {p}. Ejecuta primero pronostico_eia.py y anomalias_resstock.py.")
        df = pd.read_csv(p)
        artifacts.append({
            "file": name, "format": "csv", "rows": int(len(df)), "bytes": p.stat().st_size,
            "sha256": sha256(p), "columns": list(df.columns),
            "produced_by": f"analitica/{script}", "source_dataset_id": dsid,
            "inputs": [{"file": f"datos/{i}", "sha256": inputs_cache[i]} for i in inputs],
        })
    manifest = {
        "manifest_version": "1.0", "schema_version": SCHEMA_VERSION, "transform_version": transform,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "notes": [
            "Salidas derivadas. Cada tabla conserva la fuente separada: ResStock (modelado), EIA (ventas oficiales) y clima.",
            "Las métricas de anomalías usan eventos SINTÉTICOS; no son eventos reales del sistema eléctrico.",
            "Los timestamps de ResStock están en EST fijo (no hora local).",
        ],
        "warnings": warnings, "artifacts": artifacts,
    }
    (out / "manifiesto-gold.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"Manifiesto escrito: {len(artifacts)} archivos. Avisos: {warnings or 'ninguno'}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    main(ap.parse_args().root)
