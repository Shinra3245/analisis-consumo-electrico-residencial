
import os
import sys
import json
from pathlib import Path

from pyspark.sql import SparkSession

os.environ["PYSPARK_PYTHON"] = sys.executable

BASE = Path(__file__).resolve().parents[2]

RUTA_GOLD = (
    BASE / "data/gold/comparacion_resstock_eia_mensual"
)

RUTA_JSON = (
    BASE / "data/exports/comparacion_co_2018.json"
)

spark = (
    SparkSession.builder
    .appName("ExportarComparacionJSON")
    .master("local[*]")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("ERROR")

try:
    print("\n=== EXPORTACION JSON ===", flush=True)

    # Leer la comparacion Gold
    df = spark.read.parquet(str(RUTA_GOLD))

    filas = (
        df.select(
            "anio",
            "mes",
            "estado",
            "resstock_mwh",
            "eia_mwh",
            "diferencia_mwh",
            "relacion_porcentaje"
        )
        .orderBy("mes")
        .collect()
    )

    # Comprobar los 12 meses
    if (
        len(filas) != 12
        or [int(f["mes"]) for f in filas]
           != list(range(1, 13))
        or any(
            f["anio"] != 2018 or f["estado"] != "CO"
            for f in filas
        )
    ):
        raise ValueError("Periodo o meses invalidos")

    registros = []

    for fila in filas:
        registros.append({
            "anio": int(fila["anio"]),
            "mes": int(fila["mes"]),
            "estado": fila["estado"],
            "resstock_mwh": round(
                float(fila["resstock_mwh"]), 2
            ),
            "eia_mwh": round(
                float(fila["eia_mwh"]), 2
            ),
            "diferencia_mwh": round(
                float(fila["diferencia_mwh"]), 2
            ),
            "relacion_porcentaje": round(
                float(fila["relacion_porcentaje"]), 2
            )
        })

    # Totales calculados sin redondear previamente
    total_resstock = sum(
        float(f["resstock_mwh"]) for f in filas
    )

    total_eia = sum(
        float(f["eia_mwh"]) for f in filas
    )

    if total_eia <= 0:
        raise ValueError("Total EIA invalido")

    resultado = {
        "dataset": "comparacion_resstock_eia_mensual",
        "anio": 2018,
        "estado": "CO",
        "unidad": "MWh",
        "fuentes": {
            "resstock": "Consumo residencial modelado",
            "eia": "Ventas oficiales residenciales"
        },
        "nota": (
            "Las fuentes tienen coberturas distintas. "
            "La relacion porcentual no mide precision."
        ),
        "totales": {
            "resstock_mwh": round(total_resstock, 2),
            "eia_mwh": round(total_eia, 2),
            "relacion_porcentaje": round(
                total_resstock / total_eia * 100, 2
            )
        },
        "meses": registros
    }

    # Crear carpeta y guardar JSON
    RUTA_JSON.parent.mkdir(
        parents=True, exist_ok=True
    )

    with open(
        RUTA_JSON, "w", encoding="utf-8"
    ) as archivo:
        json.dump(
            resultado,
            archivo,
            indent=2,
            ensure_ascii=False
        )

    # Comprobar archivo guardado
    with open(
        RUTA_JSON, encoding="utf-8"
    ) as archivo:
        comprobacion = json.load(archivo)

    if len(comprobacion["meses"]) != 12:
        raise ValueError("Error en archivo JSON")

    print("Registros exportados:", len(registros))
    print("ResStock MWh:", round(total_resstock, 2))
    print("EIA MWh:", round(total_eia, 2))
    print("Destino:", RUTA_JSON)

    print("\nJSON GENERADO CORRECTAMENTE")

finally:
    spark.stop()
