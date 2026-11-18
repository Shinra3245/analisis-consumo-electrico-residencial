
import os
import sys
import time
from pathlib import Path
from datetime import datetime

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

os.environ["PYSPARK_PYTHON"] = sys.executable

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"

RUTAS = {
    "ResStock Bronze": DATA / "bronze/resstock_co_2018",
    "ResStock Silver": DATA / "silver/resstock_co_2018",
    "ResStock Gold": DATA / "gold/resstock_consumo_mensual",
    "EIA Bronze": DATA / "bronze/eia_co_2018",
    "EIA Silver": DATA / "silver/eia_co_2018",
    "EIA Gold": DATA / "gold/eia_ventas_residenciales_mensual",
    "Comparacion": DATA / "gold/comparacion_resstock_eia_mensual",
    "Rechazados ResStock": DATA / "quality/resstock_co_2018_rechazados",
    "Rechazados EIA": DATA / "quality/eia_co_2018_rechazados"
}

REPORTE = BASE / "docs/reporte_calidad_rendimiento_spark.md"

def tamano_bytes(ruta):
    if ruta.is_file():
        return ruta.stat().st_size
    return sum(
        archivo.stat().st_size
        for archivo in ruta.rglob("*")
        if archivo.is_file()
    )

spark = (
    SparkSession.builder
    .appName("ReporteCalidadRendimiento")
    .master("local[*]")
    .config("spark.sql.session.timeZone", "UTC")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("ERROR")

try:
    print("\n=== REPORTE DE CALIDAD Y RENDIMIENTO ===")

    metricas = {}

    for nombre, ruta in RUTAS.items():
        if not ruta.exists():
            raise FileNotFoundError(f"No existe: {ruta}")

        inicio = time.perf_counter()

        cantidad = spark.read.parquet(str(ruta)).count()

        duracion = time.perf_counter() - inicio

        metricas[nombre] = {
            "filas": cantidad,
            "segundos": duracion,
            "bytes": tamano_bytes(ruta)
        }

        print(
            f"{nombre}: {cantidad} filas, "
            f"{duracion:.3f} segundos"
        )

    # Comprobar la conservación de registros
    r = metricas

    if (
        r["ResStock Bronze"]["filas"]
        != r["ResStock Silver"]["filas"]
        + r["Rechazados ResStock"]["filas"]
    ):
        raise ValueError("Conteos ResStock inconsistentes")

    if (
        r["EIA Bronze"]["filas"]
        != r["EIA Silver"]["filas"]
        + r["Rechazados EIA"]["filas"]
    ):
        raise ValueError("Conteos EIA inconsistentes")

    if (
        r["ResStock Gold"]["filas"] != 12
        or r["EIA Gold"]["filas"] != 12
        or r["Comparacion"]["filas"] != 12
    ):
        raise ValueError("Meses Gold incompletos")

    # Comprobar valores anuales
    resstock = spark.read.parquet(
        str(RUTAS["ResStock Gold"])
    )

    eia = spark.read.parquet(
        str(RUTAS["EIA Gold"])
    )

    total_resstock = resstock.agg(
        F.sum("consumo_mwh")
    ).first()[0]

    total_eia = eia.agg(
        F.sum("ventas_mwh")
    ).first()[0]

    relacion = total_resstock / total_eia * 100

    if (
        abs(total_resstock - 16809653.30) > 0.10
        or abs(total_eia - 19286952.00) > 0.10
    ):
        raise ValueError("Totales anuales inesperados")

    # Preparar reporte
    lineas = [
        "# Reporte de calidad y rendimiento Spark",
        "",
        f"Fecha: {datetime.now().astimezone().isoformat(timespec='seconds')}",
        "",
        "## Entorno",
        "",
        f"- Apache Spark: {spark.version}",
        "- Ejecucion: local en Windows",
        "- Periodo: Colorado, 2018",
        "- Fuentes: ResStock y EIA",
        "",
        "## Registros y tiempos",
        "",
        "| Dataset | Filas | Tamaño (MiB) | Tiempo (s) |",
        "|---|---:|---:|---:|"
    ]

    for nombre, valor in metricas.items():
        mib = valor["bytes"] / (1024 * 1024)

        lineas.append(
            f"| {nombre} | {valor['filas']:,} "
            f"| {mib:.3f} "
            f"| {valor['segundos']:.3f} |"
        )

    lineas.extend([
        "",
        "## Resultados de calidad",
        "",
        f"- Rechazados ResStock: {r['Rechazados ResStock']['filas']}",
        f"- Rechazados EIA: {r['Rechazados EIA']['filas']}",
        "- Conservacion de conteos Bronze/Silver: correcta",
        "- Meses Gold: 12 por fuente",
        "",
        "## Totales anuales",
        "",
        f"- ResStock: {total_resstock:,.2f} MWh",
        f"- EIA: {total_eia:,.2f} MWh",
        f"- Relacion entre totales: {relacion:.2f}%",
        "",
        "## Alcance y limitaciones",
        "",
        "- Los tiempos corresponden a lectura y conteo de Parquet "
        "en esta ejecucion local; no representan el tiempo total "
        "de construccion del pipeline.",
        "- Los tamaños corresponden a las carpetas de salida.",
        "- Los controles aplicados no sustituyen una auditoria "
        "completa de las 96 columnas originales.",
        "- ResStock y EIA representan coberturas diferentes; "
        "la relacion porcentual no mide precision.",
        "- Pendientes: pruebas con datos sinteticos invalidos, "
        "escala y rendimiento en AWS, y streaming con Kinesis."
    ])

    REPORTE.parent.mkdir(parents=True, exist_ok=True)

    REPORTE.write_text(
        "\n".join(lineas) + "\n",
        encoding="utf-8"
    )

    print("\n=== RESULTADOS ANUALES ===")
    print(f"ResStock: {total_resstock:,.2f} MWh")
    print(f"EIA: {total_eia:,.2f} MWh")
    print(f"Relacion: {relacion:.2f}%")

    print("\nReporte generado:", REPORTE)
    print("\nREPORTE GENERADO CORRECTAMENTE")

finally:
    spark.stop()
