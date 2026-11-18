
import os
import sys
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

os.environ["PYSPARK_PYTHON"] = sys.executable

BASE = Path(__file__).resolve().parents[2]

RUTA_RESSTOCK = (
    BASE / "data/gold/resstock_consumo_mensual"
)

RUTA_EIA = (
    BASE / "data/gold/eia_ventas_residenciales_mensual"
)

RUTA_COMPARACION = (
    BASE / "data/gold/comparacion_resstock_eia_mensual"
)

spark = (
    SparkSession.builder
    .appName("ComparacionResStockEIA")
    .master("local[*]")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("ERROR")

try:
    print("\n=== COMPARACION RESSTOCK VS EIA ===")

    # Leer ambas capas Gold
    resstock = spark.read.parquet(str(RUTA_RESSTOCK))
    eia = spark.read.parquet(str(RUTA_EIA))

    # Seleccionar los campos relevantes
    resstock = resstock.select(
        "anio",
        "mes",
        "estado",
        "tipo_vivienda",
        F.col("consumo_mwh").alias("resstock_mwh")
    )

    eia = eia.select(
        "anio",
        "mes",
        "estado",
        "sector",
        F.col("ventas_mwh").alias("eia_mwh")
    )

    print("Meses ResStock:", resstock.count())
    print("Meses EIA:", eia.count())

    # Comprobar que cada fuente tiene una fila por mes
    claves = ["anio", "mes", "estado"]

    for nombre, datos in [
        ("ResStock", resstock),
        ("EIA", eia)
    ]:
        duplicados = (
            datos.groupBy(*claves)
            .count()
            .filter(F.col("count") > 1)
            .count()
        )

        if duplicados > 0:
            raise ValueError(
                f"{nombre}: meses duplicados"
            )

        meses = {
            r["mes"]
            for r in datos.select("mes").collect()
        }

        if (
            datos.count() != 12
            or meses != set(range(1, 13))
        ):
            raise ValueError(
                f"{nombre}: se esperaban 12 meses"
            )

        fuera_de_periodo = datos.filter(
            (F.col("anio") != 2018)
            | (F.col("estado") != "CO")
        ).count()

        if fuera_de_periodo:
            raise ValueError(
                f"{nombre}: estado o anio inesperado"
            )

    # Relacionar por el mismo estado, anio y mes
    comparacion = (
        resstock.join(
            eia,
            on=claves,
            how="inner"
        )
        .withColumn(
            "diferencia_mwh",
            F.col("resstock_mwh") - F.col("eia_mwh")
        )
        .withColumn(
            "relacion_porcentaje",
            F.when(
                F.col("eia_mwh") > 0,
                F.col("resstock_mwh")
                / F.col("eia_mwh") * 100.0
            )
        )
    )

    total_meses = comparacion.count()

    if total_meses != 12:
        raise ValueError(
            "La comparacion no contiene 12 meses"
        )

    if comparacion.filter(
        F.col("resstock_mwh").isNull()
        | F.col("eia_mwh").isNull()
        | (F.col("resstock_mwh") < 0)
        | (F.col("eia_mwh") <= 0)
    ).count():
        raise ValueError("Valores de consumo invalidos")

    # Mostrar la comparacion mensual
    print("\n=== RESULTADOS MENSUALES ===")

    comparacion.select(
        "mes",
        F.round(
            F.col("resstock_mwh") / 1_000_000, 4
        ).alias("resstock_millones_mwh"),
        F.round(
            F.col("eia_mwh") / 1_000_000, 4
        ).alias("eia_millones_mwh"),
        F.round(
            "relacion_porcentaje", 2
        ).alias("relacion_pct")
    ).orderBy("mes").show(12, truncate=False)

    # Calcular los totales anuales
    totales = comparacion.agg(
        F.sum("resstock_mwh").alias("total_resstock"),
        F.sum("eia_mwh").alias("total_eia")
    ).first()

    total_resstock = totales["total_resstock"]
    total_eia = totales["total_eia"]

    relacion_anual = (
        total_resstock / total_eia * 100.0
    )

    print("\n=== COMPARACION ANUAL ===")
    print(f"ResStock: {total_resstock:,.2f} MWh")
    print(f"EIA: {total_eia:,.2f} MWh")
    print(f"Relacion anual: {relacion_anual:.2f}%")

    # Guardar la comparacion en Parquet
    (
        comparacion.coalesce(1)
        .write
        .mode("overwrite")
        .partitionBy("anio", "estado")
        .parquet(str(RUTA_COMPARACION))
    )

    # Verificar el archivo generado
    resultado = spark.read.parquet(
        str(RUTA_COMPARACION)
    )

    if resultado.count() != total_meses:
        raise ValueError(
            "No coinciden los registros guardados"
        )

    print("\n=== VERIFICACION ===")
    print("Registros guardados:", resultado.count())
    print("Destino:", RUTA_COMPARACION)

    print("\nCOMPARACION GENERADA CORRECTAMENTE")

finally:
    spark.stop()
