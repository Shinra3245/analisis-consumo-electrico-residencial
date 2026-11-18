# Pipeline local Silver/Gold con PySpark

## Alcance implementado

[`scripts/job_spark_piloto.py`](../scripts/job_spark_piloto.py) procesa las muestras locales de ResStock, EIA-861M y clima. Lee los originales sin modificarlos, aplica controles de calidad con bloqueo, produce tablas Parquet Silver/Gold y publica el árbol de salida mediante staging y renombre atómico.

El pipeline y el tablero local ya están conectados mediante una exportación JSON validada. Este bloque todavía no implementa AWS, EMR, Kinesis, pronósticos ni detección de anomalías. Tampoco calcula un ratio ResStock/EIA ni une los perfiles con el clima.

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

Silver conserva el timestamp fuente como fin de intervalo en EST fijo. El Gold mensual asigna el consumo al intervalo que termina restando 15 minutos. El exportador del tablero convierte ese inicio primero a UTC y después a `America/Denver` o `America/New_York`; deriva de ahí hora, día y mes local, conserva el offset y marca meses parciales. EIA conserva `Final`/`Preliminary`; clima permanece separado y en UTC.

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

## Exportación para el tablero web (`tablero/data/v1/`)

El pipeline soporta la exportación de las capas Gold en formato JSON según el contrato acordado con el frontend (esquema `1.0`), disponible en dos modalidades:

1. **Generación directa con Python (sin requerir Java/Spark):** requiere las dependencias fijadas en [`scripts/requirements-tablero.txt`](../scripts/requirements-tablero.txt):
   ```bash
   python -m pip install -r scripts/requirements-tablero.txt
   python3 scripts/generar_datos_tablero.py --input datos --output tablero/data/v1 --overwrite
   ```
   El exportador verifica SHA-256 de las cuatro fuentes y bloquea la publicación si falla cualquier regla QC. Rechaza rutas de entrada/salida solapadas y no reemplaza una salida existente a menos que se indique `--overwrite`; incluso con esa opción solo reemplaza una exportación v1 reconocible que no contenga archivos adicionales. Para conservar los archivos actuales, se puede exportar a una carpeta nueva, por ejemplo `/tmp/tablero-data/v1`.
2. **Generación integrada desde PySpark con `--export-tablero`:**
   El mismo entorno virtual debe tener PySpark y las dependencias del exportador (`scripts/requirements-tablero.txt`).
   ```bash
   python -m pip install -r scripts/requirements-spark.txt -r scripts/requirements-tablero.txt
   JAVA_HOME=/usr/lib/jvm/java-17-temurin-jdk \
   PYSPARK_PYTHON=/tmp/bigdata-spark-venv/bin/python \
   /tmp/bigdata-spark-venv/bin/python scripts/job_spark_piloto.py \
     --input datos \
     --output /tmp/salidas-spark-piloto \
     --export-tablero tablero/data/v1 \
     --overwrite-tablero \
     --master 'local[2]'
   ```
   `--overwrite-tablero` es explícito y solo se permite junto con `--export-tablero`.

### Capas publicadas en `tablero/data/v1/`

| Archivo | Grano | Filas | SHA-256 |
|---|---|---:|---|
| `gold_eia_monthly.json` | Estado × Mes | 5,304 | `af48f3b56264759b5f261c088125e3545c40e012015b228ed7307b9fc01da825` |
| `gold_resstock_monthly.json` | Perfil × Mes fuente | 120 | `9ad49b84ca04544d298316f6ab680afc6af2938ae89d26538398b735e94d5a10` |
| `gold_resstock_pattern.json` | Perfil × Periodo local × Día × Hora local × Offset | 6,730 | `b020c7030e0de6b8289f134c138cb812777980387bc3a45ca29bc8e43e08def1` |
| `gold_resstock_profile_summary.json` | Perfil anual | 10 | `c06c40b4f2e34e35cc0f1fc9c7d2eff8f4bd6e803e9755988ebbf485d41bca12` |
| `gold_climate.json` | Punto × Hora UTC | 336 | `ab57a0bd00ad539ec8bb036b31de78d92d5e1fc56a2a3510deef90b606f02556` |
| `manifest.json` | Manifiesto v1.0 | 1 | `bdf50cfc00bc8777918a513511eb9f0ee4c7b848a60965e6488d0705a66699a7` |

### Tratamiento de marcas temporales y supuestos
- **Origen:** ResStock publica timestamps de fin de intervalo en EST fijo (UTC−5), sin horario de verano.
- **Conversión de inicio:** Se resta 15 minutos para obtener el inicio de cada intervalo.
- **Conversión a UTC y zona IANA:** Se suman 5 horas para obtener UTC explícito y se proyecta a la zona del estado (`America/Denver` para CO, `America/New_York` para NY).
- **Manejo de DST:** Se conserva `utc_offset_minutes` (-420/-360 para Denver, -300/-240 para NY) para distinguir horas repetidas en el cambio de horario.
- **Periodos parciales:** Los meses `2017-12` (2 horas iniciales) y `2018-12` (incompleto al cierre de año) en Colorado se rotulan como `is_partial_period = true`.

### Reglas de integridad metodológica y métrica 87.16%
- **Separación de poblaciones:** Perfiles modelados ResStock y ventas agregadas EIA permanecen desacoplados; no se interpretan como observaciones equivalentes ni se fusionan a nivel de hogar.
- **Bloqueo de la comparación 87.16%:** El archivo agregado estatal de Colorado para ResStock (`timeseries_aggregates`) está ausente en `origin/main`. No se crean datos sintéticos sustitutos y la métrica se cataloga formalmente como no reproducida (`not_reproduced`) en `manifest.json`.
- **Alcance piloto:** Exclusivamente 10 perfiles físicos (5 CO, 5 NY); no se afirma cobertura completa ni representatividad nacional.
