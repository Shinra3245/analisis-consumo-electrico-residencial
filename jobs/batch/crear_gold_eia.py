
import os
import sys
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

os.environ["PYSPARK_PYTHON"] = sys.executable

BASE = Path(__file__).resolve().parents[2]

RUTA_SILVER = BASE / "data/silver/eia_co_2018"
RUTA_GOLD = BASE / "data/gold/eia_ventas_residenciales_mensual"

spark = (
    SparkSession.builder
    .appName("GoldEIA")
    .master("local[*]")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("ERROR")

try:
    print("\n=== CAPA GOLD - EIA ===", flush=True)

    # Leer los datos validados
    df = spark.read.parquet(str(RUTA_SILVER))

    total_entrada = df.count()
    print("Registros de entrada:", total_entrada)

    # Verificar que no existan meses duplicados
    duplicados = (
        df.groupBy("anio", "mes", "estado")
        .count()
        .filter(F.col("count") > 1)
        .count()
    )

    print("Meses duplicados:", duplicados)

    if duplicados > 0:
        raise ValueError("Existen meses duplicados")

    # Comprobar los 12 meses completos
    meses = {
        fila["mes"]
        for fila in df.select("mes").collect()
    }

    if meses != set(range(1, 13)):
        raise ValueError("Faltan meses de EIA")

    # Preparar los resultados Gold
    gold = (
        df.select(
            "anio",
            "mes",
            "estado",
            "estatus_dato",
            "fuente",
            "archivo_origen",
            F.col(
                "ventas_residenciales_mwh"
            ).alias("ventas_mwh")
        )
        .withColumn(
            "sector",
            F.lit("residencial")
        )
        .withColumn(
            "ventas_millones_mwh",
            F.col("ventas_mwh") / 1_000_000.0
        )
        .orderBy("anio", "mes")
    )

    print("\n=== VENTAS MENSUALES EIA ===")

    gold.select(
        "anio",
        "mes",
        "estado",
        F.round(
            "ventas_millones_mwh", 4
        ).alias("millones_mwh")
    ).show(12, truncate=False)

    # Calcular total anual
    total_anual = gold.agg(
        F.sum("ventas_mwh").alias("total_mwh")
    ).first()["total_mwh"]

    print("\n=== RESULTADO ANUAL EIA ===")
    print(f"Total MWh: {total_anual:,.2f}")
    print(
        f"Millones de MWh: "
        f"{total_anual / 1_000_000:.4f}"
    )

    # Guardar la capa Gold
    (
        gold.coalesce(1)
        .write
        .mode("overwrite")
        .partitionBy("anio", "estado")
        .parquet(str(RUTA_GOLD))
    )

    # Verificar los resultados almacenados
    resultado = spark.read.parquet(str(RUTA_GOLD))

    filas_salida = resultado.count()

    total_guardado = resultado.agg(
        F.sum("ventas_mwh").alias("total")
    ).first()["total"]

    if filas_salida != total_entrada:
        raise ValueError("No coinciden los registros")

    if abs(total_anual - total_guardado) > 0.01:
        raise ValueError("No coinciden las ventas")

    print("\n=== VERIFICACION GOLD ===")
    print("Registros de salida:", filas_salida)
    print("Destino:", RUTA_GOLD)

    print("\nCAPA GOLD EIA GENERADA CORRECTAMENTE")

finally:
    spark.stop()
