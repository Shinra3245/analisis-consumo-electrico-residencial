
import os
import sys
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from validar_resstock_registros import validar_registros_resstock

os.environ["PYSPARK_PYTHON"] = sys.executable

BASE = Path(__file__).resolve().parents[2]

RUTA_BRONZE = BASE / "data/bronze/resstock_co_2018"
RUTA_SILVER = BASE / "data/silver/resstock_co_2018"
RUTA_RECHAZADOS = BASE / "data/quality/resstock_co_2018_rechazados"

spark = (
    SparkSession.builder
    .appName("SilverResStock")
    .master("local[*]")
    .config("spark.sql.session.timeZone", "UTC")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("ERROR")

try:
    print("\n=== CAPA SILVER - RESSTOCK ===")

    bronze = spark.read.parquet(str(RUTA_BRONZE))

    print("Registros de entrada:", bronze.count())

    # Aplicar las reglas reutilizables de validacion
    datos = validar_registros_resstock(bronze)


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
        raise ValueError("No coinciden los conteos")

    # Guardar datos validos en Parquet
    (
        validos.drop("errores")
        .coalesce(2)
        .write
        .mode("overwrite")
        .partitionBy("anio", "estado")
        .parquet(str(RUTA_SILVER))
    )

    # Guardar registros rechazados con el motivo
    (
        rechazados.write
        .mode("overwrite")
        .parquet(str(RUTA_RECHAZADOS))
    )

    # Verificar que la salida sea legible
    silver = spark.read.parquet(str(RUTA_SILVER))

    if silver.count() != total_validos:
        raise ValueError("Error en conteo Silver")

    print("\n=== PRIMEROS REGISTROS SILVER ===")
    silver.select(
        "timestamp_inicio",
        "timestamp_fin",
        "consumo_kwh",
        "mes",
        "estado"
    ).orderBy("timestamp_inicio").show(5, truncate=False)

    print("\nCAPA SILVER GENERADA CORRECTAMENTE")

finally:
    spark.stop()
