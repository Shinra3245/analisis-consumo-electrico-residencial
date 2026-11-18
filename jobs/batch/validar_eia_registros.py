
from pyspark.sql import functions as F
from pyspark.sql.window import Window


def validar_registros_eia(bronze):
    """
    Valida registros EIA y agrega una columna
    con los motivos de rechazo.
    """

    # Convertir datos a los tipos correctos
    datos = (
        bronze
        .withColumn(
            "anio_num",
            F.expr("try_cast(anio as int)")
        )
        .withColumn(
            "mes_num",
            F.expr("try_cast(mes as int)")
        )
        .withColumn(
            "ventas_mwh",
            F.expr(
                "try_cast(ventas_residenciales_mwh as double)"
            )
        )
    )

    # Identificar registros duplicados
    ventana = Window.partitionBy(
        "anio_num", "mes_num", "estado"
    )

    datos = datos.withColumn(
        "total_duplicados",
        F.count("*").over(ventana)
    )

    # Registrar los motivos de rechazo
    datos = datos.withColumn(
        "errores",
        F.concat_ws(
            " | ",
            F.when(
                F.col("anio_num").isNull()
                | (F.col("anio_num") != 2018),
                "Anio invalido"
            ),
            F.when(
                F.col("mes_num").isNull()
                | ~F.col("mes_num").between(1, 12),
                "Mes invalido"
            ),
            F.when(
                F.col("estado").isNull()
                | (F.col("estado") != "CO"),
                "Estado invalido"
            ),
            F.when(
                F.col("estatus_dato").isNull()
                | (F.col("estatus_dato") != "Final"),
                "Estatus no final"
            ),
            F.when(
                F.col("ventas_mwh").isNull()
                | F.isnan("ventas_mwh")
                | (F.col("ventas_mwh") < 0),
                "Ventas invalidas"
            ),
            F.when(
                F.col("total_duplicados") > 1,
                "Registro duplicado"
            )
        )
    )

    return datos
