# Leer el piloto con Apache Spark

Esta guía usa los artefactos versionados en [`datos/`](../datos/README.md). Requiere Java y PySpark compatibles. El PR de Mares reportó una ejecución con PySpark 4.0.1; el equipo debe registrar la versión que efectivamente tenga instalada al reproducirla.

## Iniciar Spark

Desde la raíz del repositorio:

```bash
pyspark --master "local[2]"
```

En PowerShell se usa el mismo comando. Verifica la versión con `spark.version` dentro de la sesión. No ejecutes el script de preparación para leer los archivos ya incluidos.

## Leer archivos y declarar esquemas CSV

Parquet contiene su propio esquema. Los CSV se leen con un esquema explícito para evitar inferencias variables entre equipos:

```python
from pyspark.sql.types import (
    DecimalType, DoubleType, StringType,
    StructField, StructType, TimestampType,
)

base = "datos"

schema_eia = StructType([
    StructField("periodo", StringType(), False),
    StructField("estado", StringType(), False),
    StructField("sector", StringType(), False),
    StructField("estado_dato", StringType(), False),
    StructField("ventas_mwh", DecimalType(20, 2), False),
])

schema_clima = StructType([
    StructField("punto_id", StringType(), False),
    StructField("estado", StringType(), False),
    StructField("latitude_solicitada", DoubleType(), False),
    StructField("longitude_solicitada", DoubleType(), False),
    StructField("latitude_celda", DoubleType(), False),
    StructField("longitude_celda", DoubleType(), False),
    StructField("timestamp_utc", TimestampType(), False),
    StructField("temperatura_c", DoubleType(), False),
    StructField("modelo", StringType(), False),
])

schema_demo = StructType([
    StructField("periodo", StringType(), False),
    StructField("resstock_co_unifamiliar_aislada_mwh", DoubleType(), False),
    StructField("eia_co_res_ventas_mwh", DoubleType(), False),
    StructField("razon_descriptiva_pct", DoubleType(), False),
])

spark.conf.set("spark.sql.parquet.inferTimestampNTZ.enabled", "true")
spark.conf.set("spark.sql.session.timeZone", "UTC")
resstock = spark.read.parquet(f"{base}/resstock_perfiles_piloto.parquet")
eia = spark.read.schema(schema_eia).option("header", True).csv(
    f"{base}/eia_residencial_mensual.csv")
clima = spark.read.schema(schema_clima).option("header", True).option(
    "timestampFormat", "yyyy-MM-dd'T'HH:mm:ssX").csv(
        f"{base}/clima_open_meteo_muestra.csv")
demo = spark.read.schema(schema_demo).option("header", True).csv(
    f"{base}/demo_colorado_2018_verificacion.csv")

resstock.printSchema()
eia.printSchema()
clima.printSchema()
```

La configuración UTC aplica a la lectura del campo climático, que incluye `Z`. En ResStock, `timestamp_fin_local` es un timestamp sin zona adjunta en el Parquet; la fuente lo define como EST fijo. No confundas ese valor con UTC ni apliques horario de verano. Antes de convertirlo o unirlo con clima, valida el tipo que reporta la versión instalada de Spark y acuerda una transformación explícita.

## Comprobar conteos del piloto

```python
from pyspark.sql import functions as F

print("ResStock:", resstock.count())
print("EIA:", eia.count())
print("Clima:", clima.count())
print("Comparación mensual:", demo.count())

resstock.groupBy("bldg_id").count().orderBy("bldg_id").show(20, truncate=False)
eia.groupBy("estado_dato").count().orderBy("estado_dato").show()
clima.groupBy("punto_id").count().orderBy("punto_id").show()

resstock.select(
    F.count("*").alias("filas"),
    F.countDistinct("bldg_id").alias("perfiles"),
    F.sum(F.when(F.col("electricidad_kwh").isNull(), 1).otherwise(0)).alias("nulos"),
    F.sum(F.when(F.col("electricidad_kwh") < 0, 1).otherwise(0)).alias("negativos"),
).show()
```

Conteos registrados en los artefactos: 350,400 filas ResStock (10 perfiles de 35,040 cada uno), 5,304 registros EIA (4,896 `Final`, 408 `Preliminary`), 336 horas-punto climáticas (168 por punto) y 12 meses en la comparación. El PR de Mares reportó una comprobación en PySpark 4.0.1; esa ejecución no se reprodujo al preparar esta guía. Los conteos anteriores son expectativas cotejadas con el manifiesto y CSV integrados.

La tabla `demo_colorado_2018_verificacion.csv` reporta una relación mensual entre un agregado modelado de viviendas unifamiliares aisladas y las ventas de todo el sector residencial. Sus poblaciones difieren y el agregado crudo no está incluido; por ello la relación anual de 87.16% no se declara validada independientemente.

## Reproducir la extracción en otra carpeta

La extracción consulta fuentes públicas y puede tardar o cambiar si las fuentes se actualizan. Usa una carpeta de salida separada para no reemplazar los datos versionados:

```bash
python -m pip install -r scripts/requirements-datos.txt
python scripts/preparar_datos.py --output /tmp/reproduccion-piloto-datos
```

La carpeta `--output` contendrá `raw/`, `datos/`, `manifiesto.json` y `resumen-ejecucion.json`. La opción predeterminada es `data/raw/reproduccion-piloto-datos/`, excluida de Git. La lista de 10,000 IDs es una selección candidata; el script descarga solo el piloto definido por sus opciones.
