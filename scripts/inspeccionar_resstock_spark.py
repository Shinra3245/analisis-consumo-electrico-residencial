
import os
import sys
from pathlib import Path
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

# Configurar Python del entorno virtual
os.environ["PYSPARK_PYTHON"] = sys.executable

# Ruta del archivo original
ruta = Path("data/raw/up00-co-single-family_detached.csv").resolve()

if not ruta.is_file():
    raise FileNotFoundError(f"No se encontro: {ruta}")

# Iniciar Spark
spark = (
    SparkSession.builder
    .appName("InspeccionResStock")
    .master("local[*]")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("ERROR")

try:
    # Leer el CSV original
    df = (
        spark.read
        .option("header", "true")
        .option("inferSchema", "false")
        .csv(str(ruta))
    )

    # Mostrar dimensiones
    print("\n=== INFORMACION DEL DATASET ===")
    print("Total de registros:", df.count())
    print("Total de columnas:", len(df.columns))

    # Mostrar nombres de columnas
    print("\n=== PRIMERAS 15 COLUMNAS ===")
    for columna in df.columns[:15]:
        print(columna)

    # Identificar columnas importantes
    importantes = [
        "timestamp",
        "in.state",
        "models_used",
        "units_represented",
        "out.electricity.total.energy_consumption..kwh"
    ]

    disponibles = [c for c in importantes if c in df.columns]

    print("\n=== COLUMNAS ENCONTRADAS ===")
    for columna in disponibles:
        print(columna)

    # Mostrar los primeros registros
    if disponibles:
        print("\n=== PRIMEROS 5 REGISTROS ===")
        df.select(
            *[F.col(f"`{c}`").alias(c) for c in disponibles]
        ).show(5, truncate=False)

finally:
    spark.stop()
