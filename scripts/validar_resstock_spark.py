
import os
import sys
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window

os.environ["PYSPARK_PYTHON"] = sys.executable

ruta = Path(
    "data/raw/up00-co-single-family_detached.csv"
).resolve()

spark = (
    SparkSession.builder
    .appName("ValidacionResStock")
    .master("local[*]")
    .config("spark.sql.session.timeZone", "UTC")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("ERROR")

try:
    df = (
        spark.read
        .option("header", "true")
        .csv(str(ruta))
    )

    datos = df.select(
        F.to_timestamp(
            F.col("timestamp"),
            "yyyy-MM-dd HH:mm:ss"
        ).alias("fecha"),

        F.col("`in.state`").alias("estado"),

        F.col(
            "`out.electricity.total.energy_consumption..kwh`"
        ).cast("double").alias("consumo_kwh")
    )

    print("\n=== VALIDACION DE RESSTOCK ===")

    print("Total de registros:", datos.count())

    # Comprobar valores nulos
    print("\n=== VALORES NULOS ===")

    for columna in datos.columns:
        cantidad = datos.filter(
            F.col(columna).isNull()
        ).count()

        print(f"{columna}: {cantidad}")

    # Detectar timestamps duplicados
    print("\n=== FECHAS DUPLICADAS ===")

    duplicados = (
        datos.groupBy("fecha")
        .count()
        .filter(F.col("count") > 1)
        .count()
    )

    print("Fechas duplicadas:", duplicados)

    # Comprobar consumos negativos
    print("\n=== CONSUMO NEGATIVO ===")

    negativos = datos.filter(
        F.col("consumo_kwh") < 0
    ).count()

    print("Registros negativos:", negativos)

    # Verificar rango de fechas
    print("\n=== RANGO DE FECHAS ===")

    datos.select(
        F.min("fecha").alias("fecha_inicial"),
        F.max("fecha").alias("fecha_final")
    ).show(truncate=False)

    # Comprobar intervalos de 15 minutos
    print("\n=== INTERVALOS DE TIEMPO ===")

    ventana = Window.orderBy("fecha")

    fechas = (
        datos.select("fecha")
        .where(F.col("fecha").isNotNull())
        .distinct()
    )

    intervalos = (
        fechas.withColumn(
            "anterior",
            F.lag("fecha").over(ventana)
        )
        .withColumn(
            "diferencia_segundos",
            F.col("fecha").cast("long")
            - F.col("anterior").cast("long")
        )
    )

    irregulares = intervalos.filter(
        F.col("diferencia_segundos").isNotNull()
        & (F.col("diferencia_segundos") != 900)
    ).count()

    print("Intervalos irregulares:", irregulares)

finally:
    spark.stop()
