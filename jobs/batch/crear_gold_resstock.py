
import os
import sys
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

os.environ["PYSPARK_PYTHON"] = sys.executable

BASE = Path(__file__).resolve().parents[2]

RUTA_SILVER = BASE / "data/silver/resstock_co_2018"
RUTA_GOLD = BASE / "data/gold/resstock_consumo_mensual"

spark = (
    SparkSession.builder
    .appName("GoldResStock")
    .master("local[*]")
    .config("spark.sql.session.timeZone", "UTC")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("ERROR")

try:
    print("\n=== CAPA GOLD - RESSTOCK ===", flush=True)

    # Leer la capa Silver
    df = spark.read.parquet(str(RUTA_SILVER))

    total_entrada = df.count()
    print("Registros de entrada:", total_entrada)

    # Verificar duplicados de intervalos por grupo
    duplicados = (
        df.groupBy(
            "anio", "estado",
            "tipo_vivienda", "timestamp_inicio"
        )
        .count()
        .filter(F.col("count") > 1)
        .count()
    )

    print("Intervalos duplicados:", duplicados)

    if duplicados > 0:
        raise ValueError("Existen intervalos duplicados")

    # Agrupar el consumo por mes
    mensual = (
        df.groupBy(
            "anio",
            "mes",
            "estado",
            "tipo_vivienda"
        )
        .agg(
            F.count("*").alias("intervalos"),
            F.sum("consumo_kwh").alias("consumo_kwh"),
            F.min("modelos").alias("modelos_min"),
            F.max("modelos").alias("modelos_max"),
            F.min("viviendas_representadas").alias("viviendas_min"),
            F.max("viviendas_representadas").alias("viviendas_max")
        )
        .withColumn(
            "consumo_mwh",
            F.col("consumo_kwh") / 1000.0
        )
        .withColumn(
            "consumo_millones_mwh",
            F.col("consumo_kwh") / 1000000000.0
        )
        .orderBy("anio", "mes", "estado")
    )

    # Verificar que los metadatos sean constantes
    metadatos_invalidos = mensual.filter(
        (F.col("modelos_min") != F.col("modelos_max"))
        | (
            F.abs(
                F.col("viviendas_min")
                - F.col("viviendas_max")
            ) > 0.000001
        )
    ).count()

    if metadatos_invalidos:
        raise ValueError("Metadatos inconsistentes")

    # Comprobar que no se pierdan intervalos
    intervalos_gold = mensual.agg(
        F.sum("intervalos")
    ).first()[0]

    if intervalos_gold != total_entrada:
        raise ValueError("No coinciden los registros")

    print("\n=== CONSUMO MENSUAL ===")

    mensual.select(
        "anio",
        "mes",
        "intervalos",
        F.round(
            "consumo_millones_mwh", 4
        ).alias("millones_mwh")
    ).show(12, truncate=False)

    # Calcular total anual
    total_anual = mensual.agg(
        F.sum("consumo_mwh").alias("total_mwh")
    ).first()["total_mwh"]

    print("\n=== RESULTADO ANUAL ===")
    print(f"Total MWh: {total_anual:,.2f}")
    print(
        f"Millones de MWh: "
        f"{total_anual / 1000000:,.4f}"
    )

    # Guardar Gold en Parquet
    (
        mensual.coalesce(1)
        .write
        .mode("overwrite")
        .partitionBy("anio", "estado")
        .parquet(str(RUTA_GOLD))
    )

    # Verificar escritura
    resultado = spark.read.parquet(str(RUTA_GOLD))

    print("\nFilas Gold:", resultado.count())
    print("Destino:", RUTA_GOLD)

    print("\nCAPA GOLD GENERADA CORRECTAMENTE")

finally:
    spark.stop()
