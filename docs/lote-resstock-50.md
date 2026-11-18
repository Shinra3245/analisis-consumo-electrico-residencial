# Lote exploratorio ResStock de 50 perfiles

## Alcance

El 18 de noviembre de 2026 se obtuvo un lote de 50 perfiles individuales ResStock 2025 Release 1, escenario AMY 2018, `upgrade=0`. Se seleccionó un perfil por cada combinación de estado y tipo de vivienda en diez estados: CA, CO, FL, IL, MA, NY, OH, PA, TX y WA. El índice consultado contiene 549,971 candidatos en 254 estratos y 51 jurisdicciones.

El lote conserva los diez IDs del piloto previo de CO y NY. Los otros 40 perfiles amplían la cobertura exploratoria con cinco tipos de vivienda por cada uno de ocho estados adicionales. Esta selección no es representativa de la población residencial; los pesos disponibles no corrigen el diseño exploratorio.

## Resultado medido

| Indicador | Resultado |
|---|---:|
| Perfiles solicitados / descargados | 50 / 50 |
| Descargas fallidas | 0 |
| Filas procesadas | 1,752,000 |
| Intervalos esperados por perfil | 35,040 de 15 minutos |
| Bytes de los 50 archivos fuente | 322,878,331 |
| Tiempo medido del lote de descargas | 70.312 s |
| Parquet concatenado | 8,460,089 bytes |
| SHA-256 del Parquet concatenado | `759d1e66af1c35f9a9e5379fd41b3821b77ceac853b38fdbd9bd72e2777e886f` |
| IDs declarados en roster y encontrados en Parquet | 50 / 50 |
| Perfiles con 35,040 filas | 50 / 50 |

El tiempo y los bytes de descarga son medidas de esta ejecución local; no son una estimación de ejecución en la nube. La proyección de 64.5 GB para 10,000 perfiles es una extrapolación lineal del tamaño medio de este lote, no una medición ni una meta ya procesada.

## Procesamiento y estado de salida

El job PySpark 4.0.1 se ejecutó localmente con Java 17 y aprobó las 21 reglas de calidad. Su reporte registró 50 edificios únicos, 1,752,000 filas y cero reglas fallidas. Las reglas de cobertura verifican cada perfil, paso de 900 segundos, extremos temporales, claves y atributos; el manifiesto declara los 50 IDs para detectar perfiles ausentes o inesperados.

La exportación final Gold aprobó también 21/21 reglas y produjo seis tablas JSON con conteos, tamaños y SHA-256 verificados contra `manifest.json`:

| Tabla | Filas | Bytes | SHA-256 |
|---|---:|---:|---|
| `gold_eia_monthly` | 5,304 | 601,763 | `af48f3b56264759b5f261c088125e3545c40e012015b228ed7307b9fc01da825` |
| `gold_resstock_monthly` | 600 | 101,089 | `9b52f9b8b0524a0ca667365cc3ac615cf9ff7489d1ec32270c755d75213e879d` |
| `gold_resstock_pattern` | 33,650 | 16,313,418 | `7484cf1308d7a365160325f5bc867b48b501046bf76c2b304501b88039a12b21` |
| `gold_resstock_pattern_aggregate` | 33,650 | 18,607,376 | `58e01e636babff7864ea3a8b42cbf26a3b3284ece0b5a58254cefecb6ddb6eef` |
| `gold_resstock_profile_summary` | 50 | 15,196 | `f3c4d02ed975cf897dab2142ee52983b2fee818e6a2b597d17d8390fe0f00d5e` |
| `gold_climate` | 336 | 99,993 | `ab57a0bd00ad539ec8bb036b31de78d92d5e1fc56a2a3510deef90b606f02556` |

La zona horaria se resolvió por FIPS de condado usando el conjunto oficial [NOAA/NWS c_16ap26](https://www.weather.gov/gis/Counties). Los 43 FIPS distintos del lote tuvieron resolución única. Los perfiles se distribuyen en Eastern, Central, Mountain y Pacific; los condados divididos por fronteras horarias se bloquean explícitamente. El calendario local resultante cubre los doce meses de 2018 en Eastern; en Central, Mountain y Pacific incluye además los extremos parciales de diciembre de 2017 y diciembre de 2018, que se etiquetan como parciales.

La tabla de patrones individuales y la agregada tienen el mismo número de filas en este lote porque se seleccionó un único perfil por cada estrato estado/tipo de vivienda. La agregación mantiene la clave por estrato y zona horaria y está diseñada para limitar el crecimiento al ampliar perfiles dentro de los estratos; esta ejecución no demuestra una reducción del payload para una muestra de 50.

El job y exportador se ejecutaron con entrada `/tmp/spark-input-resstock-batch50` y publicaron sus salidas en `/tmp/salidas-spark-batch50-final` y `/tmp/tablero-data-v1-50-final`. El manifiesto Gold registra 21/21 controles aprobados; las seis salidas fueron releídas y sus hashes y tamaños coincidieron. Las tablas extendidas permanecen en almacenamiento local temporal; no se copiaron a `tablero/data/v1` ni se incluyeron en el repositorio.

El tablero web existente se abrió en localhost con los artefactos versionados y se inspeccionó la vista horaria: manifiesto validado, patrón agregado visible y tabla individual bajo demanda; la consola del navegador no reportó errores. Esta comprobación visual usó los datos de diez perfiles versionados, no el lote extendido de 50.

## Conservación de archivos

- Los archivos originales descargados se conservaron temporalmente bajo `/tmp/resstock-batch50/raw/`.
- El Parquet de 50 perfiles y los archivos de entrada para Spark están bajo `/tmp/spark-input-resstock-batch50`; las fuentes originales permanecen en `/tmp/resstock-batch50/raw/`.
- El Parquet de 50 perfiles y los archivos originales no se agregaron al repositorio público.
- El repositorio versionado continúa usando el piloto de diez perfiles hasta completar la revisión y generar una publicación explícita.

## Reproducción

Desde la raíz del proyecto, la selección puede regenerarse con:

```bash
python scripts/preparar_datos.py \
  --output /tmp/resstock-batch50 \
  --pilot-states CO NY CA WA IL OH TX FL PA MA \
  --pilot-per-stratum 1 \
  --plan-profiles 10000 \
  --seed 22030511
```

El comando realiza solicitudes a las fuentes públicas y escribe los resultados en `/tmp`; no crea servicios AWS. La lista de 10,000 IDs es una selección de candidatos del índice. Solo los 50 perfiles con archivos descargados y filas verificadas cuentan como parte de este lote.

Para construir una carpeta de entrada autocontenida para Spark, incluyendo el `profile_roster` y los hashes actualizados, sin copiar fuentes originales:

```bash
python scripts/preparar_entrada_spark.py \
  --prepared /tmp/resstock-batch50 \
  --output /tmp/spark-input-resstock-batch50
```

La carpeta de salida debe ser nueva. El proceso contrasta el roster con los IDs/filas del Parquet y con `resstock_seleccion_piloto.csv`; si no coincide, no publica la entrada.
