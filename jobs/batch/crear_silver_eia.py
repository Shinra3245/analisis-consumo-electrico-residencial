
import os
import sys
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from validar_eia_registros import validar_registros_eia


os.environ["PYSPARK_PYTHON"] = sys.executable

BASE = Path(__file__).resolve().parents[2]

RUTA_BRONZE = BASE / "data/bronze/eia_co_2018"
RUTA_SILVER = BASE / "data/silver/eia_co_2018"
RUTA_RECHAZADOS = BASE / "data/quality/eia_co_2018_rechazados"

spark = (
    SparkSession.builder
    .appName("SilverEIA")
    .master("local[*]")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("ERROR")

try:
    print("\n=== CAPA SILVER - EIA ===", flush=True)

    # Leer los datos de Bronze
    bronze = spark.read.parquet(str(RUTA_BRONZE))

    print("Registros de entrada:", bronze.count())

    # Aplicar las reglas de validacion reutilizables
    datos = validar_registros_eia(bronze)


    validos = datos.filter(F.col("errores") == "")
    rechazados = datos.filter(F.col("errores") != "")

    total_entrada = datos.count()
    total_validos = validos.count()
    total_rechazados = rechazados.count()

    print("\n=== RESULTADOS DE CALIDAD ===")
    print("Registros originales:", total_entrada)
    print("Registros validos:", total_validos)
    print("Registros rechazados:", total_rechazados)

    if total_entrada != total_validos + total_rechazados:
        raise ValueError("Los conteos no coinciden")

    # Comprobar los 12 meses antes de generar Silver
    meses = {
        fila["mes_num"]
        for fila in validos.select("mes_num").distinct().collect()
    }

    if meses != set(range(1, 13)):
        raise ValueError(
            "Faltan meses validos de EIA en 2018"
        )

    # Seleccionar esquema definitivo Silver
    silver = validos.select(
        F.col("anio_num").alias("anio"),
        F.col("mes_num").alias("mes"),
        "estado",
        "estatus_dato",
        F.col("ventas_mwh").alias(
            "ventas_residenciales_mwh"
        ),
        "fuente",
        "archivo_origen"
    )

    # Guardar registros validos
    (
        silver.coalesce(1)
        .write
        .mode("overwrite")
        .partitionBy("anio", "estado")
        .parquet(str(RUTA_SILVER))
    )

    # Guardar registros rechazados y sus motivos
    (
        rechazados.write
        .mode("overwrite")
        .parquet(str(RUTA_RECHAZADOS))
    )

    # Leer y comprobar el archivo Silver
    resultado = spark.read.parquet(str(RUTA_SILVER))

    if resultado.count() != total_validos:
        raise ValueError("Error en conteo Silver")

    print("\n=== DATOS SILVER EIA ===")

    resultado.select(
        "anio",
        "mes",
        "estado",
        "ventas_residenciales_mwh"
    ).orderBy("mes").show(12, truncate=False)

    # Calcular las ventas anuales
    total_anual = resultado.agg(
        F.sum("ventas_residenciales_mwh")
        .alias("total_mwh")
    ).first()["total_mwh"]

    print("\n=== TOTAL ANUAL EIA ===")
    print(f"Total MWh: {total_anual:,.2f}")
    print(f"Millones de MWh: {total_anual / 1_000_000:.4f}")

    print("\nCAPA SILVER EIA GENERADA CORRECTAMENTE")

finally:
    spark.stop()
