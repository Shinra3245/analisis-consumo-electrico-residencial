# Pipeline local Silver/Gold con PySpark

## Alcance implementado

[`scripts/job_spark_piloto.py`](../scripts/job_spark_piloto.py) procesa las muestras locales de ResStock, EIA-861M y clima. Lee los originales sin modificarlos, aplica controles de calidad con bloqueo, produce tablas Parquet Silver/Gold y publica el árbol de salida mediante staging y renombre atómico.

Este bloque local no implementa todavía AWS, EMR, Kinesis, la aplicación de seis vistas, pronósticos ni detección de anomalías. Tampoco calcula un ratio ResStock/EIA ni une los perfiles con el clima.

## Entorno reproducido

- Python del entorno temporal usado: 3.14.
- Java: OpenJDK 17.
- PySpark/Spark: 4.0.1.
- `pyspark==4.0.1`, fijado en [`scripts/requirements-spark.txt`](../scripts/requirements-spark.txt).

Instalación en un entorno virtual:

```bash
python3 -m venv .venv-spark
source .venv-spark/bin/activate
python -m pip install -r scripts/requirements-spark.txt
```

Ejecución segura desde la raíz del proyecto; `--output` debe ser una carpeta nueva o vacía y estar fuera de `datos/`:

```bash
python scripts/job_spark_piloto.py \
  --input datos \
  --output /tmp/salidas-spark-piloto \
  --master 'local[2]'
```

El job resuelve rutas reales, rechaza solapamientos entre entrada/salida y no sobrescribe una salida no vacía. Antes de procesar, compara el tamaño y SHA-256 de los cuatro archivos de entrada con `datos/manifiesto-integracion.json`.

## Capas producidas

| Tabla | Grano | Filas verificadas | Campos principales |
|---|---|---:|---|
| Silver ResStock | Perfil × intervalo de 15 min | 350,400 | `bldg_id`, `state_code`, `housing_type`, `profile_weight`, `timestamp_end_est`, `electricity_kwh`, `quality_flags` |
| Silver EIA | Estado × mes | 5,304 | `period`, `state_code`, `sector`, `data_status`, `sales_mwh`, `quality_flags` |
| Silver clima | Punto × hora UTC | 336 | `punto_id`, `state_code`, coordenadas, `timestamp_utc`, `temperatura_c`, `modelo` |
| Gold ResStock mensual | Perfil × mes fuente | 120 | `bldg_id`, `source_period`, `state_code`, `housing_type`, `profile_weight`, `kwh_month`, `n_intervals` |
| Gold EIA mensual | Estado × mes × estado de publicación | 5,304 | `period`, `state_code`, `data_status`, `sales_mwh` |

Para completar Silver ResStock, `state_code`, `housing_type` y `profile_weight` se obtienen de `resstock_seleccion_propuesta.csv` mediante `bldg_id`. El QC verifica que cada perfil del Parquet tenga metadatos válidos y unívocos. El índice tiene 10,000 candidatos; el Parquet procesado contiene 10 perfiles.

Los timestamps de ResStock conservan la semántica de fin de intervalo en EST fijo. El mes de Gold se asigna al intervalo de duración restando 15 minutos; así los datos AMY 2018 producen 12 meses por perfil. Este job aún no convierte a hora local para patrones horarios. EIA conserva `Final`/`Preliminary`; clima permanece separado y en UTC.

## Controles y publicación

El job registra 21 reglas: 7 ResStock, 7 EIA y 7 clima. Incluyen conteos y cobertura temporal, nulos, valores/rangos, unicidad, continuidad (900 s ResStock y 3,600 s clima) y correspondencia de metadatos para los perfiles descargados. Si alguna regla falla, no se escriben las capas y el proceso termina con código distinto de cero.

La salida válida contiene:

```text
<output>/
├── silver/
├── gold/
├── manifiesto_ejecucion.json
└── reporte_calidad.json
```

El manifiesto registra SHA-256 y tamaño de entradas y archivos Parquet de salida, conteos, versión de esquema/transformación y estado de calidad. La hora exacta de descarga de los archivos no está en el manifiesto de entrada y queda explícitamente como desconocida; no se sustituye por la hora de ejecución.

## Ejecución observada

Comando ejecutado en el entorno temporal, sin escribir resultados dentro del repositorio:

```bash
JAVA_HOME=/usr/lib/jvm/java-17-temurin-jdk \
PYSPARK_PYTHON=/tmp/bigdata-spark-venv/bin/python \
/tmp/bigdata-spark-venv/bin/python scripts/job_spark_piloto.py \
  --input datos \
  --output /tmp/bigdata-spark-piloto-final-20261118 \
  --master 'local[2]'
```

Resultado observado: Spark 4.0.1 finalizó con `VALID_WITH_WARNINGS`, 21/21 reglas aprobadas y dos advertencias: la muestra climática permanece separada y no se conoce la hora UTC exacta de descarga de las fuentes. Se comprobaron 350,400, 5,304 y 336 filas Silver, 120 filas Gold ResStock y 5,304 filas Gold EIA. Se recalcularon y compararon los hashes de cada Parquet contra `manifiesto_ejecucion.json`; no hubo diferencias.

La salida está en `/tmp/bigdata-spark-piloto-final-20261118` en el entorno donde se hizo la ejecución; no está versionada ni publicada en la nube.
