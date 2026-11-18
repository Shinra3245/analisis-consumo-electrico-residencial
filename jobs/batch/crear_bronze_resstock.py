
import os
import sys
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

os.environ["PYSPARK_PYTHON"] = sys.executable

# Rutas del proyecto
BASE = Path(__file__).resolve().parents[2]

RUTA_RAW = BASE / "data/raw/up00-co-single-family_detached.csv"
RUTA_BRONZE = BASE / "data/bronze/resstock_co_2018"

if not RUTA_RAW.is_file():
    raise FileNotFoundError(f"Archivo no encontrado: {RUTA_RAW}")

# Crear sesion Spark
spark = (
    SparkSession.builder
    .appName("BronzeResStock")
    .master("local[*]")
    .config("spark.sql.session.timeZone", "UTC")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("ERROR")

try:
    print("\n=== CAPA BRONZE - RESSTOCK ===", flush=True)

    # Leer el archivo original sin inferir tipos
    df = (
        spark.read
        .option("header", "true")
        .option("inferSchema", "false")
        .csv(str(RUTA_RAW))
    )

    filas_entrada = df.count()
    columnas_entrada = len(df.columns)

    print("Registros originales:", filas_entrada)
    print("Columnas originales:", columnas_entrada)

    # Agregar identificacion de la fuente
    bronze = (
        df.withColumn("_source", F.lit("ResStock"))
        .withColumn(
            "_source_file",
            F.lit(RUTA_RAW.name)
        )
    )

    # Guardar en formato Parquet
    bronze.coalesce(2).write \
        .mode("overwrite") \
        .parquet(str(RUTA_BRONZE))

    print("\nArchivo Parquet generado.")

    # Comprobar el resultado guardado
    resultado = spark.read.parquet(str(RUTA_BRONZE))
    filas_salida = resultado.count()

    print("Registros de salida:", filas_salida)
    print("Columnas de salida:", len(resultado.columns))
    print("Destino:", RUTA_BRONZE)

    if filas_entrada != filas_salida:
        raise ValueError("El conteo de filas no coincide")

    if columnas_entrada != 96:
        print("Advertencia: esquema distinto al esperado")

    print("\nCAPA BRONZE GENERADA CORRECTAMENTE")

finally:
    spark.stop()
