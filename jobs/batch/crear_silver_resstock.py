
import os
import sys
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

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

    # Convertir las columnas a tipos adecuados
    datos = bronze.select(
        F.to_timestamp(
            F.col("timestamp"),
            "yyyy-MM-dd HH:mm:ss"
        ).alias("timestamp_fin"),

        F.col("`in.state`").alias("estado"),

        F.col(
            "`in.geometry_building_type_recs`"
        ).alias("tipo_vivienda"),

        F.col("models_used")
        .cast("long").alias("modelos"),

        F.col("units_represented")
        .cast("double").alias("viviendas_representadas"),

        F.col(
            "`out.electricity.total.energy_consumption..kwh`"
        ).cast("double").alias("consumo_kwh"),

        F.col("_source").alias("fuente"),
        F.col("_source_file").alias("archivo_origen")
    )

    # Calcular el inicio del intervalo
    datos = datos.withColumn(
        "timestamp_inicio",
        F.expr("timestamp_fin - INTERVAL 15 MINUTES")
    )

    # Obtener año y mes del intervalo de consumo
    datos = (
        datos
        .withColumn("anio", F.year("timestamp_inicio"))
        .withColumn("mes", F.month("timestamp_inicio"))
    )

    # Validar registros y registrar sus errores
    datos = datos.withColumn(
        "errores",
        F.concat_ws(
            " | ",
            F.when(
                F.col("timestamp_fin").isNull(),
                "Fecha invalida"
            ),
            F.when(
                F.col("estado").isNull()
                | (F.col("estado") != "CO"),
                "Estado invalido"
            ),
            F.when(
                F.col("tipo_vivienda").isNull()
                | (F.trim(F.col("tipo_vivienda")) == ""),
                "Tipo de vivienda invalido"
            ),
            F.when(
                F.col("consumo_kwh").isNull()
                | F.isnan("consumo_kwh")
                | (F.col("consumo_kwh") < 0),
                "Consumo invalido"
            ),
            F.when(
                F.col("modelos").isNull()
                | (F.col("modelos") <= 0),
                "Modelos invalidos"
            ),
            F.when(
                F.col("viviendas_representadas").isNull()
                | F.isnan("viviendas_representadas")
                | (F.col("viviendas_representadas") <= 0),
                "Viviendas representadas invalidas"
            ),
            F.when(
                F.col("anio").isNotNull()
                & (F.col("anio") != 2018),
                "Año fuera de la muestra"
            )
        )
    )

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
