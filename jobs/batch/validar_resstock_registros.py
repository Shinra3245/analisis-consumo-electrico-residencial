
from pyspark.sql import functions as F


def validar_registros_resstock(bronze):
    """
    Transforma los registros ResStock y registra
    los motivos de rechazo de cada fila.
    No escribe archivos.
    """

    datos = bronze.select(
        F.expr(
            "try_to_timestamp(`timestamp`, "
            "'yyyy-MM-dd HH:mm:ss')"
        ).alias("timestamp_fin"),

        F.col("`in.state`").alias("estado"),

        F.col(
            "`in.geometry_building_type_recs`"
        ).alias("tipo_vivienda"),

        F.expr(
            "try_cast(`models_used` AS BIGINT)"
        ).alias("modelos"),

        F.expr(
            "try_cast(`units_represented` AS DOUBLE)"
        ).alias("viviendas_representadas"),

        F.expr(
            "try_cast("
            "`out.electricity.total.energy_consumption..kwh` "
            "AS DOUBLE)"
        ).alias("consumo_kwh"),

        F.col("_source").alias("fuente"),
        F.col("_source_file").alias("archivo_origen")
    )

    # El timestamp original representa el fin
    # de un intervalo de consumo de 15 minutos.
    datos = datos.withColumn(
        "timestamp_inicio",
        F.expr("timestamp_fin - INTERVAL 15 MINUTES")
    )

    datos = (
        datos
        .withColumn("anio", F.year("timestamp_inicio"))
        .withColumn("mes", F.month("timestamp_inicio"))
    )

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
                | (F.trim("tipo_vivienda") == ""),
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
                "Anio fuera de la muestra"
            )
        )
    )

    return datos
