# Catálogo de datos del proyecto

**Brian García Mares · Big Data**

**Consulta y extracción:** 17 de noviembre de 2026

## Inventario

| Fuente y versión | Periodo | Cobertura y unidad de observación | Resolución y medida | Formato de origen y extracción |
|---|---|---|---|---|
| ResStock 2025 Release 1, AMY 2018, baseline `upgrade=0` | Año meteorológico 2018 | Metadatos de 549,971 modelos por tipo de vivienda y ubicación en 50 estados y Washington D. C. Piloto individual de Colorado y Nueva York. Agregado de Colorado para vivienda unifamiliar aislada. | 15 minutos en series. Electricidad consumida en kWh por intervalo. En el agregado, el consumo ya está ponderado. | Metadatos Parquet por rangos HTTPS. Series Parquet individuales y agregado CSV de OEDI. |
| U.S. EIA, EIA-861M, hoja `Monthly-States` del histórico de ventas e ingresos | 2018–2025 finales. Enero–agosto de 2026 preliminares según el archivo consultado. | Un registro por mes, estado y sector `RES`. Incluye 50 estados y Washington D. C. | Mensual, ventas minoristas de electricidad en MWh. | XLSX público, descargado por HTTPS y normalizado a CSV. |
| Open-Meteo Historical Weather API, ERA5-Land | 1–7 de enero de 2018 en UTC | Dos puntos de Colorado, Denver y Grand Junction. La respuesta incluye la celda devuelta por el servicio. | Horaria. Temperatura a 2 m en °C. | JSON de la API, normalizado a CSV. |
| EIA-930 (previsto como contexto) | Por definir si se incluye | Demanda de la red eléctrica por autoridad de balance del territorio continental. | Horaria, según el campo y la unidad declarados por el servicio. | API o descargas EIA. Sin extracción en este corte. |

Los archivos obtenidos y derivados, sus fechas, tamaños, filas y huellas se documentan en [el manifiesto](../data/processed/piloto-datos/manifiesto.json). Del Parquet nacional se leyeron seis columnas usando 2,486,800 bytes HTTP de un objeto de 465,060,991 bytes. El registro de esa lectura incluye el identificador ETag del objeto. El SHA-256 de esa entrada queda vacío porque se leyó una proyección remota. Los dos CSV resultantes sí tienen hash.

## Campos utilizados

| Fuente | Campo | Interpretación y uso |
|---|---|---|
| ResStock metadatos | `bldg_id` | Identificador del modelo de vivienda. Une el índice y el perfil del mismo release y baseline. |
| ResStock metadatos | `completed_status`, `weight` | Estado de simulación y cantidad de unidades representadas por el modelo. Se eligieron simulaciones `Success` con peso positivo y tipo declarado. |
| ResStock metadatos | `in.state`, `in.county`, `in.geometry_building_type_recs` | Estado, identificador de condado en el formato de la fuente y clasificación RECS de la vivienda. Mantener el identificador de condado como texto. |
| ResStock individual | `timestamp` → `timestamp_fin_local` | Fin de intervalo de 15 minutos. En el piloto va del 1 de enero de 2018 a las 00:15 al 1 de enero de 2019 a las 00:00. El Parquet entrega timestamps sin zona incorporada. |
| ResStock individual | `out.electricity.total.energy_consumption..kwh` → `electricidad_kwh` | Energía eléctrica consumida por el modelo en el intervalo. El diccionario incluye carga y descarga de baterías en esta medida. |
| ResStock agregado | `models_used`, `units_represented` | Cantidad de modelos y unidades representadas, respectivamente. Son atributos del agregado, constantes durante la serie de Colorado. |
| ResStock agregado | `out.electricity.total.energy_consumption..kwh` | Energía eléctrica ponderada del grupo en el intervalo. Sumar por mes usando el inicio del intervalo y dividir entre 1,000 para obtener MWh. |
| EIA | `Year`, `Month`, `State`, `Data Status`, `Residential / Sales` | Periodo, estado, condición final o preliminar y ventas del sector residencial en MWh. La clave de la salida es `estado + sector + periodo`. |
| Open-Meteo | `hourly.time`, `hourly.temperature_2m`, `latitude`, `longitude` | Hora UTC y temperatura a 2 m en °C. Se guardan las coordenadas solicitadas y las de la celda retornada. La clave es `punto_id + timestamp_utc`. |

El release 2025.1 cambió nombres de columnas. El doble punto de `..kwh` forma parte del nombre original. El README vigente documenta 82 columnas omitidas de AMY 2018 y una ruta alternativa para agregados de upgrades 29–32. Los campos utilizados se comprobaron en el baseline. En Spark, el Parquet del piloto ya usa nombres sencillos para la serie individual. [README vigente](https://oedi-data-lake.s3.amazonaws.com/nrel-pds-building-stock/end-use-load-profiles-for-us-building-stock/2025/resstock_amy2018_release_1/README.md) · [Diccionario de esta versión](https://oedi-data-lake.s3.amazonaws.com/nrel-pds-building-stock/end-use-load-profiles-for-us-building-stock/2025/resstock_amy2018_release_1/data_dictionary.tsv) · [Avisos del repositorio](https://oedi-data-lake.s3.amazonaws.com/nrel-pds-building-stock/end-use-load-profiles-for-us-building-stock/KNOWN_ISSUES.md)

## Uso, publicación y atribución

| Fuente | Guardar crudo | Publicar derivados o adjuntar una muestra académica | Atribución |
|---|---|---|---|
| ResStock | Sí, bajo la licencia de datos CC BY 4.0 indicada para este release. El README dedica los datos a investigación. | Con atribución, enlace a licencia, fuente y aviso de cambios. Para entregar el proyecto conviene adjuntar el piloto reducido y conservar los originales recuperables mediante URL y manifiesto. | Citar ResStock 2025 Release 1 (AMY 2018), OEDI, el DOI, el [archivo de cita](https://oedi-data-lake.s3.amazonaws.com/nrel-pds-building-stock/end-use-load-profiles-for-us-building-stock/2025/resstock_amy2018_release_1/citation.txt) y la [guía técnica](https://oedi-data-lake.s3.amazonaws.com/nrel-pds-building-stock/end-use-load-profiles-for-us-building-stock/2025/resstock_amy2018_release_1/ResStockTechnicalReferenceGuide_2025_1.pdf). Indicar si se seleccionaron campos, perfiles o intervalos. |
| EIA | Sí, el archivo oficial de ventas es información gubernamental reutilizable. | Sí, identificar la serie y fecha de publicación o del corte, además de indicar transformación y filtros. | U.S. Energy Information Administration, EIA-861M, Sales and Revenue, histórico 2010–2026 (datos hasta agosto de 2026, consulta del 17 de noviembre de 2026). [Descarga oficial](https://www.eia.gov/electricity/data/eia861m/xls/sales_revenue.xlsx) · [Política de reutilización](https://www.eia.gov/about/copyrights_reuse.php) |
| Open-Meteo | Sí, los datos de la API están bajo CC BY 4.0. El acceso gratuito al servicio tiene condiciones de uso no comercial. | Sí, incluir atribución a Open-Meteo, identificar el modelo ERA5-Land, enlazar la licencia e indicar conversión o agregación. | Open-Meteo Historical Weather API, ERA5-Land del ECMWF/Copernicus Climate Change Service. [Documentación](https://open-meteo.com/en/docs/historical-weather-api) · [Términos](https://open-meteo.com/en/terms) |
| EIA-930 | La política de reutilización de EIA corresponde a sus datos oficiales. | Si se incorpora, publicar con atribución como contexto operativo de la red. | U.S. Energy Information Administration, Hourly Electric Grid Monitor, fuente y fecha de extracción. [Documentación](https://www.eia.gov/electricity/gridmonitor/about) |

Datos de ResStock atribuidos al National Renewable Energy Laboratory (NREL), con financiamiento del U.S. Department of Energy. [Repositorio OEDI, DOI 10.25984/1876417](https://doi.org/10.25984/1876417) · [Licencia CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

## Cobertura mensual y evaluación propuesta

La extracción contiene **5,304 registros EIA**. Cada uno de los 50 estados y D. C. tiene 12 meses finales por año entre 2018 y 2025 y ocho meses preliminares para 2026 en el archivo utilizado. El panel final de 2018–2025 contiene 4,896 registros. La tabla [cobertura EIA](../data/processed/piloto-datos/datos/cobertura_eia.csv) conserva el detalle por año, estado y sector.

| Bloque | Periodo | Meses por estado | Uso propuesto con Diego |
|---|---|---:|---|
| Entrenamiento | 2018–2023 | 72 | Ajuste inicial y comparación con un baseline estacional que predice con el mismo mes del año anterior. |
| Validación | 2024 | 12 | Selección del método y parámetros con orden temporal. |
| Prueba final | 2025 | 12 | Evaluación del método seleccionado en ventas residenciales EIA. |
| Monitoreo preliminar | Enero–agosto de 2026 | 8 | Vista informativa identificada como preliminar. |

EIA mide las ventas facturadas, cuyos periodos suelen abarcar entre 28 y 35 días. Al analizar cambios históricos se deben considerar revisiones de la fuente y las notas metodológicas de EIA. La evaluación anterior corresponde a ventas residenciales estatales. La demo de ResStock usa perfiles modelados del año meteorológico 2018. [Notas de EIA Electric Power Monthly](https://www.eia.gov/electricity/monthly/epm_table_grapher.php?t=table_5_02)

## Verificación semántica de Colorado 2018

| Medida | Valor comprobado |
|---|---:|
| Intervalos ResStock | 35,040 |
| Modelos utilizados en el agregado unifamiliar aislado | 5,869 |
| Unidades representadas por ponderación | 1,490,160.66 |
| Energía eléctrica modelada del grupo ResStock | 16,809,653.300 MWh |
| Ventas del sector residencial completo EIA | 19,286,952 MWh |
| Cociente entre totales | 87.155572% |

En el tablero conviene rotular el 87.16% como **«Relación entre totales anuales»**. La razón compara cifras de poblaciones y métodos distintos. Los cocientes mensuales se pueden revisar en [la reconstrucción de la demo](../data/processed/piloto-datos/datos/demo_colorado_2018_verificacion.csv). Para conservar la asignación temporal, el intervalo que termina el 1 de enero de 2019 a las 00:00 se contabiliza en diciembre de 2018.

## Clima y decisión sobre la unión de tablas

La prueba de Open-Meteo contiene 336 horas-punto válidas en total, 168 por punto. Denver y Grand Junction representan las celdas de consulta de esos lugares. El catálogo conserva su alcance como muestra de dos puntos.

Los metadatos ResStock traen la dimensión de condado. Para una unión futura, validar el mapeo de identificadores tal como aparecen en origen, elegir y documentar coordenadas o celdas por condado y revisar el huso horario estándar de la simulación. Algunos identificadores de condado tienen un formato distinto de `G0800310`, por ejemplo en Alaska. El timestamp local de fin de intervalo requiere una regla geográfica antes de convertirse a UTC. Para comparar temperatura horaria, consolidar los cuatro intervalos de electricidad de cada hora compatible. En este corte, el clima puede mostrarse como una serie descriptiva por punto.
