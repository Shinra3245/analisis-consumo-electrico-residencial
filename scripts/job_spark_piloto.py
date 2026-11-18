#!/usr/bin/env python3
"""Job PySpark reproducible para procesamiento local de datos de consumo residencial.

Lee los artefactos piloto locales (ResStock Parquet, EIA CSV, Clima CSV) con
esquemas explícitos, aplica 20 controles de calidad formales según docs/contrato-datos-v1.md,
bloquea la publicación si hay reglas fallidas, escribe tablas Silver y Gold con
nombres canónicos y asignación mensual corregida (12 meses 2018), preservando
la separación semántica de fuentes, y publica atómicamente el árbol completo
(incluyendo el reporte de calidad JSON) mediante staging temporal hermano con tempfile.mkdtemp.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
import shutil
import sys
import tempfile
from typing import Any, Dict, List, Tuple


def parse_arguments() -> argparse.Namespace:
    """Parsea los argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        description="Job PySpark reproducible para el bloque local de datos."
    )
    parser.add_argument(
        "--input",
        type=str,
        default="datos",
        help="Directorio que contiene los archivos de entrada (default: datos).",
    )
    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="Directorio destino para las salidas Silver, Gold y el reporte JSON.",
    )
    parser.add_argument(
        "--master",
        type=str,
        default="local[2]",
        help="Master URL para Spark (default: local[2]).",
    )
    parser.add_argument(
        "--app-name",
        type=str,
        default="PilotoConsumoResidencialSilverGold",
        help="Nombre de la aplicación Spark.",
    )
    return parser.parse_args()


def validate_paths(input_dir: str, output_dir: str) -> Tuple[str, str]:
    """Valida que los directorios de entrada y salida sean seguros y no colisionen.

    Resuelve symlinks mediante realpath para evitar evasión de seguridad.
    Rechaza rutas destructivas:
    1. Si output es idéntico a input.
    2. Si output y input se solapan o se contienen mutuamente.
    3. Si output ya existe y no está vacío (evita sobrescritura accidental).
    """
    real_input = os.path.realpath(input_dir)
    real_output = os.path.realpath(output_dir)

    if not os.path.isdir(real_input):
        raise FileNotFoundError(
            f"El directorio de entrada no existe: {real_input}"
        )

    if real_input == real_output:
        raise ValueError(
            f"El directorio de salida (--output: {real_output}) no puede ser idéntico al directorio "
            f"de entrada ({real_input}). Debe usar una ruta no destructiva."
        )

    # Control de anidamiento y solapamiento mutuo resolviendo enlaces simbólicos
    is_overlapping = False
    try:
        common = os.path.commonpath([real_input, real_output])
        is_overlapping = (common == real_input or common == real_output)
    except ValueError:
        # Rutas en unidades distintas (ej. Windows C: vs D:) no se solapan
        is_overlapping = False

    if is_overlapping:
        raise ValueError(
            f"El directorio de salida ({real_output}) y el directorio de entrada "
            f"({real_input}) no pueden solaparse ni contenerse mutuamente para evitar contaminación de fuentes."
        )

    # Rechazar si el directorio de salida ya existe y contiene archivos
    if os.path.exists(real_output):
        if not os.path.isdir(real_output):
            raise ValueError(
                f"La ruta de salida existe y no es un directorio: {real_output}"
            )
        if os.listdir(real_output):
            raise ValueError(
                f"El directorio de salida ya existe y no está vacío ({real_output}). "
                "Para evitar sobrescrituras destructivas accidentales, proporcione un directorio nuevo o vacío."
            )

    return real_input, real_output


def build_spark_session(app_name: str, master: str):
    """Inicializa la sesión de Spark con la configuración temporal y de Parquet requerida."""
    from pyspark.sql import SparkSession

    builder = (
        SparkSession.builder.appName(app_name)
        .master(master)
        # Configuración obligatoria para Parquet sin zona horaria (TimestampNTZType)
        .config("spark.sql.parquet.inferTimestampNTZ.enabled", "true")
        .config("spark.sql.session.timeZone", "UTC")
        # Compatibilidad en lectura/escritura de timestamps
        .config("spark.sql.parquet.outputTimestampType", "TIMESTAMP_MICROS")
        .config("spark.sql.parquet.datetimeRebaseModeInRead", "CORRECTED")
        .config("spark.sql.parquet.int96RebaseModeInRead", "CORRECTED")
    )
    return builder.getOrCreate()


def define_schemas():
    """Define esquemas explícitos para los archivos CSV del piloto."""
    from pyspark.sql.types import (
        DoubleType,
        IntegerType,
        LongType,
        StringType,
        StructField,
        StructType,
        TimestampType,
    )

    # Esquema explícito para EIA-861M mensual
    schema_eia = StructType(
        [
            StructField("periodo", StringType(), nullable=False),
            StructField("estado", StringType(), nullable=False),
            StructField("sector", StringType(), nullable=False),
            StructField("estado_dato", StringType(), nullable=False),
            StructField("ventas_mwh", DoubleType(), nullable=False),
        ]
    )

    # Esquema explícito para Clima muestra Open-Meteo
    schema_clima = StructType(
        [
            StructField("punto_id", StringType(), nullable=False),
            StructField("estado", StringType(), nullable=False),
            StructField("latitude_solicitada", DoubleType(), nullable=False),
            StructField("longitude_solicitada", DoubleType(), nullable=False),
            StructField("latitude_celda", DoubleType(), nullable=False),
            StructField("longitude_celda", DoubleType(), nullable=False),
            StructField("timestamp_utc", TimestampType(), nullable=False),
            StructField("temperatura_c", DoubleType(), nullable=False),
            StructField("modelo", StringType(), nullable=False),
        ]
    )

    # Metadatos de los 10 perfiles disponibles, tomados del índice versionado
    # de selección. Los 10,000 registros del índice son candidatos, no perfiles
    # descargados; el job solo enriquece IDs presentes en el Parquet piloto.
    schema_resstock_metadata = StructType(
        [
            StructField("bldg_id", LongType(), nullable=False),
            StructField("estado", StringType(), nullable=False),
            StructField("tipo_vivienda", StringType(), nullable=False),
            StructField("condado_codigo", StringType(), nullable=False),
            StructField("peso_viviendas", DoubleType(), nullable=False),
            StructField("upgrade", IntegerType(), nullable=False),
            StructField("url", StringType(), nullable=False),
        ]
    )

    return schema_eia, schema_clima, schema_resstock_metadata


def build_source_inventory(input_dir: str) -> List[Dict[str, Any]]:
    """Verifica los hashes de entrada contra el manifiesto integrado del piloto."""
    manifest_path = os.path.join(input_dir, "manifiesto-integracion.json")
    with open(manifest_path, encoding="utf-8") as source_file:
        source_manifest = json.load(source_file)

    required = {
        "resstock_perfiles_piloto.parquet": "resstock_2025r1_amy2018_upgrade0_pilot",
        "resstock_seleccion_propuesta.csv": "resstock_2025r1_selection_index",
        "eia_residencial_mensual.csv": "eia861m_sales_monthly",
        "clima_open_meteo_muestra.csv": "openmeteo_era5land_hourly",
    }
    declared = {item["file"]: item for item in source_manifest["artifacts"]}
    inventory: List[Dict[str, Any]] = []
    for filename, dataset_id in required.items():
        path = os.path.join(input_dir, filename)
        record = declared.get(filename)
        if record is None:
            raise ValueError(f"El manifiesto integrado no contiene {filename}.")
        digest = hashlib.sha256()
        size_bytes = 0
        with open(path, "rb") as input_file:
            for chunk in iter(lambda: input_file.read(1024 * 1024), b""):
                digest.update(chunk)
                size_bytes += len(chunk)
        actual_sha = digest.hexdigest()
        if actual_sha != record["sha256"] or size_bytes != record["bytes"]:
            raise ValueError(
                f"El archivo {filename} no coincide con hash/tamaño del manifiesto integrado."
            )
        inventory.append(
            {
                "source_dataset_id": dataset_id,
                "source_uri": record.get("source_url"),
                "file": filename,
                "bytes": size_bytes,
                "source_sha256": actual_sha,
                "integrated_date": source_manifest.get("integrated_date"),
                "source_retrieved_at_utc": None,
                "retrieval_timestamp_note": "El manifiesto disponible no conserva la hora exacta de descarga.",
                "license_note": record.get("license"),
            }
        )
    return inventory


def execute_resstock_qc(df_resstock, df_metadata) -> Dict[str, Any]:
    """Ejecuta 7 controles de calidad sobre perfiles y metadatos ResStock."""
    from pyspark.sql import functions as F
    from pyspark.sql.window import Window

    filas_totales = df_resstock.count()
    edificios_unicos = df_resstock.select("bldg_id").distinct().count()

    # Conteo por edificio
    conteo_por_edificio = {
        int(row["bldg_id"]): int(row["count"])
        for row in df_resstock.groupBy("bldg_id").count().collect()
    }

    # Revisión de nulos en todas las columnas
    null_exprs = [
        F.sum(F.when(F.col(c).isNull(), 1).otherwise(0)).alias(c)
        for c in ["bldg_id", "timestamp_fin_local", "electricidad_kwh"]
    ]
    nulls = df_resstock.select(null_exprs).first().asDict()
    total_nulos = int(sum(nulls.values()))

    # Revisión de valores no físicos, negativos o no finitos (NaN o infinitos)
    no_finitos_o_negativos = df_resstock.filter(
        (F.col("electricidad_kwh") < 0.0)
        | F.isnan("electricidad_kwh")
        | (F.col("electricidad_kwh") == float("inf"))
        | (F.col("electricidad_kwh") == float("-inf"))
        | F.col("electricidad_kwh").isNull()
    ).count()

    # Unicidad de clave primaria (bldg_id, timestamp_fin_local)
    duplicados_pk = (
        df_resstock.groupBy("bldg_id", "timestamp_fin_local")
        .count()
        .filter(F.col("count") > 1)
        .count()
    )

    # Continuidad temporal: verificar paso estricto de 15 min (900 s) y límites
    w_resstock = Window.partitionBy("bldg_id").orderBy("timestamp_fin_local")
    step_sec_expr = (
        F.unix_timestamp(F.col("timestamp_fin_local"))
        - F.unix_timestamp(F.lag("timestamp_fin_local").over(w_resstock))
    )
    pasos_invalidos_900s = (
        df_resstock.withColumn("step_sec", step_sec_expr)
        .filter(F.col("step_sec").isNotNull() & (F.col("step_sec") != 900))
        .count()
    )

    limites_invalidos = (
        df_resstock.groupBy("bldg_id")
        .agg(
            F.min("timestamp_fin_local").alias("min_ts"),
            F.max("timestamp_fin_local").alias("max_ts"),
        )
        .filter(
            (F.col("min_ts") != F.to_timestamp(F.lit("2018-01-01 00:15:00")))
            | (F.col("max_ts") != F.to_timestamp(F.lit("2019-01-01 00:00:00")))
        )
        .count()
    )

    metadata_duplicados = (
        df_metadata.groupBy("bldg_id").count().filter(F.col("count") != 1).count()
    )
    perfiles_sin_metadata = (
        df_resstock.select("bldg_id").distinct()
        .join(df_metadata.select("bldg_id").distinct(), "bldg_id", "left_anti")
        .count()
    )
    metadata_invalida = df_metadata.filter(
        F.col("estado").isNull()
        | F.col("tipo_vivienda").isNull()
        | F.col("peso_viviendas").isNull()
        | F.col("condado_codigo").isNull()
        | F.col("upgrade").isNull()
        | F.col("url").isNull()
        | (F.col("estado") == "")
        | (F.col("tipo_vivienda") == "")
        | (~F.col("estado").rlike("^[A-Z]{2}$"))
        | F.col("tipo_vivienda").isNull()
        | (F.col("peso_viviendas") <= 0)
        | F.isnan("peso_viviendas")
        | (F.col("peso_viviendas") == float("inf"))
        | (F.col("peso_viviendas") == float("-inf"))
    ).count()

    # Rango temporal y consumo
    stats = (
        df_resstock.select(
            F.min("timestamp_fin_local").alias("min_ts"),
            F.max("timestamp_fin_local").alias("max_ts"),
            F.min("electricidad_kwh").alias("min_kwh"),
            F.max("electricidad_kwh").alias("max_kwh"),
        )
        .first()
        .asDict()
    )

    # Cálculo coherente de fallos en cobertura por edificio
    conteo_fallidos_cobertura = sum(
        1 for v in conteo_por_edificio.values() if v != 35040
    )
    edificios_faltantes = max(0, 10 - len(conteo_por_edificio))
    cumplida_cobertura = bool(
        conteo_fallidos_cobertura == 0 and len(conteo_por_edificio) == 10
    )
    fallos_cobertura = (
        0 if cumplida_cobertura else max(1, conteo_fallidos_cobertura + edificios_faltantes)
    )

    cumplida_totales = bool(filas_totales == 350400 and edificios_unicos == 10)
    fallos_totales = 0 if cumplida_totales else max(1, abs(350400 - filas_totales) + abs(10 - edificios_unicos))

    # 7 reglas evaluadas
    reglas = [
        {
            "regla": "filas_y_edificios_esperados",
            "condicion": "filas == 350400 y edificios == 10",
            "cumplida": cumplida_totales,
            "fallos": int(fallos_totales),
        },
        {
            "regla": "cobertura_intervalos_anual_por_edificio",
            "condicion": "cada bldg_id tiene exactamente 35040 intervalos de 15 min (AMY 2018)",
            "cumplida": cumplida_cobertura,
            "fallos": int(fallos_cobertura),
        },
        {
            "regla": "ausencia_de_nulos",
            "condicion": "0 nulos en campos bldg_id, timestamp_fin_local y electricidad_kwh",
            "cumplida": bool(total_nulos == 0),
            "fallos": int(total_nulos),
        },
        {
            "regla": "energia_no_negativa_y_finita",
            "condicion": "electricidad_kwh >= 0.0, no nula, no NaN y no infinita",
            "cumplida": bool(no_finitos_o_negativos == 0),
            "fallos": int(no_finitos_o_negativos),
        },
        {
            "regla": "unicidad_clave_primaria",
            "condicion": "par (bldg_id, timestamp_fin_local) sin duplicados",
            "cumplida": bool(duplicados_pk == 0),
            "fallos": int(duplicados_pk),
        },
        {
            "regla": "continuidad_y_paso_15min_estricto",
            "condicion": "pasos consecutivos de exactamente 900s e inicio 2018-01-01 00:15 / fin 2019-01-01 00:00 por edificio",
            "cumplida": bool(pasos_invalidos_900s == 0 and limites_invalidos == 0),
            "fallos": int(pasos_invalidos_900s + limites_invalidos),
        },
        {
            "regla": "metadata_resstock_completa_y_univoca",
            "condicion": "cada perfil piloto tiene una fila válida en resstock_seleccion_propuesta.csv",
            "cumplida": bool(metadata_duplicados == 0 and perfiles_sin_metadata == 0 and metadata_invalida == 0),
            "fallos": int(metadata_duplicados + perfiles_sin_metadata + metadata_invalida),
        },
    ]

    return {
        "fuente": "resstock_perfiles_piloto.parquet",
        "filas_leidas": int(filas_totales),
        "edificios_unicos": int(edificios_unicos),
        "conteo_por_edificio": conteo_por_edificio,
        "nulos_por_columna": {k: int(v) for k, v in nulls.items()},
        "rango_temporal": {
            "inicio": str(stats["min_ts"]),
            "fin": str(stats["max_ts"]),
        },
        "rango_consumo_kwh": {
            "minimo": float(stats["min_kwh"]),
            "maximo": float(stats["max_kwh"]),
        },
        "reglas": reglas,
        "advertencias": [],
    }


def execute_eia_qc(df_eia) -> Dict[str, Any]:
    """Ejecuta 7 controles de calidad sobre el dataset mensual de EIA."""
    from pyspark.sql import functions as F

    filas_totales = df_eia.count()
    estados_unicos = df_eia.select("estado").distinct().count()

    conteo_estado_dato = {
        row["estado_dato"]: int(row["count"])
        for row in df_eia.groupBy("estado_dato").count().collect()
    }

    # Revisión de nulos en todas las columnas (captura nulos por parseo en modo PERMISSIVE)
    eia_cols = ["periodo", "estado", "sector", "estado_dato", "ventas_mwh"]
    null_exprs = [
        F.sum(F.when(F.col(c).isNull(), 1).otherwise(0)).alias(c)
        for c in eia_cols
    ]
    nulls = df_eia.select(null_exprs).first().asDict()
    total_nulos = int(sum(nulls.values()))

    # Revisión de formato de periodo: regex estricto YYYY-MM con mes 01-12
    # y validación de fecha parseable mediante to_date
    periodos_invalidos = df_eia.filter(
        (~F.col("periodo").rlike("^[0-9]{4}-(0[1-9]|1[0-2])$"))
        | (F.to_date(F.concat(F.col("periodo"), F.lit("-01")), "yyyy-MM-dd").isNull())
    ).count()

    # Sector debe ser RES
    sectores_no_res = df_eia.filter(F.col("sector") != "RES").count()

    # Estado dato debe ser Final o Preliminary
    estados_dato_invalidos = df_eia.filter(
        ~F.col("estado_dato").isin("Final", "Preliminary")
    ).count()

    # Ventas no negativas y finitas (no nulo, no NaN, no inf)
    ventas_invalidas = df_eia.filter(
        (F.col("ventas_mwh") < 0.0)
        | F.col("ventas_mwh").isNull()
        | F.isnan("ventas_mwh")
        | (F.col("ventas_mwh") == float("inf"))
        | (F.col("ventas_mwh") == float("-inf"))
    ).count()

    # Unicidad PK (periodo, estado, sector)
    duplicados_pk = (
        df_eia.groupBy("periodo", "estado", "sector")
        .count()
        .filter(F.col("count") > 1)
        .count()
    )

    stats = (
        df_eia.select(
            F.min("periodo").alias("periodo_min"),
            F.max("periodo").alias("periodo_max"),
            F.min("ventas_mwh").alias("ventas_min"),
            F.max("ventas_mwh").alias("ventas_max"),
        )
        .first()
        .asDict()
    )

    cumplida_totales = bool(filas_totales == 5304 and estados_unicos == 51)
    fallos_totales = 0 if cumplida_totales else max(1, abs(5304 - filas_totales) + abs(51 - estados_unicos))

    # 7 reglas evaluadas
    reglas = [
        {
            "regla": "conteos_totales_esperados",
            "condicion": "filas == 5304 y estados == 51 (50 estados + DC)",
            "cumplida": cumplida_totales,
            "fallos": int(fallos_totales),
        },
        {
            "regla": "ausencia_de_nulos_en_esquema",
            "condicion": "0 nulos en todas las columnas (periodo, estado, sector, estado_dato, ventas_mwh)",
            "cumplida": bool(total_nulos == 0),
            "fallos": total_nulos,
        },
        {
            "regla": "formato_periodo_y_mes_valido",
            "condicion": "periodo cumple regex ^[0-9]{4}-(0[1-9]|1[0-2])$ y fecha de primer día parseable",
            "cumplida": bool(periodos_invalidos == 0),
            "fallos": int(periodos_invalidos),
        },
        {
            "regla": "sector_exclusivo_residencial",
            "condicion": "sector == 'RES' en todas las filas",
            "cumplida": bool(sectores_no_res == 0),
            "fallos": int(sectores_no_res),
        },
        {
            "regla": "estado_dato_valido",
            "condicion": "estado_dato pertenece a {'Final', 'Preliminary'}",
            "cumplida": bool(estados_dato_invalidos == 0),
            "fallos": int(estados_dato_invalidos),
        },
        {
            "regla": "ventas_no_negativas_y_finitas",
            "condicion": "ventas_mwh >= 0.0, no nulo, no NaN y no infinito",
            "cumplida": bool(ventas_invalidas == 0),
            "fallos": int(ventas_invalidas),
        },
        {
            "regla": "unicidad_clave_primaria",
            "condicion": "tupla (periodo, estado, sector) sin duplicados",
            "cumplida": bool(duplicados_pk == 0),
            "fallos": int(duplicados_pk),
        },
    ]

    return {
        "fuente": "eia_residencial_mensual.csv",
        "filas_leidas": int(filas_totales),
        "estados_unicos": int(estados_unicos),
        "distribucion_estado_dato": conteo_estado_dato,
        "nulos_por_columna": {k: int(v) for k, v in nulls.items()},
        "rango_periodos": {
            "minimo": str(stats["periodo_min"]),
            "maximo": str(stats["periodo_max"]),
        },
        "rango_ventas_mwh": {
            "minimo": float(stats["ventas_min"]),
            "maximo": float(stats["ventas_max"]),
        },
        "reglas": reglas,
        "advertencias": [],
    }


def execute_clima_qc(df_clima) -> Dict[str, Any]:
    """Ejecuta 7 controles de calidad sobre la muestra horaria de clima."""
    from pyspark.sql import functions as F
    from pyspark.sql.window import Window

    filas_totales = df_clima.count()
    puntos_unicos = df_clima.select("punto_id").distinct().count()

    conteo_puntos = {
        row["punto_id"]: int(row["count"])
        for row in df_clima.groupBy("punto_id").count().collect()
    }

    # Revisión de nulos en todas las columnas
    clima_cols = [
        "punto_id",
        "estado",
        "latitude_solicitada",
        "longitude_solicitada",
        "latitude_celda",
        "longitude_celda",
        "timestamp_utc",
        "temperatura_c",
        "modelo",
    ]
    null_exprs = [
        F.sum(F.when(F.col(c).isNull(), 1).otherwise(0)).alias(c)
        for c in clima_cols
    ]
    nulls = df_clima.select(null_exprs).first().asDict()
    total_nulos = int(sum(nulls.values()))

    # Modelo ERA5-Land
    modelos_invalidos = df_clima.filter(F.col("modelo") != "ERA5-Land").count()

    # Rango físico de temperatura en °C (-60 a +60 °C), finita
    temperatura_invalida = df_clima.filter(
        (F.col("temperatura_c") < -60.0)
        | (F.col("temperatura_c") > 60.0)
        | F.col("temperatura_c").isNull()
        | F.isnan("temperatura_c")
        | (F.col("temperatura_c") == float("inf"))
        | (F.col("temperatura_c") == float("-inf"))
    ).count()

    # Coordenadas geográficas dentro de rangos físicos válidos:
    # latitud [-90, 90], longitud [-180, 180], no nulas ni infinitas
    coords_invalidas = df_clima.filter(
        F.col("latitude_solicitada").isNull()
        | F.col("longitude_solicitada").isNull()
        | F.col("latitude_celda").isNull()
        | F.col("longitude_celda").isNull()
        | (F.col("latitude_solicitada") < -90.0)
        | (F.col("latitude_solicitada") > 90.0)
        | (F.col("latitude_celda") < -90.0)
        | (F.col("latitude_celda") > 90.0)
        | (F.col("longitude_solicitada") < -180.0)
        | (F.col("longitude_solicitada") > 180.0)
        | (F.col("longitude_celda") < -180.0)
        | (F.col("longitude_celda") > 180.0)
        | F.isnan("latitude_solicitada")
        | F.isnan("longitude_solicitada")
        | F.isnan("latitude_celda")
        | F.isnan("longitude_celda")
        | (F.col("latitude_solicitada") == float("inf"))
        | (F.col("latitude_solicitada") == float("-inf"))
        | (F.col("longitude_solicitada") == float("inf"))
        | (F.col("longitude_solicitada") == float("-inf"))
    ).count()

    # Unicidad PK (punto_id, timestamp_utc)
    duplicados_pk = (
        df_clima.groupBy("punto_id", "timestamp_utc")
        .count()
        .filter(F.col("count") > 1)
        .count()
    )

    # Continuidad temporal horaria: paso estricto de 3600 s y límites (168 h por punto)
    w_clima = Window.partitionBy("punto_id").orderBy("timestamp_utc")
    step_sec_clima = (
        F.unix_timestamp(F.col("timestamp_utc"))
        - F.unix_timestamp(F.lag("timestamp_utc").over(w_clima))
    )
    pasos_invalidos_3600s = (
        df_clima.withColumn("step_sec", step_sec_clima)
        .filter(F.col("step_sec").isNotNull() & (F.col("step_sec") != 3600))
        .count()
    )

    limites_invalidos_clima = (
        df_clima.groupBy("punto_id")
        .agg(
            F.min("timestamp_utc").alias("min_ts"),
            F.max("timestamp_utc").alias("max_ts"),
        )
        .filter(
            (F.col("min_ts") != F.to_timestamp(F.lit("2018-01-01 00:00:00")))
            | (F.col("max_ts") != F.to_timestamp(F.lit("2018-01-07 23:00:00")))
        )
        .count()
    )

    stats = (
        df_clima.select(
            F.min("timestamp_utc").alias("min_ts"),
            F.max("timestamp_utc").alias("max_ts"),
            F.min("temperatura_c").alias("min_temp"),
            F.max("temperatura_c").alias("max_temp"),
        )
        .first()
        .asDict()
    )

    puntos_fallidos_conteo = sum(1 for v in conteo_puntos.values() if v != 168)
    cumplida_clima_totales = bool(
        filas_totales == 336
        and puntos_unicos == 2
        and puntos_fallidos_conteo == 0
    )
    fallos_clima_totales = (
        0
        if cumplida_clima_totales
        else max(1, puntos_fallidos_conteo + abs(336 - filas_totales) + abs(2 - puntos_unicos))
    )

    # 7 reglas evaluadas
    reglas = [
        {
            "regla": "conteos_totales_y_puntos_esperados",
            "condicion": "filas == 336 y puntos == 2 (168 h por punto, 7 días)",
            "cumplida": cumplida_clima_totales,
            "fallos": int(fallos_clima_totales),
        },
        {
            "regla": "ausencia_de_nulos_en_esquema",
            "condicion": "0 nulos en todas las columnas de la muestra de clima",
            "cumplida": bool(total_nulos == 0),
            "fallos": total_nulos,
        },
        {
            "regla": "modelo_meteorologico_declarado",
            "condicion": "modelo == 'ERA5-Land'",
            "cumplida": bool(modelos_invalidos == 0),
            "fallos": int(modelos_invalidos),
        },
        {
            "regla": "rango_fisico_temperatura",
            "condicion": "-60.0 <= temperatura_c <= 60.0, no nula y finita",
            "cumplida": bool(temperatura_invalida == 0),
            "fallos": int(temperatura_invalida),
        },
        {
            "regla": "coordenadas_completas_y_en_rango",
            "condicion": "latitudes [-90, 90] y longitudes [-180, 180] presentes, no nulas y finitas",
            "cumplida": bool(coords_invalidas == 0),
            "fallos": int(coords_invalidas),
        },
        {
            "regla": "unicidad_clave_primaria",
            "condicion": "tupla (punto_id, timestamp_utc) sin duplicados",
            "cumplida": bool(duplicados_pk == 0),
            "fallos": int(duplicados_pk),
        },
        {
            "regla": "continuidad_temporal_horaria_168h",
            "condicion": "pasos consecutivos de exactamente 3600s e inicio 2018-01-01 00:00Z / fin 2018-01-07 23:00Z por punto",
            "cumplida": bool(pasos_invalidos_3600s == 0 and limites_invalidos_clima == 0),
            "fallos": int(pasos_invalidos_3600s + limites_invalidos_clima),
        },
    ]

    advertencias = [
        "Muestra meteorológica preservada en capa Silver desacoplada. "
        "No se efectúa join espacial ni temporal con perfiles de consumo, "
        "conforme a la decisión de contrato v1."
    ]

    return {
        "fuente": "clima_open_meteo_muestra.csv",
        "filas_leidas": int(filas_totales),
        "puntos_unicos": int(puntos_unicos),
        "conteo_por_punto": conteo_puntos,
        "nulos_por_columna": {k: int(v) for k, v in nulls.items()},
        "rango_temporal_utc": {
            "inicio": str(stats["min_ts"]),
            "fin": str(stats["max_ts"]),
        },
        "rango_temperatura_c": {
            "minimo": float(stats["min_temp"]),
            "maximo": float(stats["max_temp"]),
        },
        "reglas": reglas,
        "advertencias": advertencias,
    }


def transform_silver_dataframes(
    df_resstock, df_metadata, df_eia, df_clima, now_utc_str: str
) -> Tuple[Any, Any, Any]:
    """Transforma los DataFrames a su formato Silver canónico según contrato v1.

    Implementa nombres canónicos:
    - ResStock: timestamp_end_est, electricity_kwh, bldg_id, interval_minutes,
      state_code, housing_type y profile_weight, enriquecidos desde el índice
      versionado y validados contra los IDs presentes en el Parquet.
    - EIA: period, state_code, sector, data_status, sales_mwh.
    - Clima: punto_id, state_code, latitude_solicitada, longitude_solicitada,
      latitude_celda, longitude_celda, timestamp_utc, temperatura_c, modelo.

    quality_flags implementa semántica a nivel de fila evaluando anomalías individuales.
    """
    from pyspark.sql import functions as F
    from pyspark.sql.types import DoubleType, LongType

    # 1. Silver ResStock
    flags_resstock_expr = F.expr(
        "filter(array("
        "case when electricidad_kwh < 0.0 then 'NEGATIVE_ENERGY' end, "
        "case when isnan(electricidad_kwh) then 'NAN_ENERGY' end, "
        "case when electricidad_kwh is null then 'NULL_ENERGY' end"
        "), x -> x is not null)"
    )

    silver_resstock = df_resstock.join(df_metadata, "bldg_id", "inner").select(
        F.lit("resstock_2025r1_amy2018_upgrade0_pilot").alias("source_dataset_id"),
        F.col("bldg_id").cast(LongType()).alias("bldg_id"),
        F.col("estado").alias("state_code"),
        F.col("tipo_vivienda").alias("housing_type"),
        F.col("peso_viviendas").alias("profile_weight"),
        F.col("timestamp_fin_local").alias("timestamp_end_est"),
        F.lit(15).alias("interval_minutes"),
        F.col("electricidad_kwh").cast(DoubleType()).alias("electricity_kwh"),
        flags_resstock_expr.alias("quality_flags"),
        F.lit(now_utc_str).alias("ingestion_timestamp_utc"),
    )

    # 2. Silver EIA
    flags_eia_expr = F.expr(
        "filter(array("
        "case when ventas_mwh < 0.0 then 'NEGATIVE_SALES' end, "
        "case when ventas_mwh is null then 'NULL_SALES' end, "
        "case when isnan(ventas_mwh) then 'NAN_SALES' end, "
        "case when sector != 'RES' then 'INVALID_SECTOR' end, "
        "case when not estado_dato in ('Final', 'Preliminary') then 'INVALID_STATUS' end, "
        "case when not periodo rlike '^[0-9]{4}-(0[1-9]|1[0-2])$' then 'INVALID_PERIOD' end"
        "), x -> x is not null)"
    )

    silver_eia = df_eia.select(
        F.lit("eia861m_sales_monthly").alias("source_dataset_id"),
        F.col("periodo").alias("period"),
        F.col("estado").alias("state_code"),
        F.col("sector"),
        F.col("estado_dato").alias("data_status"),
        F.col("ventas_mwh").cast(DoubleType()).alias("sales_mwh"),
        flags_eia_expr.alias("quality_flags"),
        F.lit(now_utc_str).alias("ingestion_timestamp_utc"),
    )

    # 3. Silver Clima
    flags_clima_expr = F.expr(
        "filter(array("
        "case when temperatura_c < -60.0 or temperatura_c > 60.0 then 'OUT_OF_BOUNDS_TEMPERATURE' end, "
        "case when temperatura_c is null then 'NULL_TEMPERATURE' end, "
        "case when isnan(temperatura_c) then 'NAN_TEMPERATURE' end, "
        "case when latitude_solicitada < -90.0 or latitude_solicitada > 90.0 then 'INVALID_LATITUDE_SOLICITADA' end, "
        "case when longitude_solicitada < -180.0 or longitude_solicitada > 180.0 then 'INVALID_LONGITUDE_SOLICITADA' end, "
        "case when latitude_celda < -90.0 or latitude_celda > 90.0 then 'INVALID_LATITUDE_CELDA' end, "
        "case when longitude_celda < -180.0 or longitude_celda > 180.0 then 'INVALID_LONGITUDE_CELDA' end, "
        "case when modelo != 'ERA5-Land' then 'UNEXPECTED_MODEL' end, "
        "case when timestamp_utc is null then 'NULL_TIMESTAMP' end"
        "), x -> x is not null)"
    )

    silver_clima = df_clima.select(
        F.lit("openmeteo_era5land_hourly").alias("source_dataset_id"),
        F.col("punto_id"),
        F.col("estado").alias("state_code"),
        F.col("latitude_solicitada"),
        F.col("longitude_solicitada"),
        F.col("latitude_celda"),
        F.col("longitude_celda"),
        F.col("timestamp_utc"),
        F.col("temperatura_c"),
        F.col("modelo"),
        flags_clima_expr.alias("quality_flags"),
        F.lit(now_utc_str).alias("ingestion_timestamp_utc"),
    )

    return silver_resstock, silver_eia, silver_clima


def transform_gold_dataframes(
    silver_resstock, silver_eia
) -> Tuple[Any, Any]:
    """Genera los DataFrames Gold mensuales manteniendo separación estricta.

    Corrección de asignación temporal:
    El Parquet de ResStock registra la marca temporal de FIN de intervalo (15 min).
    Para asignar cada intervalo al mes en que efectivamente transcurrió su consumo
    (evitando un mes espurio 2019-01 para la marca 2019-01-01 00:00), se deriva
    el periodo restando 15 minutos al timestamp_end_est. Esto produce exactamente
    los 12 meses de 2018.
    """
    from pyspark.sql import functions as F

    # 1. Gold ResStock: periodo derivado restando 15 min a la marca de fin
    gold_resstock = (
        silver_resstock
        .withColumn(
            "source_period",
            F.substring(
                F.expr("cast(timestamp_end_est - INTERVAL 15 MINUTES as string)"),
                1,
                7,
            ),
        )
        .groupBy("bldg_id", "source_period", "state_code", "housing_type", "profile_weight")
        .agg(
            F.round(F.sum("electricity_kwh"), 4).alias("kwh_month"),
            F.count(F.lit(1)).alias("n_intervals"),
        )
        .orderBy("bldg_id", "source_period")
    )

    # 2. Gold EIA: agregado mensual oficial de ventas residenciales
    gold_eia = (
        silver_eia
        .groupBy("period", "state_code", "data_status")
        .agg(
            F.round(F.sum("sales_mwh"), 2).alias("sales_mwh"),
        )
        .orderBy("state_code", "period")
    )

    return gold_resstock, gold_eia


def build_quality_report_dict(
    spark_version: str,
    real_input: str,
    real_output: str,
    now_utc_str: str,
    qc_resstock: Dict[str, Any],
    qc_eia: Dict[str, Any],
    qc_clima: Dict[str, Any],
    source_inventory: List[Dict[str, Any]],
    silver_paths: Dict[str, str],
    gold_paths: Dict[str, str],
    publication_blocked: bool,
) -> Dict[str, Any]:
    """Construye el diccionario de reporte de calidad según reglas evaluadas."""
    all_rules: List[Dict[str, Any]] = (
        qc_resstock["reglas"] + qc_eia["reglas"] + qc_clima["reglas"]
    )
    total_rules = len(all_rules)
    passed_rules = sum(1 for r in all_rules if r["cumplida"])
    failed_rules = total_rules - passed_rules

    all_warnings = (
        qc_resstock["advertencias"]
        + qc_eia["advertencias"]
        + qc_clima["advertencias"]
        + [
            "El manifiesto de datos registra fecha de integración, pero no la hora UTC exacta de descarga de las fuentes."
        ]
    )

    if failed_rules > 0:
        estado_global = "REJECTED"
    elif len(all_warnings) > 0:
        estado_global = "VALID_WITH_WARNINGS"
    else:
        estado_global = "VALID"

    return {
        "metadatos_ejecucion": {
            "version_spark": spark_version,
            "version_job": "1.4.0",
            "schema_version": "1.0",
            "timestamp_ejecucion_utc": now_utc_str,
            "directorio_entrada": real_input,
            "directorio_salida": real_output,
        },
        "resumen_reglas": {
            "total_reglas_evaluadas": total_rules,
            "reglas_cumplidas": passed_rules,
            "reglas_fallidas": failed_rules,
            "total_advertencias": len(all_warnings),
            "estado_global": estado_global,
            "bloqueo_publicacion_capas": publication_blocked,
        },
        "separacion_metodologica": {
            "resstock_modelado": (
                "10 perfiles físicos de vivienda individual (AMY 2018). "
                "Sin state_code ni pesos poblacionales en Parquet piloto. "
                "Intervalos agregados a 12 meses 2018 por duración efectiva. "
                "No representan totales estatales ni nacionales."
            ),
            "eia_ventas_mensuales": (
                "Ventas agregadas oficiales reportadas por utilities para 51 estados (EIA-861M). "
                "Representan la totalidad del sector residencial."
            ),
            "clima_reanalisis": (
                "Muestra de reanálisis ERA5-Land en 2 puntos geográficos de Colorado. "
                "Desacoplada del consumo energético."
            ),
            "regla_de_oro": (
                "No se realiza join por perfil entre ResStock y EIA ni se interpreta su razón "
                "como métrica de precisión, preservando la validez metodológica de cada fuente."
            ),
        },
        "controles_por_fuente": {
            "resstock": qc_resstock,
            "eia": qc_eia,
            "clima": qc_clima,
        },
        "fuentes_entrada": source_inventory,
        "salidas_escritas": {
            "silver": silver_paths,
            "gold": gold_paths,
        },
    }


def publish_atomically_via_sibling_staging(
    silver_resstock,
    silver_eia,
    silver_clima,
    gold_resstock,
    gold_eia,
    reporte_dict: Dict[str, Any],
    table_row_counts: Dict[str, int],
    real_output: str,
) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Escribe todo el árbol en un directorio hermano temporal y lo publica atómicamente.

    Garantiza atomicidad completa: crea staging_dir con tempfile.mkdtemp en el mismo
    sistema de archivos (directorio padre de real_output), escribe tablas Parquet y
    reporte_calidad.json, y reemplaza atómicamente la ruta destino mediante os.replace.
    Si ocurre cualquier fallo antes de os.replace, solo se limpia la ruta temporal
    creada por esta llamada sin tocar destinos preexistentes.
    """
    parent_dir = os.path.dirname(real_output)
    os.makedirs(parent_dir, exist_ok=True)

    staging_dir = tempfile.mkdtemp(
        prefix=f".{os.path.basename(real_output)}_staging_",
        dir=parent_dir,
    )

    try:
        # Rutas dentro del staging
        stg_silver_resstock = os.path.join(staging_dir, "silver", "resstock_profile_interval")
        stg_silver_eia = os.path.join(staging_dir, "silver", "eia_residential_sales_monthly")
        stg_silver_clima = os.path.join(staging_dir, "silver", "climate_hourly_point")
        stg_gold_resstock = os.path.join(staging_dir, "gold", "gold_resstock_monthly")
        stg_gold_eia = os.path.join(staging_dir, "gold", "gold_eia_monthly")
        stg_report_path = os.path.join(staging_dir, "reporte_calidad.json")

        # 1. Escritura Parquet en staging
        silver_resstock.write.mode("errorifexists").parquet(stg_silver_resstock)
        silver_eia.write.mode("errorifexists").parquet(stg_silver_eia)
        silver_clima.write.mode("errorifexists").parquet(stg_silver_clima)
        gold_resstock.write.mode("errorifexists").parquet(stg_gold_resstock)
        gold_eia.write.mode("errorifexists").parquet(stg_gold_eia)

        table_dirs = {
            "silver.resstock_profile_interval": stg_silver_resstock,
            "silver.eia_residential_sales_monthly": stg_silver_eia,
            "silver.climate_hourly_point": stg_silver_clima,
            "gold_resstock_monthly": stg_gold_resstock,
            "gold_eia_monthly": stg_gold_eia,
        }
        output_inventory = []
        for table_name, table_dir in table_dirs.items():
            files = []
            for root, _, filenames in os.walk(table_dir):
                for filename in sorted(filenames):
                    if not filename.endswith(".parquet"):
                        continue
                    full_path = os.path.join(root, filename)
                    digest = hashlib.sha256()
                    size_bytes = 0
                    with open(full_path, "rb") as parquet_file:
                        for chunk in iter(lambda: parquet_file.read(1024 * 1024), b""):
                            digest.update(chunk)
                            size_bytes += len(chunk)
                    files.append(
                        {
                            "file": os.path.relpath(full_path, staging_dir),
                            "bytes": size_bytes,
                            "sha256": digest.hexdigest(),
                        }
                    )
            output_inventory.append(
                {
                    "table": table_name,
                    "row_count": table_row_counts[table_name],
                    "files": files,
                }
            )

        reporte_dict["salidas_escritas"]["inventario_gold_silver"] = output_inventory
        run_manifest = {
            "manifest_version": "1.0",
            "schema_version": "1.0",
            "transform_version": "1.4.0",
            "quality_status": reporte_dict["resumen_reglas"]["estado_global"],
            "source_inventory": reporte_dict["fuentes_entrada"],
            "output_inventory": output_inventory,
        }
        with open(os.path.join(staging_dir, "manifiesto_ejecucion.json"), "w", encoding="utf-8") as f:
            json.dump(run_manifest, f, indent=2, ensure_ascii=False)

        # 2. Inclusión del reporte de calidad antes del reemplazo atómico
        with open(stg_report_path, "w", encoding="utf-8") as f:
            json.dump(reporte_dict, f, indent=2, ensure_ascii=False)

        # 3. Publicación atómica mediante os.replace
        os.replace(staging_dir, real_output)

        final_silver_paths = {
            "silver.resstock_profile_interval": os.path.join(real_output, "silver", "resstock_profile_interval"),
            "silver.eia_residential_sales_monthly": os.path.join(real_output, "silver", "eia_residential_sales_monthly"),
            "silver.climate_hourly_point": os.path.join(real_output, "silver", "climate_hourly_point"),
        }
        final_gold_paths = {
            "gold_resstock_monthly": os.path.join(real_output, "gold", "gold_resstock_monthly"),
            "gold_eia_monthly": os.path.join(real_output, "gold", "gold_eia_monthly"),
        }
        return final_silver_paths, final_gold_paths

    finally:
        # Solo limpia el directorio temporal creado por esta llamada si no fue renombrado
        if os.path.exists(staging_dir):
            shutil.rmtree(staging_dir, ignore_errors=True)


def main() -> int:
    """Punto de entrada principal para la ejecución del job Spark."""
    args = parse_arguments()

    print("=" * 70)
    print("Iniciando Job PySpark: Piloto de Consumo Eléctrico Residencial")
    print(f"Directorio de entrada: {args.input}")
    print(f"Directorio de salida:  {args.output}")
    print("=" * 70)

    # 1. Validación de rutas seguras y no destructivas (con realpath)
    real_input, real_output = validate_paths(args.input, args.output)

    # 2. Inicialización de Spark
    spark = build_spark_session(args.app_name, args.master)
    spark_version = spark.version
    now_utc_str = datetime.now(timezone.utc).isoformat()
    print(f"Sesión Spark iniciada exitosamente (Versión: {spark_version})")

    try:
        source_inventory = build_source_inventory(real_input)
        # 3. Definición de esquemas CSV
        schema_eia, schema_clima, schema_resstock_metadata = define_schemas()

        # 4. Rutas a archivos piloto
        resstock_path = os.path.join(real_input, "resstock_perfiles_piloto.parquet")
        eia_path = os.path.join(real_input, "eia_residencial_mensual.csv")
        clima_path = os.path.join(real_input, "clima_open_meteo_muestra.csv")
        metadata_path = os.path.join(real_input, "resstock_seleccion_propuesta.csv")

        for p in [resstock_path, eia_path, clima_path, metadata_path]:
            if not os.path.exists(p):
                raise FileNotFoundError(f"Archivo piloto no encontrado: {p}")

        # 5. Lectura de datasets con TimestampNTZ y esquemas explícitos
        print("Leyendo archivos fuente...")
        df_resstock = spark.read.parquet(resstock_path)
        df_metadata = (
            spark.read.schema(schema_resstock_metadata)
            .option("header", True)
            .csv(metadata_path)
        )
        df_eia = (
            spark.read.schema(schema_eia)
            .option("header", True)
            .csv(eia_path)
        )
        df_clima = (
            spark.read.schema(schema_clima)
            .option("header", True)
            .option("timestampFormat", "yyyy-MM-dd'T'HH:mm:ssX")
            .csv(clima_path)
        )

        # 6. Ejecución de Controles de Calidad (21 reglas en total)
        print("Ejecutando controles de calidad de datos (21 reglas)...")
        qc_resstock = execute_resstock_qc(df_resstock, df_metadata)
        qc_eia = execute_eia_qc(df_eia)
        qc_clima = execute_clima_qc(df_clima)

        all_rules = qc_resstock["reglas"] + qc_eia["reglas"] + qc_clima["reglas"]
        failed_rules = sum(1 for r in all_rules if not r["cumplida"])

        # 7. Gate de Publicación: bloquear publicación si hay reglas fallidas
        if failed_rules > 0:
            print("=" * 70)
            print("ATENCIÓN: Se detectaron reglas de calidad fallidas.")
            print(f"Total de reglas fallidas: {failed_rules}")
            print("BLOQUEO DE PUBLICACIÓN ACTIVO: No se generarán tablas Silver ni Gold.")
            print("=" * 70)

            # Genera y escribe reporte con estado REJECTED y salidas vacías
            os.makedirs(real_output, exist_ok=True)
            reporte_dict = build_quality_report_dict(
                spark_version,
                real_input,
                real_output,
                now_utc_str,
                qc_resstock,
                qc_eia,
                qc_clima,
                source_inventory,
                silver_paths={},
                gold_paths={},
                publication_blocked=True,
            )
            report_path = os.path.join(real_output, "reporte_calidad.json")
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(reporte_dict, f, indent=2, ensure_ascii=False)

            print(f"Reporte de auditoría emitido en: {report_path}")
            return 1

        # 8. Transformaciones canónicas
        print("Controles de calidad superados. Generando transformaciones Silver canónicas...")
        silver_resstock, silver_eia, silver_clima = transform_silver_dataframes(
            df_resstock, df_metadata, df_eia, df_clima, now_utc_str
        )

        print("Generando agregaciones Gold mensuales...")
        gold_resstock, gold_eia = transform_gold_dataframes(
            silver_resstock, silver_eia
        )

        table_row_counts = {
            "silver.resstock_profile_interval": silver_resstock.count(),
            "silver.eia_residential_sales_monthly": silver_eia.count(),
            "silver.climate_hourly_point": silver_clima.count(),
            "gold_resstock_monthly": gold_resstock.count(),
            "gold_eia_monthly": gold_eia.count(),
        }

        # 9. Construcción de reporte y publicación atómica con staging hermano
        final_silver_paths = {
            "silver.resstock_profile_interval": os.path.join(real_output, "silver", "resstock_profile_interval"),
            "silver.eia_residential_sales_monthly": os.path.join(real_output, "silver", "eia_residential_sales_monthly"),
            "silver.climate_hourly_point": os.path.join(real_output, "silver", "climate_hourly_point"),
        }
        final_gold_paths = {
            "gold_resstock_monthly": os.path.join(real_output, "gold", "gold_resstock_monthly"),
            "gold_eia_monthly": os.path.join(real_output, "gold", "gold_eia_monthly"),
        }
        reporte_dict = build_quality_report_dict(
            spark_version,
            real_input,
            real_output,
            now_utc_str,
            qc_resstock,
            qc_eia,
            qc_clima,
            source_inventory,
            silver_paths=final_silver_paths,
            gold_paths=final_gold_paths,
            publication_blocked=False,
        )

        print("Publicando capas y reporte atómicamente mediante staging hermano con tempfile.mkdtemp...")
        publish_atomically_via_sibling_staging(
            silver_resstock,
            silver_eia,
            silver_clima,
            gold_resstock,
            gold_eia,
            reporte_dict,
            table_row_counts,
            real_output,
        )

        print("=" * 70)
        print("Ejecución finalizada exitosamente.")
        print(f"Estado global de calidad: {reporte_dict['resumen_reglas']['estado_global']}")
        print(
            f"Reglas cumplidas: {reporte_dict['resumen_reglas']['reglas_cumplidas']}/"
            f"{reporte_dict['resumen_reglas']['total_reglas_evaluadas']}"
        )
        print(f"Reporte emitido en: {os.path.join(real_output, 'reporte_calidad.json')}")
        print("=" * 70)

        return 0

    finally:
        spark.stop()


if __name__ == "__main__":
    sys.exit(main())
