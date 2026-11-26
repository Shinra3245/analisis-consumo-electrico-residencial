#!/usr/bin/env python3
"""Generador reproducible de datos Gold para el tablero web (v1).

Lee los artefactos de datos versionados en datos/, valida hashes contra
datos/manifiesto-integracion.json, ejecuta 21 controles de calidad formales,
realiza las transformaciones canónicas requeridas por el contrato v1 y
exporta los datasets en formato JSON bajo tablero/data/v1/:
  - gold_eia_monthly.json (5,304 filas)
  - gold_resstock_monthly.json (120 filas)
  - gold_resstock_pattern.json (6,730 filas)
  - gold_resstock_pattern_aggregate.json (6,730 filas en muestra piloto; cota fija por estrato al escalar)
  - gold_resstock_profile_summary.json (10 filas)
  - gold_climate.json (336 filas)
  - manifest.json (manifiesto con hashes, esquema 1.0, QC, linaje y bloqueo 87.16%)

Manejo temporal:
  - Timestamps ResStock de origen están en EST fijo (UTC-5), sin DST.
  - Para gold_resstock_monthly: inicio de intervalo derivado restando 15 min a marca de fin.
  - Para gold_resstock_pattern y gold_resstock_pattern_aggregate: se calcula inicio de intervalo,
    se convierte explícitamente a UTC (+5 horas) y luego a la zona IANA del estado
    (America/Denver para CO, America/New_York para NY). Se preserva utc_offset_minutes
    para distinguir horas en DST y se marcan periodos locales parciales (2017-12 y 2018-12 en CO).
  - El agregado por estrato distingue (state_code, housing_type, period_local, day_type,
    hour_local, utc_offset_minutes) para mantener acotado el volumen en el navegador
    cuando la muestra N escale hacia 10,000 perfiles, manteniendo a la vez la inspección
    individual en gold_resstock_pattern.
  - La relación 87.16% Colorado/EIA queda documentada como no reproducida debido a la
    ausencia del agregado crudo en el repositorio, sin inventar datos sustitutos.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
import os
import shutil
import sys
import tempfile
from typing import Any, Dict, List, Tuple

import pandas as pd
import pyarrow.parquet as pq

PREVIOUS_EXPECTED_FILES = {
    "gold_eia_monthly.json",
    "gold_resstock_monthly.json",
    "gold_resstock_pattern.json",
    "gold_resstock_profile_summary.json",
    "gold_climate.json",
    "manifest.json",
}

EXPECTED_OUTPUT_FILES = PREVIOUS_EXPECTED_FILES | {
    "gold_resstock_pattern_aggregate.json",
}

EXPECTED_OUTPUT_FILES_V2 = EXPECTED_OUTPUT_FILES | {
    "gold_demography_state_year.json",
    "gold_anomaly_candidates.json",
    "gold_anomaly_synthetic_eval.json",
    "gold_forecast_metrics.json",
    "gold_forecast_series.json",
}


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Genera datos Gold reproducibles para el tablero web (v1/v2)."
    )
    parser.add_argument(
        "--input",
        type=str,
        default="datos",
        help="Directorio con los datos de entrada base (default: datos).",
    )
    parser.add_argument(
        "--demografia-input",
        type=str,
        default="datos/demografia_estatal",
        help="Directorio con los datos demográficos canónicos (default: datos/demografia_estatal).",
    )
    parser.add_argument(
        "--v1-base",
        type=str,
        default="tablero/data/v1",
        help="Directorio de datos v1 para conservar tablas analíticas en v2 (default: tablero/data/v1).",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="tablero/data/v1",
        help="Directorio destino para los JSON y manifest.json (default: tablero/data/v1).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Permite reemplazar atómicamente un directorio de salida existente.",
    )
    return parser.parse_args()


def validate_paths(input_dir: str, output_dir: str, overwrite: bool) -> Tuple[str, str]:
    """Valida que la salida no pueda reemplazar la fuente ni una ruta amplia."""
    real_input = os.path.realpath(input_dir)
    if not os.path.isdir(real_input):
        raise FileNotFoundError(f"El directorio de entrada no existe: {real_input}")

    if os.path.islink(output_dir):
        raise ValueError(f"La salida no puede ser un enlace simbólico: {output_dir}")
    real_output = os.path.realpath(output_dir)
    if real_output in {os.path.abspath(os.sep), os.path.realpath(os.path.expanduser("~"))}:
        raise ValueError(f"Ruta de salida protegida: {real_output}")

    try:
        common = os.path.commonpath([real_input, real_output])
    except ValueError:
        common = None
    if common in {real_input, real_output}:
        raise ValueError(
            f"La salida ({real_output}) y la entrada ({real_input}) no pueden solaparse ni contenerse."
        )

    if os.path.exists(real_output):
        if not os.path.isdir(real_output):
            raise ValueError(f"La ruta de salida existe y no es un directorio: {real_output}")
        if not overwrite:
            raise ValueError(
                f"La salida ya existe: {real_output}. Usa --overwrite para reemplazarla explícitamente."
            )
        manifest_path = os.path.join(real_output, "manifest.json")
        try:
            with open(manifest_path, encoding="utf-8") as f:
                manifest = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(
                "--overwrite solo reemplaza una salida previa reconocible del exportador; "
                f"no se pudo validar {manifest_path}."
            ) from exc
        actual_files = set(os.listdir(real_output)) - {".gitkeep"}
        if (
            manifest.get("schema_version") not in ("1.0", "2.0")
            or manifest.get("generator_script") != "scripts/generar_datos_tablero.py"
            or actual_files not in (PREVIOUS_EXPECTED_FILES, EXPECTED_OUTPUT_FILES, EXPECTED_OUTPUT_FILES_V2)
        ):
            raise ValueError(
                "--overwrite solo reemplaza una exportación Gold reconocida sin archivos adicionales; "
                f"salida protegida: {real_output}"
            )
    return real_input, real_output


def publish_staging(staging_dir: str, output_dir: str, overwrite: bool) -> None:
    """Publica el staging y restaura la salida anterior si el cambio falla."""
    if not os.path.exists(output_dir):
        os.replace(staging_dir, output_dir)
        return
    if not overwrite:
        raise ValueError(f"La salida ya existe: {output_dir}; se requiere --overwrite.")

    parent_dir = os.path.dirname(output_dir)
    backup_dir = tempfile.mkdtemp(prefix=".tablero_v1_backup_", dir=parent_dir)
    os.rmdir(backup_dir)
    os.replace(output_dir, backup_dir)
    try:
        os.replace(staging_dir, output_dir)
    except Exception:
        os.replace(backup_dir, output_dir)
        raise
    shutil.rmtree(backup_dir)


def verify_demography_source(demografia_dir: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Verifica tamaño y SHA-256 del CSV canónico demográfico contra su manifest.json."""
    manifest_path = os.path.join(demografia_dir, "manifest.json")
    if not os.path.exists(manifest_path):
        raise FileNotFoundError(f"No se encontró el manifiesto demográfico: {manifest_path}")

    with open(manifest_path, encoding="utf-8") as f:
        meta = json.load(f)

    art = meta.get("artifact", {})
    filename = art.get("file", "energy_demography_state_year_v1.csv")
    csv_path = os.path.join(demografia_dir, filename)
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"No se encontró el CSV demográfico: {csv_path}")

    digest = hashlib.sha256()
    size_bytes = 0
    with open(csv_path, "rb") as f_in:
        for chunk in iter(lambda: f_in.read(1024 * 1024), b""):
            digest.update(chunk)
            size_bytes += len(chunk)
    actual_sha = digest.hexdigest()

    expected_sha = art.get("sha256")
    expected_bytes = art.get("bytes")
    if actual_sha != expected_sha or size_bytes != expected_bytes:
        raise ValueError(
            f"Integridad violada en demografía {filename}: tamaño={size_bytes} (esperado {expected_bytes}), "
            f"sha256={actual_sha} (esperado {expected_sha})"
        )

    sources_inventory = []
    for src_key, src_val in meta.get("sources", {}).items():
        sources_inventory.append({
            "source_category": src_key,
            "file": src_val.get("file"),
            "version": src_val.get("version"),
            "url": src_val.get("url") or src_val.get("upstream_url"),
            "sha256": src_val.get("sha256"),
            "bytes": src_val.get("bytes"),
        })

    return meta, sources_inventory


def generate_gold_demography_state_year(csv_path: str) -> List[Dict[str, Any]]:
    """Transforma el CSV canónico demográfico a formato JSON Gold con tipos validados."""
    records = []
    with open(csv_path, mode="r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            records.append({
                "state_fips": str(r["state_fips"]).zfill(2),
                "state_code": str(r["state_code"]),
                "year": int(r["year"]),
                "population_estimate": int(r["population_estimate"]),
                "land_area_sq_mi_2020": round(float(r["land_area_sq_mi_2020"]), 6),
                "population_density_per_sq_mi": round(float(r["population_density_per_sq_mi"]), 6),
                "residential_sales_mwh": round(float(r["residential_sales_mwh"]), 2),
                "residential_kwh_per_capita": round(float(r["residential_kwh_per_capita"]), 6),
                "eia_data_status": str(r["eia_data_status"]),
                "census_vintage": int(r["census_vintage"]),
                "source_version": str(r["source_version"]),
            })
    return records


def run_demography_qc(records: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
    """Ejecuta los 6 controles formales de calidad sobre la tabla demográfica estatal."""
    rules_results = []

    n = len(records)
    r1 = bool(n == 306)
    rules_results.append({
        "fuente": "demografia",
        "regla": "conteos_totales_esperados",
        "condicion": "filas == 306 (51 jurisdicciones x 6 años 2020-2025)",
        "cumplida": r1,
        "fallos": 0 if r1 else abs(306 - n),
    })

    keys = [(r["state_fips"], r["year"]) for r in records]
    dup_pks = len(keys) - len(set(keys))
    r2 = bool(dup_pks == 0)
    rules_results.append({
        "fuente": "demografia",
        "regla": "unicidad_clave_primaria",
        "condicion": "tupla (state_fips, year) sin duplicados",
        "cumplida": r2,
        "fallos": dup_pks,
    })

    by_year = {}
    for r in records:
        by_year.setdefault(r["year"], set()).add(r["state_code"])
    expected_years = {2020, 2021, 2022, 2023, 2024, 2025}
    r3 = bool(set(by_year.keys()) == expected_years and all(len(v) == 51 for v in by_year.values()))
    rules_results.append({
        "fuente": "demografia",
        "regla": "cobertura_geografica_anual_completa",
        "condicion": "51 jurisdicciones (50 estados + DC) presentes en cada año 2020-2025",
        "cumplida": r3,
        "fallos": 0 if r3 else 1,
    })

    pos_bad = sum(
        1 for r in records
        if r["population_estimate"] <= 0
        or r["land_area_sq_mi_2020"] <= 0
        or r["residential_sales_mwh"] <= 0
        or r["population_density_per_sq_mi"] <= 0
        or r["residential_kwh_per_capita"] <= 0
    )
    r4 = bool(pos_bad == 0)
    rules_results.append({
        "fuente": "demografia",
        "regla": "positividad_de_indicadores",
        "condicion": "population, land_area, sales_mwh, density y kwh_per_capita estrictamente positivos",
        "cumplida": r4,
        "fallos": pos_bad,
    })

    meta_bad = sum(
        1 for r in records
        if r["eia_data_status"] != "Final" or r["census_vintage"] != 2025
    )
    r5 = bool(meta_bad == 0)
    rules_results.append({
        "fuente": "demografia",
        "regla": "consistencia_fuentes_y_vintage",
        "condicion": "eia_data_status == 'Final' y census_vintage == 2025 en todas las filas",
        "cumplida": r5,
        "fallos": meta_bad,
    })

    dc_recs = [r for r in records if r.get("state_code") == "DC"]
    expected_years = {2020, 2021, 2022, 2023, 2024, 2025}
    dc_ok = bool(
        len(dc_recs) == 6
        and {r.get("year") for r in dc_recs} == expected_years
        and all(str(r.get("state_fips")) == "11" for r in dc_recs)
        and all(float(r.get("population_density_per_sq_mi", 0)) > 10000 for r in dc_recs)
    )
    rules_results.append({
        "fuente": "demografia",
        "regla": "distincion_territorial_dc",
        "condicion": "DC identificado con FIPS 11, años 2020-2025 y densidad urbana atípica (>10,000 hab/mi²)",
        "cumplida": dc_ok,
        "fallos": 0 if dc_ok else 1,
    })

    failed = sum(1 for r in rules_results if not r["cumplida"])
    return rules_results, failed


def load_and_copy_analytics(v1_base_dir: str, staging_dir: str) -> Tuple[Dict[str, Any], Dict[str, Any], str]:
    """Copia las 4 tablas analíticas de v1 si están presentes para mantener todas las vistas en v2."""
    manifest_path = os.path.join(v1_base_dir, "manifest.json")
    if not os.path.exists(manifest_path):
        return {}, {}, ""

    with open(manifest_path, encoding="utf-8") as f:
        v1_manifest = json.load(f)

    analytics_tables = [
        "gold_anomaly_candidates",
        "gold_anomaly_synthetic_eval",
        "gold_forecast_metrics",
        "gold_forecast_series",
    ]

    copied_meta = {}
    v1_tables = v1_manifest.get("tables", {})
    for tname in analytics_tables:
        if tname in v1_tables:
            src_file = os.path.join(v1_base_dir, v1_tables[tname]["file"])
            dst_file = os.path.join(staging_dir, v1_tables[tname]["file"])
            if os.path.exists(src_file):
                with open(src_file, "rb") as f_in:
                    content = f_in.read()
                actual_sha = hashlib.sha256(content).hexdigest()
                expected_sha = v1_tables[tname].get("sha256")
                if expected_sha and actual_sha != expected_sha:
                    raise ValueError(f"Integridad analítica violada en {src_file}")
                with open(dst_file, "wb") as f_out:
                    f_out.write(content)
                copied_meta[tname] = dict(v1_tables[tname])

    analytics_section = v1_manifest.get("analytics", {})
    analytics_status = v1_manifest.get("analytics_status", "VALID_WITH_WARNINGS")
    return copied_meta, analytics_section, analytics_status


def verify_input_sources(input_dir: str) -> List[Dict[str, Any]]:
    """Verifica tamaño y SHA-256 de los 4 archivos contra manifiesto-integracion.json."""
    manifest_path = os.path.join(input_dir, "manifiesto-integracion.json")
    if not os.path.exists(manifest_path):
        raise FileNotFoundError(f"No se encontró el manifiesto de entrada: {manifest_path}")

    with open(manifest_path, encoding="utf-8") as f:
        meta = json.load(f)

    declared = {item["file"]: item for item in meta.get("artifacts", [])}
    required = {
        "resstock_perfiles_piloto.parquet": "resstock_2025r1_amy2018_upgrade0_pilot",
        "resstock_seleccion_propuesta.csv": "resstock_2025r1_selection_index",
        "eia_residencial_mensual.csv": "eia861m_sales_monthly",
        "clima_open_meteo_muestra.csv": "openmeteo_era5land_hourly",
    }

    inventory = []
    for filename, dataset_id in required.items():
        if filename not in declared:
            raise ValueError(f"El archivo {filename} no está en manifiesto-integracion.json")
        rec = declared[filename]
        path = os.path.join(input_dir, filename)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Archivo de entrada no existe: {path}")

        digest = hashlib.sha256()
        size_bytes = 0
        with open(path, "rb") as f_in:
            for chunk in iter(lambda: f_in.read(1024 * 1024), b""):
                digest.update(chunk)
                size_bytes += len(chunk)
        actual_sha = digest.hexdigest()

        if actual_sha != rec["sha256"] or size_bytes != rec["bytes"]:
            raise ValueError(
                f"Integridad violada en {filename}: tamaño={size_bytes} (esperado {rec['bytes']}), "
                f"sha256={actual_sha} (esperado {rec['sha256']})"
            )

        if filename == "resstock_perfiles_piloto.parquet":
            roster = rec.get("profile_roster")
            if roster and isinstance(roster, dict) and "bldg_ids" in roster:
                rs_roster_info = {
                    "source": "manifest_profile_roster",
                    "bldg_ids": sorted(roster["bldg_ids"]),
                    "expected_bldgs": len(roster["bldg_ids"]),
                    "expected_rows": len(roster["bldg_ids"]) * roster.get("intervals_per_profile", 35040),
                }
            else:
                declared_rows = rec.get("rows", 350400)
                rs_roster_info = {
                    "source": "manifest_declared_rows",
                    "bldg_ids": None,
                    "expected_bldgs": declared_rows // 35040 if declared_rows else 10,
                    "expected_rows": declared_rows,
                }

        inventory.append(
            {
                "file": filename,
                "source_dataset_id": dataset_id,
                "bytes": size_bytes,
                "sha256": actual_sha,
                "source_url": rec.get("source_url"),
                "license": rec.get("license"),
                "transform": rec.get("transform"),
            }
        )

    return inventory, rs_roster_info


def run_qc_checks(
    df_resstock: pd.DataFrame,
    df_metadata: pd.DataFrame,
    df_eia: pd.DataFrame,
    df_clima: pd.DataFrame,
    roster_info: Dict[str, Any] | None = None,
) -> Tuple[Dict[str, Any], int, List[str]]:
    """Ejecuta los 21 controles de calidad formales sobre los DataFrames de entrada."""
    rules_results = []
    warnings = [
        "Muestra meteorológica preservada en capa desacoplada sin join espacial ni temporal con perfiles de consumo.",
        "El manifiesto de integración no registra la hora UTC exacta de descarga original de las fuentes.",
        "El agregado crudo ResStock Colorado 2018 para la comparación 87.16% está ausente en origin/main; la métrica queda catalogada como no reproducida.",
    ]

    # --- 1. ResStock (7 reglas) ---
    bldgs = df_resstock["bldg_id"].unique()
    n_rows_rs = len(df_resstock)
    n_bldgs_rs = len(bldgs)

    if roster_info is None:
        roster_info = {}
    expected_bldgs = roster_info.get("expected_bldgs", n_bldgs_rs)
    expected_rows = roster_info.get("expected_rows", expected_bldgs * 35040)
    expected_ids = roster_info.get("bldg_ids")

    ids_match = (set(bldgs) == set(expected_ids)) if expected_ids is not None else True
    r1 = bool(n_rows_rs == expected_rows and n_bldgs_rs == expected_bldgs and ids_match)
    r1_cond = f"filas == {expected_rows} (N*35040) y edificios == {expected_bldgs}"
    if expected_ids is not None:
        r1_cond += " con IDs coincidentes con profile_roster"
    rules_results.append({
        "fuente": "resstock",
        "regla": "filas_y_edificios_esperados",
        "condicion": r1_cond,
        "cumplida": r1,
        "fallos": 0 if r1 else 1,
    })

    counts_by_bldg = df_resstock.groupby("bldg_id").size().to_dict()
    r2 = bool(all(c == 35040 for c in counts_by_bldg.values()) and len(counts_by_bldg) == expected_bldgs)
    rules_results.append({
        "fuente": "resstock",
        "regla": "cobertura_intervalos_anual_por_edificio",
        "condicion": f"cada bldg_id tiene exactamente 35040 intervalos de 15 min (AMY 2018) y {expected_bldgs} edificios",
        "cumplida": r2,
        "fallos": 0 if r2 else 1,
    })

    nulls_rs = int(df_resstock[["bldg_id", "timestamp_fin_local", "electricidad_kwh"]].isna().sum().sum())
    r3 = bool(nulls_rs == 0)
    rules_results.append({
        "fuente": "resstock",
        "regla": "ausencia_de_nulos",
        "condicion": "0 nulos en campos bldg_id, timestamp_fin_local y electricidad_kwh",
        "cumplida": r3,
        "fallos": nulls_rs,
    })

    invalid_energy = int(((df_resstock["electricidad_kwh"] < 0) | df_resstock["electricidad_kwh"].isna() | df_resstock["electricidad_kwh"].isin([float("inf"), float("-inf")])).sum())
    r4 = bool(invalid_energy == 0)
    rules_results.append({
        "fuente": "resstock",
        "regla": "energia_no_negativa_y_finita",
        "condicion": "electricidad_kwh >= 0.0, no nula, no NaN y no infinita",
        "cumplida": r4,
        "fallos": invalid_energy,
    })

    dup_pk_rs = int(df_resstock.duplicated(subset=["bldg_id", "timestamp_fin_local"]).sum())
    r5 = bool(dup_pk_rs == 0)
    rules_results.append({
        "fuente": "resstock",
        "regla": "unicidad_clave_primaria",
        "condicion": "par (bldg_id, timestamp_fin_local) sin duplicados",
        "cumplida": r5,
        "fallos": dup_pk_rs,
    })

    # Continuidad temporal 900s y límites
    df_rs_sorted = df_resstock.sort_values(["bldg_id", "timestamp_fin_local"])
    diffs = df_rs_sorted.groupby("bldg_id")["timestamp_fin_local"].diff().dropna()
    invalid_steps = int((diffs != pd.Timedelta(seconds=900)).sum())
    min_ts = df_resstock.groupby("bldg_id")["timestamp_fin_local"].min()
    max_ts = df_resstock.groupby("bldg_id")["timestamp_fin_local"].max()
    limits_ok = bool(
        (min_ts == pd.Timestamp("2018-01-01 00:15:00")).all()
        and (max_ts == pd.Timestamp("2019-01-01 00:00:00")).all()
    )
    r6 = bool(invalid_steps == 0 and limits_ok)
    rules_results.append({
        "fuente": "resstock",
        "regla": "continuidad_y_paso_15min_estricto",
        "condicion": "pasos consecutivos de exactamente 900s e inicio 2018-01-01 00:15 / fin 2019-01-01 00:00 por edificio",
        "cumplida": r6,
        "fallos": invalid_steps + (0 if limits_ok else 1),
    })

    meta_pilot = df_metadata[df_metadata["bldg_id"].isin(bldgs)]
    meta_valid = (
        len(meta_pilot) == n_bldgs_rs
        and meta_pilot["bldg_id"].nunique() == n_bldgs_rs
        and meta_pilot["estado"].str.match(r"^[A-Z]{2}$").all()
        and (meta_pilot["peso_viviendas"] > 0).all()
        and not meta_pilot[["tipo_vivienda", "condado_codigo", "upgrade", "url"]].isna().any().any()
    )
    r7 = bool(meta_valid)
    rules_results.append({
        "fuente": "resstock",
        "regla": "metadata_resstock_completa_y_univoca",
        "condicion": f"cada uno de los {n_bldgs_rs} perfiles tiene una fila válida en resstock_seleccion_propuesta.csv",
        "cumplida": r7,
        "fallos": 0 if r7 else 1,
    })

    # --- 2. EIA (7 reglas) ---
    n_rows_eia = len(df_eia)
    n_states_eia = df_eia["estado"].nunique()
    r8 = bool(n_rows_eia == 5304 and n_states_eia == 51)
    rules_results.append({
        "fuente": "eia",
        "regla": "conteos_totales_esperados",
        "condicion": "filas == 5304 y estados == 51 (50 estados + DC)",
        "cumplida": r8,
        "fallos": 0 if r8 else 1,
    })

    nulls_eia = int(df_eia[["periodo", "estado", "sector", "estado_dato", "ventas_mwh"]].isna().sum().sum())
    r9 = bool(nulls_eia == 0)
    rules_results.append({
        "fuente": "eia",
        "regla": "ausencia_de_nulos_en_esquema",
        "condicion": "0 nulos en todas las columnas (periodo, estado, sector, estado_dato, ventas_mwh)",
        "cumplida": r9,
        "fallos": nulls_eia,
    })

    valid_period = df_eia["periodo"].str.match(r"^[0-9]{4}-(0[1-9]|1[0-2])$").all()
    r10 = bool(valid_period)
    rules_results.append({
        "fuente": "eia",
        "regla": "formato_periodo_y_mes_valido",
        "condicion": "periodo cumple regex ^[0-9]{4}-(0[1-9]|1[0-2])$",
        "cumplida": r10,
        "fallos": 0 if r10 else 1,
    })

    res_only = (df_eia["sector"] == "RES").all()
    r11 = bool(res_only)
    rules_results.append({
        "fuente": "eia",
        "regla": "sector_exclusivo_residencial",
        "condicion": "sector == 'RES' en todas las filas",
        "cumplida": r11,
        "fallos": 0 if r11 else 1,
    })

    valid_status = df_eia["estado_dato"].isin(["Final", "Preliminary"]).all()
    r12 = bool(valid_status)
    rules_results.append({
        "fuente": "eia",
        "regla": "estado_dato_valido",
        "condicion": "estado_dato pertenece a {'Final', 'Preliminary'}",
        "cumplida": r12,
        "fallos": 0 if r12 else 1,
    })

    invalid_sales = int(((df_eia["ventas_mwh"] < 0) | df_eia["ventas_mwh"].isna() | df_eia["ventas_mwh"].isin([float("inf"), float("-inf")])).sum())
    r13 = bool(invalid_sales == 0)
    rules_results.append({
        "fuente": "eia",
        "regla": "ventas_no_negativas_y_finitas",
        "condicion": "ventas_mwh >= 0.0, no nulo, no NaN y no infinito",
        "cumplida": r13,
        "fallos": invalid_sales,
    })

    dup_pk_eia = int(df_eia.duplicated(subset=["periodo", "estado", "sector"]).sum())
    r14 = bool(dup_pk_eia == 0)
    rules_results.append({
        "fuente": "eia",
        "regla": "unicidad_clave_primaria",
        "condicion": "tupla (periodo, estado, sector) sin duplicados",
        "cumplida": r14,
        "fallos": dup_pk_eia,
    })

    # --- 3. Clima (7 reglas) ---
    n_rows_clima = len(df_clima)
    n_pts_clima = df_clima["punto_id"].nunique()
    counts_by_pt = df_clima.groupby("punto_id").size().to_dict()
    r15 = bool(n_rows_clima == 336 and n_pts_clima == 2 and all(c == 168 for c in counts_by_pt.values()))
    rules_results.append({
        "fuente": "clima",
        "regla": "conteos_totales_y_puntos_esperados",
        "condicion": "filas == 336 y puntos == 2 (168 h por punto, 7 días)",
        "cumplida": r15,
        "fallos": 0 if r15 else 1,
    })

    nulls_clima = int(df_clima.isna().sum().sum())
    r16 = bool(nulls_clima == 0)
    rules_results.append({
        "fuente": "clima",
        "regla": "ausencia_de_nulos_en_esquema",
        "condicion": "0 nulos en todas las columnas de la muestra de clima",
        "cumplida": r16,
        "fallos": nulls_clima,
    })

    valid_model = (df_clima["modelo"] == "ERA5-Land").all()
    r17 = bool(valid_model)
    rules_results.append({
        "fuente": "clima",
        "regla": "modelo_meteorologico_declarado",
        "condicion": "modelo == 'ERA5-Land'",
        "cumplida": r17,
        "fallos": 0 if r17 else 1,
    })

    temp_valid = int(((df_clima["temperatura_c"] < -60.0) | (df_clima["temperatura_c"] > 60.0) | df_clima["temperatura_c"].isna()).sum())
    r18 = bool(temp_valid == 0)
    rules_results.append({
        "fuente": "clima",
        "regla": "rango_fisico_temperatura",
        "condicion": "-60.0 <= temperatura_c <= 60.0, no nula y finita",
        "cumplida": r18,
        "fallos": temp_valid,
    })

    coords_valid = (
        (df_clima["latitude_solicitada"] >= -90.0) & (df_clima["latitude_solicitada"] <= 90.0)
        & (df_clima["latitude_celda"] >= -90.0) & (df_clima["latitude_celda"] <= 90.0)
        & (df_clima["longitude_solicitada"] >= -180.0) & (df_clima["longitude_solicitada"] <= 180.0)
        & (df_clima["longitude_celda"] >= -180.0) & (df_clima["longitude_celda"] <= 180.0)
    ).all()
    r19 = bool(coords_valid)
    rules_results.append({
        "fuente": "clima",
        "regla": "coordenadas_completas_y_en_rango",
        "condicion": "latitudes [-90, 90] y longitudes [-180, 180] presentes, no nulas y finitas",
        "cumplida": r19,
        "fallos": 0 if r19 else 1,
    })

    dup_pk_clima = int(df_clima.duplicated(subset=["punto_id", "timestamp_utc"]).sum())
    r20 = bool(dup_pk_clima == 0)
    rules_results.append({
        "fuente": "clima",
        "regla": "unicidad_clave_primaria",
        "condicion": "tupla (punto_id, timestamp_utc) sin duplicados",
        "cumplida": r20,
        "fallos": dup_pk_clima,
    })

    # Continuidad temporal horaria 3600s
    df_clima_sorted = df_clima.copy()
    df_clima_sorted["ts_dt"] = pd.to_datetime(df_clima_sorted["timestamp_utc"])
    df_clima_sorted = df_clima_sorted.sort_values(["punto_id", "ts_dt"])
    diffs_clima = df_clima_sorted.groupby("punto_id")["ts_dt"].diff().dropna()
    invalid_steps_clima = int((diffs_clima != pd.Timedelta(seconds=3600)).sum())
    min_clima = df_clima_sorted.groupby("punto_id")["ts_dt"].min()
    max_clima = df_clima_sorted.groupby("punto_id")["ts_dt"].max()
    limits_clima_ok = bool(
        (min_clima == pd.Timestamp("2018-01-01 00:00:00Z")).all()
        and (max_clima == pd.Timestamp("2018-01-07 23:00:00Z")).all()
    )
    r21 = bool(invalid_steps_clima == 0 and limits_clima_ok)
    rules_results.append({
        "fuente": "clima",
        "regla": "continuidad_temporal_horaria_168h",
        "condicion": "pasos consecutivos de exactamente 3600s e inicio 2018-01-01 00:00Z / fin 2018-01-07 23:00Z por punto",
        "cumplida": r21,
        "fallos": invalid_steps_clima + (0 if limits_clima_ok else 1),
    })

    failed_count = sum(1 for r in rules_results if not r["cumplida"])
    qc_dict = {
        "total_rules": len(rules_results),
        "passed_rules": len(rules_results) - failed_count,
        "failed_rules": failed_count,
        "status": "VALID_WITH_WARNINGS" if failed_count == 0 else "REJECTED",
        "rules": rules_results,
        "warnings": warnings,
    }
    return qc_dict, failed_count, warnings


def generate_gold_eia_monthly(df_eia: pd.DataFrame) -> List[Dict[str, Any]]:
    """Genera gold_eia_monthly con contrato canónico: period, state_code, data_status, sales_mwh."""
    grouped = (
        df_eia.groupby(["periodo", "estado", "estado_dato"])["ventas_mwh"]
        .sum()
        .round(2)
        .reset_index()
        .rename(columns={"periodo": "period", "estado": "state_code", "estado_dato": "data_status", "ventas_mwh": "sales_mwh"})
        .sort_values(["state_code", "period"])
    )
    return grouped[["period", "state_code", "data_status", "sales_mwh"]].to_dict(orient="records")


def generate_gold_resstock_monthly(df_resstock: pd.DataFrame, df_meta: pd.DataFrame) -> List[Dict[str, Any]]:
    """Genera gold_resstock_monthly con 120 filas (10 perfiles x 12 meses fuente)."""
    df = df_resstock.copy()
    start_est = df["timestamp_fin_local"] - pd.Timedelta(minutes=15)
    df["source_period"] = start_est.dt.strftime("%Y-%m")

    merged = df.merge(df_meta[["bldg_id", "estado", "tipo_vivienda"]], on="bldg_id")
    grouped = (
        merged.groupby(["bldg_id", "source_period", "estado", "tipo_vivienda"])["electricidad_kwh"]
        .sum()
        .round(4)
        .reset_index()
        .rename(columns={"estado": "state_code", "tipo_vivienda": "housing_type", "electricidad_kwh": "kwh_month"})
        .sort_values(["bldg_id", "source_period"])
    )
    return grouped[["bldg_id", "source_period", "kwh_month", "state_code", "housing_type"]].to_dict(orient="records")


def generate_gold_resstock_profile_summary(df_resstock: pd.DataFrame, df_meta: pd.DataFrame) -> List[Dict[str, Any]]:
    """Genera gold_resstock_profile_summary para los 10 perfiles piloto (8,760 horas por perfil)."""
    df = df_resstock.copy()
    start_est = df["timestamp_fin_local"] - pd.Timedelta(minutes=15)
    df["hour_start"] = start_est.dt.floor("h")

    hourly = (
        df.groupby(["bldg_id", "hour_start"])["electricidad_kwh"]
        .sum()
        .reset_index()
    )

    summ = (
        hourly.groupby("bldg_id")
        .agg(
            annual_kwh=("electricidad_kwh", "sum"),
            mean_hour_kwh=("electricidad_kwh", "mean"),
            peak_hour_kwh=("electricidad_kwh", "max"),
            n_hours=("electricidad_kwh", "count"),
        )
        .reset_index()
    )
    summ["annual_kwh"] = summ["annual_kwh"].round(4)
    summ["mean_hour_kwh"] = summ["mean_hour_kwh"].round(4)
    summ["peak_hour_kwh"] = summ["peak_hour_kwh"].round(4)
    summ["source_year"] = 2018

    meta_cols = df_meta[["bldg_id", "estado", "tipo_vivienda", "peso_viviendas"]].rename(
        columns={"estado": "state_code", "tipo_vivienda": "housing_type", "peso_viviendas": "profile_weight"}
    )
    res = summ.merge(meta_cols, on="bldg_id").sort_values(["state_code", "housing_type"])
    return res[
        ["bldg_id", "source_year", "annual_kwh", "mean_hour_kwh", "peak_hour_kwh", "n_hours", "state_code", "housing_type", "profile_weight"]
    ].to_dict(orient="records")


NOAA_COUNTY_TIMEZONE_VERSION = "NOAA/NWS c_16ap26"

NOAA_SPLIT_COUNTIES = {
    "12045",  # FL Gulf (C/E split)
    "16049",  # ID Idaho (P/M split)
    "31031",  # NE Cherry (M/C split)
    "38025",  # ND Dunn (M/C split)
    "38053",  # ND McKenzie (M/C split)
    "38087",  # ND Sioux (M/C split)
    "41045",  # OR Malheur (P/M split)
    "46117",  # SD Stanley (M/C split)
    "48109",  # TX Culberson (M/C split)
}

NOAA_COUNTY_ZIP_SOURCE = {
    "file": "c_16ap26.zip",
    "version": "c_16ap26 (valid 2026-04-16)",
    "sha256": "503f9d697a97bdbfd8a7cfe6b3b666801f43392fa220294987a68cac0bd3f03b",
    "url": "https://www.weather.gov/source/gis/Shapefiles/County/c_16ap26.zip",
}

# Crosswalk derivado mínimo validado contra NOAA/NWS c_16ap26 (c_16ap26.dbf)
# para los condados presentes en el lote exploratorio (43 FIPS únicos)
NOAA_FIPS_CROSSWALK_BATCH = {
    "06037": ("CA", "Los Angeles", "America/Los_Angeles"),
    "06053": ("CA", "Monterey", "America/Los_Angeles"),
    "06067": ("CA", "Sacramento", "America/Los_Angeles"),
    "06073": ("CA", "San Diego", "America/Los_Angeles"),
    "08005": ("CO", "Arapahoe", "America/Denver"),
    "08031": ("CO", "Denver", "America/Denver"),
    "08041": ("CO", "El Paso", "America/Denver"),
    "08053": ("CO", "Hinsdale", "America/Denver"),
    "08107": ("CO", "Routt", "America/Denver"),
    "12011": ("FL", "Broward", "America/New_York"),
    "12081": ("FL", "Manatee", "America/New_York"),
    "12083": ("FL", "Marion", "America/New_York"),
    "12086": ("FL", "Miami-Dade", "America/New_York"),
    "12095": ("FL", "Orange", "America/New_York"),
    "17019": ("IL", "Champaign", "America/Chicago"),
    "17043": ("IL", "DuPage", "America/Chicago"),
    "17117": ("IL", "Macoupin", "America/Chicago"),
    "17157": ("IL", "Randolph", "America/Chicago"),
    "17199": ("IL", "Williamson", "America/Chicago"),
    "25023": ("MA", "Plymouth", "America/New_York"),
    "25027": ("MA", "Worcester", "America/New_York"),
    "36003": ("NY", "Allegany", "America/New_York"),
    "36045": ("NY", "Jefferson", "America/New_York"),
    "36047": ("NY", "Kings", "America/New_York"),
    "36081": ("NY", "Queens", "America/New_York"),
    "36111": ("NY", "Ulster", "America/New_York"),
    "39017": ("OH", "Butler", "America/New_York"),
    "39035": ("OH", "Cuyahoga", "America/New_York"),
    "39051": ("OH", "Fulton", "America/New_York"),
    "39095": ("OH", "Lucas", "America/New_York"),
    "39153": ("OH", "Summit", "America/New_York"),
    "42003": ("PA", "Allegheny", "America/New_York"),
    "42011": ("PA", "Berks", "America/New_York"),
    "42085": ("PA", "Mercer", "America/New_York"),
    "42091": ("PA", "Montgomery", "America/New_York"),
    "42133": ("PA", "York", "America/New_York"),
    "48029": ("TX", "Bexar", "America/Chicago"),
    "48113": ("TX", "Dallas", "America/Chicago"),
    "48201": ("TX", "Harris", "America/Chicago"),
    "48245": ("TX", "Jefferson", "America/Chicago"),
    "53011": ("WA", "Clark", "America/Los_Angeles"),
    "53033": ("WA", "King", "America/Los_Angeles"),
    "53063": ("WA", "Spokane", "America/Los_Angeles"),
}


def extract_county_fips(condado_codigo: Any) -> str | None:
    """Extrae el código FIPS de 5 dígitos (state 2d + county 3d) desde el código de condado."""
    if not isinstance(condado_codigo, str):
        return None
    s = condado_codigo.strip()
    if s.startswith("G") and len(s) >= 8:
        # Formato GISJOIN censal: G + SS + 0 + CCC + 0
        state_fips = s[1:3]
        county_part = s[4:7]
        if state_fips.isdigit() and county_part.isdigit():
            return f"{state_fips}{county_part}"
    elif len(s) == 5 and s.isdigit():
        return s
    return None


def resolve_county_iana_timezone(county_fips: str | None, state_code: str) -> str:
    """Resuelve la zona IANA por county FIPS según NOAA/NWS c_16ap26, bloqueando condados divididos.

    Fuente: NOAA/NWS County Boundaries c_16ap26 (válida 16-Apr-2026, SHA-256 503f9d69...)
    https://www.weather.gov/gis/Counties y https://www.weather.gov/gis/CountyMetadata
    """
    if not county_fips or not isinstance(county_fips, str) or len(county_fips) != 5:
        raise ValueError(
            f"FIPS inválido o ausente ({county_fips}) para estado {state_code}: "
            "se requiere metadata de condado para resolver zona horaria NOAA/NWS."
        )

    if county_fips in NOAA_SPLIT_COUNTIES:
        raise ValueError(
            f"FIPS {county_fips} ({state_code}) bloqueado: condado con frontera dividida en dos zonas horarias según NOAA/NWS (c_16ap26)."
        )

    # Consulta directa al crosswalk validado contra NOAA/NWS c_16ap26
    entry = NOAA_FIPS_CROSSWALK_BATCH.get(county_fips)
    if entry:
        st, cname, tz = entry
        if st != state_code:
            raise ValueError(
                f"Incongruencia entre estado {state_code} y registro NOAA {st} ({cname}) para FIPS {county_fips}."
            )
        return tz

    # Si no está en el crosswalk validado del lote, bloquear estrictamente para no inferir por estado
    raise ValueError(
        f"FIPS {county_fips} ({state_code}) no presente en el crosswalk validado NOAA/NWS c_16ap26; "
        "bloqueado por ambigüedad. No se infiere zona horaria estatal."
    )


def check_month_is_partial(series_dt: pd.Series, tz_name: str, period_str: str) -> bool:
    """Calcula reproduciblemente si un mes local está incompleto en el rango temporal observado.

    Un mes civil local está completo si y solo si abarca desde el primer instante esperado
    (día 1 a las 00:00:00) hasta el último intervalo esperado (último día a las 23:45:00).
    """
    y, m = map(int, period_str.split("-"))
    month_start = pd.Timestamp(year=y, month=m, day=1, hour=0, minute=0, tz=tz_name)
    if m == 12:
        next_month_start = pd.Timestamp(year=y + 1, month=1, day=1, hour=0, minute=0, tz=tz_name)
    else:
        next_month_start = pd.Timestamp(year=y, month=m + 1, day=1, hour=0, minute=0, tz=tz_name)
    expected_last_interval = next_month_start - pd.Timedelta(minutes=15)

    obs_min = series_dt.min()
    obs_max = series_dt.max()
    return bool((obs_min > month_start) or (obs_max < expected_last_interval))


def prepare_resstock_metadata_timezones(df_meta: pd.DataFrame, expected_bldgs: set[int] | None = None) -> pd.DataFrame:
    """Resuelve la zona IANA por bldg_id sobre df_meta una sola vez (evitando lookup fila a fila sobre intervalos).

    Falla estrictamente si algún perfil carece de FIPS o resolución de zona, evitando omisiones silenciosas.
    """
    meta_cols = ["bldg_id", "estado", "tipo_vivienda", "condado_codigo"]
    sub_meta = df_meta[[c for c in meta_cols if c in df_meta.columns]].drop_duplicates("bldg_id").copy()

    if expected_bldgs:
        missing_in_meta = expected_bldgs - set(sub_meta["bldg_id"])
        if missing_in_meta:
            raise ValueError(f"Perfiles ausentes en metadatos para resolución de zona horaria: {sorted(missing_in_meta)}")
        sub_meta = sub_meta[sub_meta["bldg_id"].isin(expected_bldgs)].copy()

    sub_meta["county_fips"] = sub_meta["condado_codigo"].map(extract_county_fips)

    # Validar FIPS ausente
    missing_fips = sub_meta[sub_meta["county_fips"].isna()]["bldg_id"].tolist()
    if missing_fips:
        raise ValueError(f"Perfil(es) sin county_fips en metadatos: {missing_fips}; no se omite silenciosamente.")

    # Resolver zona por perfil sobre df_meta (1 fila por perfil)
    sub_meta["time_zone"] = sub_meta.apply(
        lambda r: resolve_county_iana_timezone(r["county_fips"], r["estado"]),
        axis=1,
    )
    sub_meta["source_version"] = NOAA_COUNTY_TIMEZONE_VERSION

    # Validar que todos los perfiles tengan zona válida resuelta
    unresolved = sub_meta[sub_meta["time_zone"].isna()]["bldg_id"].tolist()
    if unresolved:
        raise ValueError(f"Perfil(es) sin resolución válida de zona horaria NOAA: {unresolved}; abortando exportación.")

    return sub_meta[["bldg_id", "estado", "tipo_vivienda", "county_fips", "time_zone", "source_version"]]


def generate_gold_resstock_pattern(df_resstock: pd.DataFrame, df_meta: pd.DataFrame) -> List[Dict[str, Any]]:
    """Genera gold_resstock_pattern con conversión horaria por condado según NOAA/NWS c_16ap26.

    Convierte:
      timestamp_fin_local (EST fijo) -> inicio de intervalo (restando 15 min)
      -> UTC (+5 horas)
      -> Zona local IANA resuelta por condado FIPS vía NOAA/NWS (c_16ap26).
      Preserva utc_offset_minutes para distinguir instantes en transición DST.
      Marca is_partial_period reproduciblemente por cobertura observada vs civil esperada.
      Excluye horas con < 4 intervalos de 15 min para evitar sesgar el consumo en bordes.
    """
    unique_bldgs = set(df_resstock["bldg_id"].unique())
    meta_tz = prepare_resstock_metadata_timezones(df_meta, expected_bldgs=unique_bldgs)

    # Merge vectorizado en Cython sobre bldg_id
    df = df_resstock.merge(meta_tz, on="bldg_id")
    if len(df["bldg_id"].unique()) != len(unique_bldgs):
        raise ValueError("Discrepancia en merge de perfiles con metadatos de zona horaria.")

    pattern_records = []

    for tz_name, tz_sub in df.groupby("time_zone"):
        start_est = tz_sub["timestamp_fin_local"] - pd.Timedelta(minutes=15)
        start_utc = (start_est + pd.Timedelta(hours=5)).dt.tz_localize("UTC")
        start_local = start_utc.dt.tz_convert(tz_name)

        tz_sub = tz_sub.copy()
        tz_sub["start_local"] = start_local
        tz_sub["period_local"] = start_local.dt.strftime("%Y-%m")
        tz_sub["date_local"] = start_local.dt.strftime("%Y-%m-%d")
        tz_sub["hour_local"] = start_local.dt.hour
        tz_sub["day_type"] = start_local.dt.dayofweek.map(lambda d: "weekend" if d >= 5 else "weekday")

        offset_sec = (
            start_local.dt.tz_localize(None) - start_local.dt.tz_convert("UTC").dt.tz_localize(None)
        ).dt.total_seconds()
        tz_sub["utc_offset_minutes"] = (offset_sec // 60).astype(int)

        # Regla reproducible de meses parciales por cobertura real observada
        partial_map = {
            p: check_month_is_partial(sub_p["start_local"], tz_name, p)
            for p, sub_p in tz_sub.groupby("period_local")
        }

        hourly = tz_sub.groupby(
            ["bldg_id", "estado", "tipo_vivienda", "period_local", "date_local", "day_type", "hour_local", "utc_offset_minutes", "time_zone", "source_version"]
        ).agg(
            kwh=("electricidad_kwh", "sum"),
            n_intervals=("electricidad_kwh", "count"),
        ).reset_index()

        # Excluir horas incompletas (< 4 intervalos de 15 min) para evitar sesgos en media y percentiles
        hourly = hourly[hourly["n_intervals"] == 4].copy()

        hourly["is_partial_period"] = hourly["period_local"].map(partial_map)

        pat = hourly.groupby(
            ["bldg_id", "estado", "tipo_vivienda", "period_local", "day_type", "hour_local", "utc_offset_minutes", "time_zone", "source_version", "is_partial_period"]
        ).agg(
            median_kwh=("kwh", "median"),
            mean_kwh=("kwh", "mean"),
            p10_kwh=("kwh", lambda s: s.quantile(0.10)),
            p90_kwh=("kwh", lambda s: s.quantile(0.90)),
            n_obs=("kwh", "count"),
        ).reset_index()

        pat["median_kwh"] = pat["median_kwh"].round(4)
        pat["mean_kwh"] = pat["mean_kwh"].round(4)
        pat["p10_kwh"] = pat["p10_kwh"].round(4)
        pat["p90_kwh"] = pat["p90_kwh"].round(4)
        pat["state_code"] = pat["estado"]
        pat["housing_type"] = pat["tipo_vivienda"]

        cols = [
            "bldg_id",
            "period_local",
            "day_type",
            "hour_local",
            "utc_offset_minutes",
            "is_partial_period",
            "median_kwh",
            "mean_kwh",
            "p10_kwh",
            "p90_kwh",
            "n_obs",
            "state_code",
            "housing_type",
            "time_zone",
            "source_version",
        ]
        pattern_records.extend(pat[cols].to_dict(orient="records"))

    pattern_records.sort(key=lambda r: (r["bldg_id"], r["period_local"], r["day_type"], r["hour_local"], r["utc_offset_minutes"]))
    return pattern_records


def generate_gold_resstock_pattern_aggregate(
    df_resstock: pd.DataFrame, df_meta: pd.DataFrame
) -> List[Dict[str, Any]]:
    """Genera gold_resstock_pattern_aggregate con grano por estrato y tiempo local NOAA/NWS.

    Dimensiones / Grano de la clave primaria:
      (state_code, housing_type, time_zone, period_local, day_type, hour_local, utc_offset_minutes)

    Mantiene acotado el volumen consumido por el navegador al escalar la muestra N,
    evitando enviar filas por edificio cuando el usuario analiza patrones agregados.

    Estadísticas calculadas por celda:
      - mean_kwh: media de consumo horario en kWh
      - median_kwh: mediana de consumo horario en kWh
      - p10_kwh: percentil 10 de consumo horario en kWh
      - p90_kwh: percentil 90 de consumo horario en kWh
      - min_kwh: consumo mínimo horario observado en la celda
      - max_kwh: consumo máximo horario observado en la celda
      - n_obs: cantidad de observaciones horarias completas agrupadas
      - n_profiles: cantidad de modelos de simulación únicos que aportan a la celda

    Manejo temporal por condado:
      - Resuelto por county FIPS vía NOAA/NWS c_16ap26.
      - Bloqueo estricto de condados fronterizos divididos (como Gulf, FL y Culberson, TX).
      - time_zone distingue granularmente zonas dentro de estados multidivisionales (FL, TX).
      - utc_offset_minutes distingue horas durante transiciones DST.
      - is_partial_period identifica meses locales incompletos por cobertura reproducible.
      - Excluye horas con < 4 intervalos de 15 min para evitar distorsiones en consumo horario.

    Advertencia metodológica obligatoria:
      La muestra modelada ResStock es física y exploratoria; no representa a la
      población residencial general, totales censales ni facturación de clientes.
    """
    unique_bldgs = set(df_resstock["bldg_id"].unique())
    meta_tz = prepare_resstock_metadata_timezones(df_meta, expected_bldgs=unique_bldgs)

    df = df_resstock.merge(meta_tz, on="bldg_id")
    if len(df["bldg_id"].unique()) != len(unique_bldgs):
        raise ValueError("Discrepancia en merge de perfiles con metadatos de zona horaria.")

    agg_records = []

    for tz_name, tz_sub in df.groupby("time_zone"):
        start_est = tz_sub["timestamp_fin_local"] - pd.Timedelta(minutes=15)
        start_utc = (start_est + pd.Timedelta(hours=5)).dt.tz_localize("UTC")
        start_local = start_utc.dt.tz_convert(tz_name)

        tz_sub = tz_sub.copy()
        tz_sub["start_local"] = start_local
        tz_sub["period_local"] = start_local.dt.strftime("%Y-%m")
        tz_sub["date_local"] = start_local.dt.strftime("%Y-%m-%d")
        tz_sub["hour_local"] = start_local.dt.hour
        tz_sub["day_type"] = start_local.dt.dayofweek.map(lambda d: "weekend" if d >= 5 else "weekday")

        offset_sec = (
            start_local.dt.tz_localize(None) - start_local.dt.tz_convert("UTC").dt.tz_localize(None)
        ).dt.total_seconds()
        tz_sub["utc_offset_minutes"] = (offset_sec // 60).astype(int)

        partial_map = {
            p: check_month_is_partial(sub_p["start_local"], tz_name, p)
            for p, sub_p in tz_sub.groupby("period_local")
        }

        hourly = tz_sub.groupby(
            ["bldg_id", "estado", "tipo_vivienda", "period_local", "date_local", "day_type", "hour_local", "utc_offset_minutes", "time_zone", "source_version"]
        ).agg(
            kwh=("electricidad_kwh", "sum"),
            n_intervals=("electricidad_kwh", "count"),
        ).reset_index()

        # Excluir horas incompletas (< 4 cuartos de hora de 15 min)
        hourly = hourly[hourly["n_intervals"] == 4].copy()

        hourly["is_partial_period"] = hourly["period_local"].map(partial_map)

        agg = hourly.groupby(
            ["estado", "tipo_vivienda", "time_zone", "period_local", "day_type", "hour_local", "utc_offset_minutes", "source_version", "is_partial_period"]
        ).agg(
            mean_kwh=("kwh", "mean"),
            median_kwh=("kwh", "median"),
            p10_kwh=("kwh", lambda s: s.quantile(0.10)),
            p90_kwh=("kwh", lambda s: s.quantile(0.90)),
            min_kwh=("kwh", "min"),
            max_kwh=("kwh", "max"),
            n_obs=("kwh", "count"),
            n_profiles=("bldg_id", "nunique"),
        ).reset_index()

        agg["mean_kwh"] = agg["mean_kwh"].round(4)
        agg["median_kwh"] = agg["median_kwh"].round(4)
        agg["p10_kwh"] = agg["p10_kwh"].round(4)
        agg["p90_kwh"] = agg["p90_kwh"].round(4)
        agg["min_kwh"] = agg["min_kwh"].round(4)
        agg["max_kwh"] = agg["max_kwh"].round(4)
        agg["state_code"] = agg["estado"]
        agg["housing_type"] = agg["tipo_vivienda"]

        cols = [
            "state_code",
            "housing_type",
            "time_zone",
            "period_local",
            "day_type",
            "hour_local",
            "utc_offset_minutes",
            "is_partial_period",
            "mean_kwh",
            "median_kwh",
            "p10_kwh",
            "p90_kwh",
            "min_kwh",
            "max_kwh",
            "n_obs",
            "n_profiles",
            "source_version",
        ]
        agg_records.extend(agg[cols].to_dict(orient="records"))

    agg_records.sort(
        key=lambda r: (
            r["state_code"],
            r["housing_type"],
            r["time_zone"],
            r["period_local"],
            r["day_type"],
            r["hour_local"],
            r["utc_offset_minutes"],
        )
    )
    return agg_records


def generate_gold_climate(df_clima: pd.DataFrame) -> List[Dict[str, Any]]:
    """Genera gold_climate con 336 filas horarias UTC."""
    df = df_clima.copy()
    df["point_id"] = df["punto_id"]
    df["state_code"] = df["estado"]
    df["temperature_c"] = df["temperatura_c"].round(2)
    df["model"] = df["modelo"]
    df["requested_latitude"] = df["latitude_solicitada"]
    df["requested_longitude"] = df["longitude_solicitada"]
    df["cell_latitude"] = df["latitude_celda"]
    df["cell_longitude"] = df["longitude_celda"]

    df = df.sort_values(["point_id", "timestamp_utc"])
    cols = [
        "point_id",
        "state_code",
        "timestamp_utc",
        "temperature_c",
        "model",
        "requested_latitude",
        "requested_longitude",
        "cell_latitude",
        "cell_longitude",
    ]
    return df[cols].to_dict(orient="records")


def write_json_and_measure(data: Any, target_path: str) -> Tuple[int, str]:
    """Escribe un archivo JSON con indentación estándar, mide bytes y calcula SHA-256."""
    encoded = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
    size_bytes = len(encoded)
    sha256 = hashlib.sha256(encoded).hexdigest()
    with open(target_path, "wb") as f:
        f.write(encoded)
    return size_bytes, sha256


def main() -> int:
    args = parse_arguments()
    real_input, real_output = validate_paths(args.input, args.output, args.overwrite)
    is_v2 = "v2" in real_output
    print("=" * 70)
    print(f"Iniciando generación de datos Gold reproducibles para {'tablero/data/v2' if is_v2 else 'tablero/data/v1'}")
    print(f"Directorio de entrada:       {args.input}")
    print(f"Directorio demografía:       {args.demografia_input}")
    print(f"Directorio de salida:        {args.output}")
    print("=" * 70)

    # 1. Verificación de fuentes de entrada
    print("Verificando hashes e inventario de datos de entrada...")
    source_inventory, rs_roster_info = verify_input_sources(real_input)
    print("  4 archivos base verificados exitosamente contra manifiesto de integración.")

    demo_sources = []
    records_demography = []
    demo_qc_rules = []
    if is_v2 or os.path.exists(args.demografia_input):
        print("Verificando fuentes demográficas canónicas...")
        demo_meta, demo_sources = verify_demography_source(args.demografia_input)
        demo_csv_path = os.path.join(args.demografia_input, demo_meta["artifact"]["file"])
        records_demography = generate_gold_demography_state_year(demo_csv_path)
        demo_qc_rules, demo_failed = run_demography_qc(records_demography)
        print(f"  Demografía verificada: {len(records_demography)} filas, {len(demo_qc_rules)} reglas QC aprobadas.")
        if demo_failed > 0:
            print(f"ERROR: Se detectaron {demo_failed} reglas demográficas fallidas. Publicación bloqueada.")
            return 1

    # 2. Carga de datos
    print("Cargando datasets piloto...")
    parquet_path = os.path.join(real_input, "resstock_perfiles_piloto.parquet")
    meta_path = os.path.join(real_input, "resstock_seleccion_propuesta.csv")
    eia_path = os.path.join(real_input, "eia_residencial_mensual.csv")
    clima_path = os.path.join(real_input, "clima_open_meteo_muestra.csv")

    df_resstock = pq.read_table(parquet_path).to_pandas()
    df_meta = pd.read_csv(meta_path)
    df_eia = pd.read_csv(eia_path)
    df_clima = pd.read_csv(clima_path)

    # 3. Ejecución de QC formal
    print("Ejecutando controles de calidad de datos...")
    qc_dict, failed_count, warnings = run_qc_checks(
        df_resstock, df_meta, df_eia, df_clima, roster_info=rs_roster_info
    )
    print(f"  Reglas base aprobadas: {qc_dict['passed_rules']}/{qc_dict['total_rules']}")
    if failed_count > 0:
        print(f"ERROR: Se detectaron {failed_count} reglas fallidas. Publicación bloqueada.")
        return 1

    # 4. Transformaciones Gold
    print("Generando tablas Gold según contrato acordado...")
    records_eia = generate_gold_eia_monthly(df_eia)
    records_rs_monthly = generate_gold_resstock_monthly(df_resstock, df_meta)
    records_rs_summary = generate_gold_resstock_profile_summary(df_resstock, df_meta)
    records_rs_pattern = generate_gold_resstock_pattern(df_resstock, df_meta)
    records_rs_pattern_agg = generate_gold_resstock_pattern_aggregate(df_resstock, df_meta)
    records_climate = generate_gold_climate(df_clima)

    print(f"  - gold_eia_monthly:                 {len(records_eia)} filas")
    print(f"  - gold_resstock_monthly:            {len(records_rs_monthly)} filas")
    print(f"  - gold_resstock_profile_summary:    {len(records_rs_summary)} filas")
    print(f"  - gold_resstock_pattern:            {len(records_rs_pattern)} filas")
    print(f"  - gold_resstock_pattern_aggregate:  {len(records_rs_pattern_agg)} filas")
    print(f"  - gold_climate:                     {len(records_climate)} filas")
    if records_demography and is_v2:
        print(f"  - gold_demography_state_year:       {len(records_demography)} filas")

    # 5. Escritura atómica a carpeta de salida mediante staging
    parent_dir = os.path.dirname(real_output)
    os.makedirs(parent_dir, exist_ok=True)

    staging_dir = tempfile.mkdtemp(prefix=".tablero_staging_", dir=parent_dir)
    now_utc_str = datetime.now(timezone.utc).isoformat()

    n_bldgs = len(df_resstock["bldg_id"].unique())
    states_list = sorted(df_meta[df_meta["bldg_id"].isin(df_resstock["bldg_id"].unique())]["estado"].unique())
    states_str = ", ".join(states_list)

    try:
        tables_meta = {}
        payloads = {
            "gold_eia_monthly": (records_eia, "gold_eia_monthly.json", ["period", "state_code"]),
            "gold_resstock_monthly": (records_rs_monthly, "gold_resstock_monthly.json", ["bldg_id", "source_period"]),
            "gold_resstock_pattern": (records_rs_pattern, "gold_resstock_pattern.json", ["bldg_id", "period_local", "day_type", "hour_local", "utc_offset_minutes"]),
            "gold_resstock_pattern_aggregate": (records_rs_pattern_agg, "gold_resstock_pattern_aggregate.json", ["state_code", "housing_type", "time_zone", "period_local", "day_type", "hour_local", "utc_offset_minutes"]),
            "gold_resstock_profile_summary": (records_rs_summary, "gold_resstock_profile_summary.json", ["bldg_id"]),
            "gold_climate": (records_climate, "gold_climate.json", ["point_id", "timestamp_utc"]),
        }

        if is_v2 and records_demography:
            payloads["gold_demography_state_year"] = (
                records_demography,
                "gold_demography_state_year.json",
                ["state_fips", "year"],
            )

        for table_name, (records, filename, pk) in payloads.items():
            file_path = os.path.join(staging_dir, filename)
            size_b, sha_hex = write_json_and_measure(records, file_path)
            tables_meta[table_name] = {
                "file": filename,
                "rows": len(records),
                "bytes": size_b,
                "sha256": sha_hex,
                "primary_key": pk,
            }

        # En v2, incorporar tablas analíticas si existen en v1 para no vaciar vistas
        copied_analytics_meta = {}
        analytics_section = None
        analytics_status = None
        if is_v2 and os.path.isdir(args.v1_base):
            copied_analytics_meta, analytics_section, analytics_status = load_and_copy_analytics(
                args.v1_base, staging_dir
            )
            tables_meta.update(copied_analytics_meta)

        # 6. Construcción y escritura de manifest.json
        combined_qc_rules = list(qc_dict.get("rules", [])) + demo_qc_rules if is_v2 else qc_dict.get("rules", [])
        total_rules = qc_dict["total_rules"] + (len(demo_qc_rules) if is_v2 else 0)
        passed_rules = qc_dict["passed_rules"] + (len(demo_qc_rules) if is_v2 else 0)

        coverage_summary = {
            "eia": "2018-01 through 2026-08 (51 jurisdictions: 50 states + DC), monthly residential utility sales",
            "resstock": f"AMY 2018, {n_bldgs} profiles ({states_str}), 15-minute intervals (35,040 per bldg); individual patterns and stratum-level aggregate patterns",
            "climate": "2018-01-01 to 2018-01-07, 2 point locations in Colorado (Denver, Grand Junction), ERA5-Land hourly"
        }
        if is_v2:
            coverage_summary["demography"] = "2020 through 2025 (51 jurisdictions: 50 states + DC), annual residential sales, population estimates (Vintage 2025) and density"

        methodology_sep = {
            "resstock_modelled": (
                f"{n_bldgs} physical building energy simulation models (AMY 2018). Exploratory sample across {len(states_list)} states ({states_str}); "
                "does not represent national totals. Timestamps converted explicitly from fixed EST to UTC and local IANA time zones by county (NOAA/NWS c_16ap26)."
            ),
            "resstock_pattern_aggregate": {
                "grain": "(state_code, housing_type, time_zone, period_local, day_type, hour_local, utc_offset_minutes)",
                "metrics_calculated": [
                    "mean_kwh",
                    "median_kwh",
                    "p10_kwh",
                    "p90_kwh",
                    "min_kwh",
                    "max_kwh",
                    "n_obs",
                    "n_profiles",
                ],
                "temporal_handling": (
                    "Explicit conversion: fixed EST (-15m to interval start) -> UTC (+5h) -> "
                    "local IANA zones resolved by county FIPS (NOAA/NWS c_16ap26), preserving utc_offset_minutes, "
                    "excluding incomplete hours (<4 intervals), and deriving is_partial_period by civil month coverage."
                ),
                "sample_representativeness": (
                    "Modeled physical simulation profiles; does NOT represent population, census totals, or utility billing totals."
                ),
                "scalability_purpose": (
                    "Keeps browser payload bounded to stratum dimensions as sample size scales, while preserving individual inspection via lazy-load in gold_resstock_pattern."
                ),
            },
            "eia_sales": (
                "Aggregated official utility sales from Form EIA-861M for 51 jurisdictions. "
                "Completely distinct population and scope from ResStock."
            ),
            "climate_reanalysis": (
                "ERA5-Land reanalysis for 2 point locations in CO; preserved decoupled without spatial or temporal join to consumption."
            ),
            "colorado_eia_comparison_metric": {
                "reported_ratio_pct": 87.16,
                "status": "not_reproduced",
                "blocker": (
                    "The raw ResStock Colorado aggregate dataset (timeseries_aggregates) is absent from origin/main. "
                    "Per project governance and data integrity rules, no synthetic substitute is created, "
                    "and the 87.16% figure is documented as an unverified external descriptive ratio, not an independently reproduced precision metric."
                )
            }
        }
        if is_v2:
            methodology_sep["state_energy_demography"] = {
                "grain": "(state_fips, year)",
                "coverage": "2020 through 2025 (51 jurisdictions: 50 states + DC)",
                "metrics": [
                    "population_estimate",
                    "population_density_per_sq_mi",
                    "residential_sales_mwh",
                    "residential_kwh_per_capita",
                ],
                "sources": "Census PEP Vintage 2025, Census TIGERweb 2020 land area, EIA-861M final residential sales",
                "methodology_separation": (
                    "Aggregate macro-level data combining official Census Bureau population estimates and EIA utility sales. "
                    "Fundamentally separate and decoupled from individual simulated building profiles (ResStock AMY 2018). "
                    "The District of Columbia (DC) is an urban federal district (11,348 hab/mi²), distinct from the 50 states. "
                    "Ratios and correlations between density, population, and sales per capita are strictly descriptive; no causal claim is made."
                )
            }

        combined_inventory = list(source_inventory)
        if is_v2 and demo_sources:
            combined_inventory.extend(demo_sources)

        manifest_data = {
            "manifest_version": "1.0",
            "schema_version": "1.0",
            "publication_version": "2.0" if is_v2 else "1.0",
            "generated_at_utc": now_utc_str,
            "generator_script": "scripts/generar_datos_tablero.py",
            "data_status": qc_dict["status"],
            "coverage_summary": coverage_summary,
            "methodology_separation": methodology_sep,
            "source_inventory": combined_inventory,
            "qc_rules": {
                "total_rules": total_rules,
                "passed_rules": passed_rules,
                "failed_rules": 0,
                "status": qc_dict["status"],
                "warnings": qc_dict["warnings"],
                "rules": combined_qc_rules if is_v2 else qc_dict.get("rules", []),
            },
            "tables": tables_meta,
        }

        if analytics_section:
            manifest_data["analytics"] = analytics_section
        if analytics_status:
            manifest_data["analytics_status"] = analytics_status

        manifest_path = os.path.join(staging_dir, "manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2, ensure_ascii=False)

        # 7. Publicación atómica; la salida anterior se conserva salvo --overwrite explícito.
        publish_staging(staging_dir, real_output, args.overwrite)
        print(f"Archivos publicados exitosamente en: {real_output}")
        print("=" * 70)

    finally:
        if os.path.exists(staging_dir):
            shutil.rmtree(staging_dir, ignore_errors=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
