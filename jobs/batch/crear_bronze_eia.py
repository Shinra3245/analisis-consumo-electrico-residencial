
import os
import sys
from pathlib import Path

from openpyxl import load_workbook
from pyspark.sql import SparkSession
from pyspark.sql.types import (
    StructType,
    StructField,
    StringType
)

os.environ["PYSPARK_PYTHON"] = sys.executable

# Rutas del proyecto
BASE = Path(__file__).resolve().parents[2]

RUTA_RAW = BASE / "data/raw/eia_sales_revenue.xlsx"
RUTA_BRONZE = BASE / "data/bronze/eia_co_2018"

if not RUTA_RAW.is_file():
    raise FileNotFoundError(f"No existe: {RUTA_RAW}")

print("\n=== CAPA BRONZE - EIA ===", flush=True)

# Extraer los registros del Excel
wb = load_workbook(
    RUTA_RAW,
    read_only=True,
    data_only=True
)

registros = []

try:
    ws = wb["Monthly-States"]

    for fila in ws.iter_rows(
        min_row=4,
        max_col=6,
        values_only=True
    ):
        anio = fila[0]
        mes = fila[1]
        estado = fila[2]
        estatus = fila[3]
        ventas = fila[5]

        if (
            anio == 2018
            and str(estado).strip().upper() == "CO"
        ):
            registros.append((
                str(anio),
                str(mes) if mes is not None else None,
                "CO",
                str(estatus) if estatus is not None else None,
                str(ventas) if ventas is not None else None,
                "EIA",
                RUTA_RAW.name
            ))

finally:
    wb.close()

print("Registros extraidos:", len(registros))

if len(registros) != 12:
    raise ValueError(
        "Se esperaban 12 registros de Colorado 2018"
    )

# Definir esquema Bronze: datos originales como texto
schema = StructType([
    StructField("anio", StringType(), True),
    StructField("mes", StringType(), True),
    StructField("estado", StringType(), True),
    StructField("estatus_dato", StringType(), True),
    StructField(
        "ventas_residenciales_mwh",
        StringType(),
        True
    ),
    StructField("fuente", StringType(), True),
    StructField("archivo_origen", StringType(), True)
])

# Iniciar Spark
spark = (
    SparkSession.builder
    .appName("BronzeEIA")
    .master("local[*]")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("ERROR")

try:
    # Crear DataFrame en Spark
    df = spark.createDataFrame(
        registros,
        schema=schema
    )

    print("\n=== DATOS BRONZE ===")
    df.orderBy("mes").show(12, truncate=False)

    # Guardar como Parquet
    (
        df.coalesce(1)
        .write
        .mode("overwrite")
        .parquet(str(RUTA_BRONZE))
    )

    print("\nArchivo Parquet generado.")

    # Verificar escritura
    resultado = spark.read.parquet(str(RUTA_BRONZE))

    filas_salida = resultado.count()

    print("Registros de salida:", filas_salida)
    print("Columnas:", len(resultado.columns))
    print("Destino:", RUTA_BRONZE)

    if filas_salida != len(registros):
        raise ValueError("Error en conteo Bronze")

    print("\nCAPA BRONZE EIA GENERADA CORRECTAMENTE")

finally:
    spark.stop()
