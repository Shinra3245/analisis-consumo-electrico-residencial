# Contrato de datos v1 — consumo eléctrico residencial

**Estado:** propuesta técnica basada en artefactos locales inspeccionados; lista para revisión del equipo. No implica que la ingestión Spark/Kinesis esté implementada.

El contrato mantiene separadas las series modeladas de ResStock, las ventas residenciales publicadas por EIA y el clima de Open-Meteo. Las tablas describen poblaciones y resoluciones distintas; no se fusionan como si fueran observaciones equivalentes.

## 1. Identificación y trazabilidad comunes

Cada conjunto procesado debe acompañarse con estos atributos de lote:

| Atributo | Tipo | Regla |
|---|---|---|
| `source_dataset_id` | texto | ID estable, por ejemplo `resstock_2025r1_amy2018_upgrade0`, `eia861m_sales_monthly` o `openmeteo_era5land_hourly`. |
| `source_uri` | texto | URL exacta de descarga o endpoint, sin claves ni parámetros secretos. |
| `source_retrieved_at_utc` | timestamp UTC | Instante en que el equipo obtuvo el archivo/respuesta. |
| `source_sha256` | texto hexadecimal | Hash del archivo crudo; se calcula al recibirlo y se conserva en manifiesto. |
| `schema_version` | texto | Versión del esquema de salida, inicialmente `1.0`. |
| `transform_version` | texto | Versión/tag del código que produjo la tabla. |
| `quality_status` | enum | `valid`, `valid_with_warnings` o `rejected`; los motivos quedan en `quality_flags`. |

Estos atributos pueden residir en manifiesto/metadata de partición y no repetirse en cada fila. Para los eventos simulados de replay, agregar `replay_id` e `ingested_at_utc`; nunca reemplazar con ellos la fecha/período original de la fuente.

## 2. ResStock: perfil residencial modelado

### Evidencia inspeccionada

El Parquet piloto del ZIP se leyó completo con PyArrow 26.0.1 desde memoria, sin extraerlo. Tiene 350,400 filas y estas columnas:

| Columna observada | Tipo Parquet | Nulos | Semántica confirmada para el piloto |
|---|---|---:|---|
| `bldg_id` | `uint32` | 0 | ID de modelo ResStock. |
| `timestamp_fin_local` | `timestamp[ms]` sin zona adjunta | 0 | El nombre que asignó el script es engañoso: ResStock publica la serie convertida a Eastern Standard Time (EST) fijo. Marca el fin del intervalo. |
| `electricidad_kwh` | `float32` | 0 | Energía modelada del intervalo, en kWh. |

El piloto contiene 10 IDs con 35,040 filas por ID; las claves `(bldg_id, timestamp_fin_est)` no se repiten. Cada perfil está ordenado desde `2018-01-01 00:15` hasta `2019-01-01 00:00` EST, con pasos de 900 segundos; no hay consumos negativos ni valores no finitos. La FAQ oficial de ResStock confirma que los timestamps representan el fin del intervalo y se convierten a EST para publicación. [FAQ ResStock](https://natlabrockies.github.io/ResStock.github.io/docs/FAQ.html)

### Tabla canónica propuesta `silver.resstock_profile_interval`

| Campo canónico | Tipo lógico | Requerido | Origen/regla |
|---|---|---:|---|
| `source_dataset_id` | texto | sí | Constante del release, año meteorológico y upgrade indicados arriba. |
| `bldg_id` | entero sin signo / texto estable | sí | Preservar el ID original; no inferir identidad física de una vivienda real. |
| `state_code` | texto de 2 letras | sí | Enriquecer desde el índice/metadatos usando `bldg_id`; no está en el Parquet piloto consolidado. |
| `housing_type` | texto | sí | Enriquecer desde metadatos del mismo release; no está en el Parquet piloto consolidado. |
| `profile_weight` | decimal | sí para estimaciones ponderadas | Enriquecer desde el peso del mismo release. No usar una muestra no probabilística como estimador nacional. |
| `timestamp_end_est` | timestamp con offset fijo `-05:00` | sí | Renombrar conceptualmente `timestamp_fin_local`; preservar semántica de fin de intervalo. El campo fuente no contiene offset. |
| `interval_minutes` | entero | sí | `15` para este piloto y release. |
| `electricity_kwh` | float64 lógico | sí | Valor de `electricidad_kwh`; el tipo canónico más amplio evita pérdidas adicionales al unir archivos. |
| `quality_flags` | lista de texto | sí | Vacía si pasó controles; si no, registrar razones y no ocultar/reparar la fila silenciosamente. |

PK: `(source_dataset_id, bldg_id, timestamp_end_est)`. Al entregar a un motor que exige instantes, convertir EST fijo a UTC sumando cinco horas y guardar ambos campos: instante normalizado `event_time_utc` y fecha fuente `timestamp_end_est`. No aplicar horario de verano al campo fuente EST. Las dimensiones geográficas y el peso deben proceder del índice de la misma versión; su inclusión/publicación sigue condicionada a la revisión de términos ResStock.

**Controles:** 35,040 intervalos por perfil para AMY 2018; unicidad de PK; incrementos de 15 min; cero nulos/no finitos; energía no negativa; metadatos presentes y del mismo release; peso positivo; conteo de perfiles/filas y hash en manifiesto. Rechazar o poner en cuarentena perfiles incompletos. El piloto de 10 modelos no demuestra representatividad nacional.

## 3. EIA: ventas residenciales mensuales

### Evidencia inspeccionada

Se reprodujeron byte a byte `datos/eia_residencial_mensual.csv` y `datos/cobertura_eia.csv` desde la hoja oficial `Monthly-States` del XLSX EIA-861M mediante [`scripts/preparar_eia.py`](../scripts/preparar_eia.py). El corte contiene 5,304 filas, 51 códigos de estado/DC, 4,896 meses `Final` y 408 `Preliminary`; periodo 2018–2025 completo y enero–agosto 2026 preliminar. Los MWh son ventas del sector residencial reportadas/agregadas por estado, no lecturas de medidores ni mediciones de la muestra ResStock. [Página Form EIA-861M](https://www.eia.gov/electricity/data/eia861m/)

### Tabla canónica `silver.eia_residential_sales_monthly`

| Campo | Tipo lógico | Regla |
|---|---|---|
| `period` | `YYYY-MM` | Periodo informado por EIA; no convertirlo en una hora inventada. |
| `state_code` | texto de 2 letras | Incluye `DC`; clave geográfica estatal. |
| `sector` | enum | `RES`. |
| `data_status` | enum | Preservar `Final`/`Preliminary`; dato preliminar no se marca final. |
| `sales_mwh` | decimal | MWh reportados en la fila original. |

PK: `(period, state_code, sector)`. Conservar el estado del dato en toda gráfica/modelo. En una simulación de streaming se conserva `period`; `ingested_at_utc`/`replay_id` solo indican cuándo se reprodujo el registro.

**Controles:** mes válido; clave única; venta finita y no negativa; estado de dato conocido; conteo mensual por estado cotejado con cobertura; meses faltantes explícitos; 2026 marcado preliminar en el corte examinado.

## 4. Clima: observación de reanálisis por punto

La tabla integrada contiene 336 filas: 168 horas por cada punto de Denver y Grand Junction del 1 al 7 de enero de 2018, con modelo `ERA5-Land`, timestamp UTC y temperatura a 2 m en °C. Es una celda de reanálisis consultada por punto, no una estación local ni una medida representativa de todo Colorado. La licencia de datos de Open-Meteo es CC BY 4.0; los términos del endpoint gratuito restringen el servicio a uso no comercial y permiten contenido educativo. [Licencia Open-Meteo](https://open-meteo.com/en/license) · [Términos](https://open-meteo.com/en/terms) · [Dataset ERA5-Land de Copernicus](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land?tab=overview)

### Tabla canónica `silver.climate_hourly_point`

Campos de la muestra: `punto_id`, `estado`, coordenadas solicitadas y de la celda, `timestamp_utc`, `temperatura_c`, `modelo`. PK: `(source_dataset_id, punto_id, timestamp_utc)`. Mantener las coordenadas de solicitud y las coordenadas de celda como campos separados.

**Controles:** timestamp UTC explícito y continuo por punto; unicidad de PK; °C como unidad declarada; modelo fijado; coordenadas finitas; valor finito; crédito/licencia y cambios visibles. No unir al consumo hasta acordar un mapeo geográfico compatible y conservar las zonas horarias de ambas fuentes.

## 5. Fuentes aún separadas y reglas de unión

- EIA-930 no forma parte de este contrato porque aún no hay extracción ni campo/unidad temporal confirmados.
- EIA mensual se puede comparar con agregados mensuales como análisis de escalas/poblaciones, con la población de cada serie explicada. No se une a cada vivienda ResStock.
- Clima se conserva por `punto_id`; no se interpreta como clima de todo el estado ni se une por cercanía aproximada sin documentar geografía, celda, huso y regla horaria.
- Los datos crudos permanecen inmutables en Bronze; las tablas de arriba son Silver; las agregaciones para tablero/modelo serían Gold, versionadas y trazables a los hashes de Bronze.

## 6. Decisiones y pendientes del equipo

1. Brian y Christian verifican que `state_code`, `housing_type` y peso vengan del índice de ResStock 2025 R1 y acuerdan el join por `bldg_id`.
2. El equipo decide el tipo físico de timestamp UTC y su serialización en S3/Parquet/Kinesis sin perder `timestamp_end_est`.
3. Omar define la envoltura de replay (`replay_id`, `ingested_at_utc`, idempotency key) sin sobrescribir periodo/event time de origen.
4. Diego define qué agregaciones Gold necesita el tablero y cómo distinguir datos finales/preliminares.
5. ResStock 2025 R1 declara CC BY 4.0 en su citation file. Al compartir los artefactos del proyecto, conservar cita, atribución NREL/DOE, enlace a licencia, aviso de cambios y nota de disclaimer/investigación del README.
