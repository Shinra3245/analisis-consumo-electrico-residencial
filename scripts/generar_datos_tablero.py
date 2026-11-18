#!/usr/bin/env python3
"""Generador reproducible de datos Gold para el tablero web (v1).

Lee los artefactos de datos versionados en datos/, valida hashes contra
datos/manifiesto-integracion.json, ejecuta 21 controles de calidad formales,
realiza las transformaciones canónicas requeridas por el contrato v1 y
exporta los datasets en formato JSON bajo tablero/data/v1/:
  - gold_eia_monthly.json (5,304 filas)
  - gold_resstock_monthly.json (120 filas)
  - gold_resstock_pattern.json (6,730 filas)
  - gold_resstock_profile_summary.json (10 filas)
  - gold_climate.json (336 filas)
  - manifest.json (manifiesto con hashes, esquema 1.0, QC, linaje y bloqueo 87.16%)

Manejo temporal:
  - Timestamps ResStock de origen están en EST fijo (UTC-5), sin DST.
  - Para gold_resstock_monthly: inicio de intervalo derivado restando 15 min a marca de fin.
  - Para gold_resstock_pattern: se calcula inicio de intervalo, se convierte explícitamente
    a UTC (+5 horas) y luego a la zona IANA del estado (America/Denver para CO,
    America/New_York para NY). Se preserva utc_offset_minutes para distinguir horas en DST
    y se marcan periodos locales parciales (2017-12 y 2018-12 en CO).
  - La relación 87.16% Colorado/EIA queda documentada como no reproducida debido a la
    ausencia del agregado crudo en el repositorio, sin inventar datos sustitutos.
"""

from __future__ import annotations

import argparse
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

EXPECTED_OUTPUT_FILES = {
    "gold_eia_monthly.json",
    "gold_resstock_monthly.json",
    "gold_resstock_pattern.json",
    "gold_resstock_profile_summary.json",
    "gold_climate.json",
    "manifest.json",
}


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Genera datos Gold reproducibles para el tablero web (v1)."
    )
    parser.add_argument(
        "--input",
        type=str,
        default="datos",
        help="Directorio con los datos de entrada (default: datos).",
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
            manifest.get("schema_version") != "1.0"
            or manifest.get("generator_script") != "scripts/generar_datos_tablero.py"
            or actual_files != EXPECTED_OUTPUT_FILES
        ):
            raise ValueError(
                "--overwrite solo reemplaza una exportación v1 reconocida sin archivos adicionales; "
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

    return inventory


def run_qc_checks(
    df_resstock: pd.DataFrame,
    df_metadata: pd.DataFrame,
    df_eia: pd.DataFrame,
    df_clima: pd.DataFrame,
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
    r1 = bool(n_rows_rs == 350400 and n_bldgs_rs == 10)
    rules_results.append({
        "fuente": "resstock",
        "regla": "filas_y_edificios_esperados",
        "condicion": "filas == 350400 y edificios == 10",
        "cumplida": r1,
        "fallos": 0 if r1 else 1,
    })

    counts_by_bldg = df_resstock.groupby("bldg_id").size().to_dict()
    r2 = bool(all(c == 35040 for c in counts_by_bldg.values()) and len(counts_by_bldg) == 10)
    rules_results.append({
        "fuente": "resstock",
        "regla": "cobertura_intervalos_anual_por_edificio",
        "condicion": "cada bldg_id tiene exactamente 35040 intervalos de 15 min (AMY 2018)",
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
        len(meta_pilot) == 10
        and meta_pilot["bldg_id"].nunique() == 10
        and meta_pilot["estado"].str.match(r"^[A-Z]{2}$").all()
        and (meta_pilot["peso_viviendas"] > 0).all()
        and not meta_pilot[["tipo_vivienda", "condado_codigo", "upgrade", "url"]].isna().any().any()
    )
    r7 = bool(meta_valid)
    rules_results.append({
        "fuente": "resstock",
        "regla": "metadata_resstock_completa_y_univoca",
        "condicion": "cada perfil piloto tiene una fila válida en resstock_seleccion_propuesta.csv",
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


def generate_gold_resstock_pattern(df_resstock: pd.DataFrame, df_meta: pd.DataFrame) -> List[Dict[str, Any]]:
    """Genera gold_resstock_pattern con conversión horaria explícita a zonas IANA locales.

    Convierte:
      timestamp_fin_local (EST fijo) -> inicio de intervalo (restando 15 min)
      -> UTC (+5 horas)
      -> Zona local IANA:
         CO: America/Denver
         NY: America/New_York
      Preserva utc_offset_minutes para distinguir instantes en transición DST.
      Marca is_partial_period=True para periodos incompletos (2017-12 y 2018-12 en CO).
    """
    tz_map = {
        "CO": "America/Denver",
        "NY": "America/New_York",
    }

    df = df_resstock.merge(df_meta[["bldg_id", "estado", "tipo_vivienda"]], on="bldg_id")
    pattern_records = []

    for state_code, tz_name in tz_map.items():
        sub = df[df["estado"] == state_code].copy()
        if sub.empty:
            continue

        # 1. Inicio en EST fijo
        start_est = sub["timestamp_fin_local"] - pd.Timedelta(minutes=15)
        # 2. Conversión a UTC
        start_utc = (start_est + pd.Timedelta(hours=5)).dt.tz_localize("UTC")
        # 3. Conversión a zona local
        start_local = start_utc.dt.tz_convert(tz_name)

        sub["period_local"] = start_local.dt.strftime("%Y-%m")
        sub["date_local"] = start_local.dt.strftime("%Y-%m-%d")
        sub["hour_local"] = start_local.dt.hour
        sub["day_type"] = start_local.dt.dayofweek.map(lambda d: "weekend" if d >= 5 else "weekday")

        offset_sec = (start_local.dt.tz_localize(None) - start_local.dt.tz_convert("UTC").dt.tz_localize(None)).dt.total_seconds()
        sub["utc_offset_minutes"] = (offset_sec // 60).astype(int)

        # 4. Agregación a nivel horario (sumando intervalos dentro de cada hora local)
        hourly = sub.groupby(
            ["bldg_id", "estado", "tipo_vivienda", "period_local", "date_local", "day_type", "hour_local", "utc_offset_minutes"]
        ).agg(
            kwh=("electricidad_kwh", "sum")
        ).reset_index()

        # 5. Agregación del patrón por perfil, mes local, tipo de día, hora y desplazamiento
        pat = hourly.groupby(
            ["bldg_id", "estado", "tipo_vivienda", "period_local", "day_type", "hour_local", "utc_offset_minutes"]
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
        pat["time_zone"] = tz_name
        pat["state_code"] = pat["estado"]
        pat["housing_type"] = pat["tipo_vivienda"]

        # En Colorado, la cobertura de AMY 2018 abarca partes de 2017-12 y 2018-12
        if state_code == "CO":
            pat["is_partial_period"] = pat["period_local"].isin(["2017-12", "2018-12"])
        else:
            pat["is_partial_period"] = False

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
        ]
        pattern_records.extend(pat[cols].to_dict(orient="records"))

    # Ordenar por bldg_id, period_local, day_type, hour_local, utc_offset_minutes
    pattern_records.sort(key=lambda r: (r["bldg_id"], r["period_local"], r["day_type"], r["hour_local"], r["utc_offset_minutes"]))
    return pattern_records


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
    print("=" * 70)
    print("Iniciando generación de datos Gold reproducibles para tablero/data/v1")
    print(f"Directorio de entrada: {args.input}")
    print(f"Directorio de salida:  {args.output}")
    print("=" * 70)

    # 1. Verificación de fuentes de entrada
    print("Verificando hashes e inventario de datos de entrada...")
    source_inventory = verify_input_sources(real_input)
    print(f"  4 archivos verificados exitosamente contra manifiesto de integración.")

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
    print("Ejecutando 21 controles de calidad de datos...")
    qc_dict, failed_count, warnings = run_qc_checks(df_resstock, df_meta, df_eia, df_clima)
    print(f"  Reglas aprobadas: {qc_dict['passed_rules']}/{qc_dict['total_rules']}")
    if failed_count > 0:
        print(f"ERROR: Se detectaron {failed_count} reglas fallidas. Publicación bloqueada.")
        return 1

    # 4. Transformaciones Gold
    print("Generando tablas Gold según contrato acordado...")
    records_eia = generate_gold_eia_monthly(df_eia)
    records_rs_monthly = generate_gold_resstock_monthly(df_resstock, df_meta)
    records_rs_summary = generate_gold_resstock_profile_summary(df_resstock, df_meta)
    records_rs_pattern = generate_gold_resstock_pattern(df_resstock, df_meta)
    records_climate = generate_gold_climate(df_clima)

    print(f"  - gold_eia_monthly:              {len(records_eia)} filas")
    print(f"  - gold_resstock_monthly:         {len(records_rs_monthly)} filas")
    print(f"  - gold_resstock_profile_summary: {len(records_rs_summary)} filas")
    print(f"  - gold_resstock_pattern:         {len(records_rs_pattern)} filas")
    print(f"  - gold_climate:                  {len(records_climate)} filas")

    # 5. Escritura atómica a carpeta de salida mediante staging
    parent_dir = os.path.dirname(real_output)
    os.makedirs(parent_dir, exist_ok=True)

    staging_dir = tempfile.mkdtemp(prefix=".tablero_v1_staging_", dir=parent_dir)
    now_utc_str = datetime.now(timezone.utc).isoformat()

    try:
        tables_meta = {}
        payloads = {
            "gold_eia_monthly": (records_eia, "gold_eia_monthly.json", ["period", "state_code"]),
            "gold_resstock_monthly": (records_rs_monthly, "gold_resstock_monthly.json", ["bldg_id", "source_period"]),
            "gold_resstock_pattern": (records_rs_pattern, "gold_resstock_pattern.json", ["bldg_id", "period_local", "day_type", "hour_local", "utc_offset_minutes"]),
            "gold_resstock_profile_summary": (records_rs_summary, "gold_resstock_profile_summary.json", ["bldg_id"]),
            "gold_climate": (records_climate, "gold_climate.json", ["point_id", "timestamp_utc"]),
        }

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

        # 6. Construcción y escritura de manifest.json
        manifest_data = {
            "manifest_version": "1.0",
            "schema_version": "1.0",
            "generated_at_utc": now_utc_str,
            "generator_script": "scripts/generar_datos_tablero.py",
            "data_status": qc_dict["status"],
            "coverage_summary": {
                "eia": "2018-01 through 2026-08 (51 jurisdictions: 50 states + DC), monthly residential utility sales",
                "resstock": "AMY 2018, 10 pilot profiles (5 Colorado, 5 New York), 15-minute intervals (35,040 per bldg)",
                "climate": "2018-01-01 to 2018-01-07, 2 point locations in Colorado (Denver, Grand Junction), ERA5-Land hourly"
            },
            "methodology_separation": {
                "resstock_modelled": (
                    "10 physical building energy simulation models (AMY 2018). Pilot exploratory sample; "
                    "does not represent national totals. Timestamps converted explicitly from fixed EST to UTC and local IANA time zones."
                ),
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
            },
            "source_inventory": source_inventory,
            "qc_rules": {
                "total_rules": qc_dict["total_rules"],
                "passed_rules": qc_dict["passed_rules"],
                "failed_rules": qc_dict["failed_rules"],
                "status": qc_dict["status"],
                "warnings": qc_dict["warnings"],
            },
            "tables": tables_meta,
        }

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
