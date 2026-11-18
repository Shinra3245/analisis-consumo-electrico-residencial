#!/usr/bin/env python3
"""Publica salidas de analitica como tablas JSON Gold para el tablero.

Valida el manifiesto del directorio Gold base, transforma las salidas reproducibles
del analizador de EIA y construye un directorio nuevo, sin sobrescribir datos.
"""
import argparse
import csv
import hashlib
import json
import math
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE = ROOT / "tablero/data/v1"
DEFAULT_ANALYTICS = Path("/tmp/analitica-dashboard-final")
DEFAULT_OUTPUT = Path("/tmp/tablero-data-integrado")


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def num(row, key):
    return float(row[key])


def dump_rows(path, rows):
    path.write_text(json.dumps(rows, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


def base_manifest(base):
    p = base / "manifest.json"
    manifest = json.loads(p.read_text(encoding="utf-8"))
    if str(manifest.get("schema_version", manifest.get("manifest_version", ""))) != "1.0":
        raise ValueError("El manifiesto base debe declarar esquema 1.0.")
    for name, entry in manifest.get("tables", {}).items():
        path = base / entry["file"]
        if not path.is_file():
            raise ValueError(f"Falta tabla base: {path}")
        if path.stat().st_size != entry.get("bytes") or sha256(path) != entry.get("sha256"):
            raise ValueError(f"Hash/tamaño no coincide con manifiesto base: {name}")
    return manifest


def build(analytics, base, output):
    analytics = analytics.resolve()
    base = base.resolve()
    output = output.resolve()
    if output.exists():
        raise ValueError(f"La salida ya existe; usa una carpeta nueva: {output}")
    summary_path = analytics / "resumen.json"
    required = ["candidatos_estadisticos.csv", "evaluacion_sintetica.csv",
                "forecast_metricas_por_estado.csv", "forecast_serie.csv"]
    if not summary_path.is_file() or any(not (analytics / n).is_file() for n in required):
        raise ValueError("Faltan salidas del analizador en " + str(analytics))

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if not summary.get("forecast", {}).get("suficiente"):
        raise ValueError("El backtest no tiene datos suficientes; no se exporta una vista vacía.")
    manifest = base_manifest(base)
    candidates_in = read_csv(analytics / "candidatos_estadisticos.csv")
    synthetic_in = read_csv(analytics / "evaluacion_sintetica.csv")
    forecast_metrics_in = read_csv(analytics / "forecast_metricas_por_estado.csv")
    forecast_series_in = read_csv(analytics / "forecast_serie.csv")

    candidates = [{
        "period": r["fecha"], "state_code": r["estado"],
        "yoy_change_pct": (math.exp(num(r, "yoy")) - 1) * 100,
        "season": r["estacion"], "robust_z": num(r, "z_robusto"),
        "partition": r["particion"], "classification": "statistical_candidate",
    } for r in candidates_in]
    synthetic = [{
        "injection_pct": num(r, "magnitud_inyectada") * 100,
        "k_mad": num(r, "k_mad"), "tp": int(r["tp"]), "fn": int(r["fn"]),
        "fp": int(r["fp"]), "tn": int(r["tn"]),
        "recall": num(r, "recall"), "precision": num(r, "precision"),
        "false_positive_rate": num(r, "tasa_falsos_positivos"),
        "evaluation_scope": "synthetic_injection",
    } for r in synthetic_in]
    forecast_metrics = [{
        "state_code": r["estado"],
        "naive_mae_mwh": num(r, "naive_MAE"), "naive_rmse_mwh": num(r, "naive_RMSE"),
        "naive_smape_pct": num(r, "naive_sMAPE"),
        "model_mae_mwh": num(r, "modelo_MAE"), "model_rmse_mwh": num(r, "modelo_RMSE"),
        "model_smape_pct": num(r, "modelo_sMAPE"),
        "model_smape_improvement_pct": num(r, "mejora_smape_pct"),
    } for r in forecast_metrics_in]
    forecast_series = [{
        "state_code": r["estado"], "period": r["period"],
        "actual_mwh": num(r, "real_mwh"), "naive_mwh": num(r, "naive_mwh"),
        "model_mwh": num(r, "modelo_mwh"), "partition": r["particion"],
    } for r in forecast_series_in]
    expected_fc = summary["forecast"]
    periods = sorted({r["period"] for r in forecast_series})
    states = {r["state_code"] for r in forecast_series}
    if len(forecast_metrics) != 51 or len(states) != 51 or len(periods) != 24 or len(forecast_series) != 1224:
        raise ValueError("Cobertura forecast inesperada; se esperan 51 estados x 24 meses = 1224 filas.")
    if periods[0] != "2024-01" or periods[-1] != "2025-12":
        raise ValueError("El holdout forecast no coincide con 2024-01..2025-12.")

    analytics_tables = {
        "gold_anomaly_candidates": ("gold_anomaly_candidates.json", candidates,
                                     ["state_code", "period", "season"], "eia"),
        "gold_anomaly_synthetic_eval": ("gold_anomaly_synthetic_eval.json", synthetic,
                                         ["injection_pct"], "eia"),
        "gold_forecast_metrics": ("gold_forecast_metrics.json", forecast_metrics,
                                  ["state_code"], "eia"),
        "gold_forecast_series": ("gold_forecast_series.json", forecast_series,
                                 ["state_code", "period"], "eia"),
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}-", dir=output.parent))
    try:
        for entry in manifest["tables"].values():
            shutil.copy2(base / entry["file"], staging / entry["file"])
        for name, (filename, rows, primary_key, source) in analytics_tables.items():
            path = staging / filename
            dump_rows(path, rows)
            manifest["tables"][name] = {
                "file": filename, "rows": len(rows), "bytes": path.stat().st_size,
                "sha256": sha256(path), "primary_key": primary_key,
                "source": source, "inputs": ["datos/eia_residencial_mensual.csv", "resumen.json"],
            }
        manifest["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
        manifest["analytics_status"] = "VALID_WITH_WARNINGS"
        manifest["analytics"] = {
            "source": "EIA-861M monthly residential sales",
            "anomaly_method": "per-state year-over-year log change with seasonal median/MAD bounds; k=3.5",
            "anomaly_real_events_verified": False,
            "synthetic_metrics_only": True,
            "anomaly_counts": summary["anomalias_reales"],
            "forecast": {
                "type": "temporal holdout backtest, not future projection",
                "training": expected_fc["periodo_entrenamiento"],
                "holdout": expected_fc["periodo_prueba"],
                "median_naive_smape_pct": expected_fc["sMAPE_mediana_naive"],
                "median_model_smape_pct": expected_fc["sMAPE_mediana_modelo"],
                "states_model_beats_naive": expected_fc["estados_donde_modelo_supera_naive_sMAPE"],
                "state_count": expected_fc["n_estados"],
            },
        }
        (staging / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(staging, output)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    print(json.dumps({"output": str(output), "tables": {n: {"rows": len(v[1]), "file": v[0]} for n, v in analytics_tables.items()},
                      "forecast_periods": [periods[0], periods[-1]], "states": len(states)}, indent=2))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--analitica", type=Path, default=DEFAULT_ANALYTICS)
    ap.add_argument("--base", type=Path, default=DEFAULT_BASE)
    ap.add_argument("--salida", type=Path, default=DEFAULT_OUTPUT)
    a = ap.parse_args()
    build(a.analitica, a.base, a.salida)


if __name__ == "__main__":
    main()
