# Validación inicial de fuentes

Primer avance investigativo para la revisión del 17 de noviembre. **Fecha de consulta: 16 de noviembre de 2026.** Es una revisión breve de documentación oficial y de accesos públicos, no una validación exhaustiva. No se descargó ningún dataset ni se registró ninguna cuenta o clave.

Leyenda: **Confirmado** = visto en la fuente oficial citada. **No confirmado** = no se encontró o no se comprobó. **Pendiente** = por hacer.

## Matriz

| Aspecto | ResStock 2025.1 | EIA | Open-Meteo |
|---|---|---|---|
| Fuente oficial / documentación | [README del release en OEDI](https://oedi-data-lake.s3.amazonaws.com/nrel-pds-building-stock/end-use-load-profiles-for-us-building-stock/2025/resstock_amy2018_release_1/README.md); [sitio ResStock](https://nrel.github.io/ResStock.github.io/docs/data.html); [guía técnica 2025.1](https://nrel.github.io/ResStock.github.io/assets/trd/ResStockTechnicalReferenceGuide_2025_1.pdf) | [Documentación de API v2 de EIA](https://www.eia.gov/opendata/documentation.php) | [Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api); [términos de uso](https://open-meteo.com/en/terms) |
| Propósito en el proyecto | Perfiles residenciales modelados, características de vivienda y resúmenes por estado | Series mensuales/anuales por estado y demanda horaria del sistema | Temperatura y otras variables meteorológicas |
| Acceso comprobado | **Confirmado:** el listado público del bucket de OEDI responde y muestra, bajo `2025/resstock_amy2018_release_1/`, las carpetas `metadata_and_annual_results`, `timeseries_aggregates`, `timeseries_individual_buildings`, `weather`, `building_energy_models` y `geographic_information`. El README se leyó. **No se descargó ningún dato.** | **Confirmado:** la página de documentación carga. **No confirmado:** acceso a datos, porque la API exige clave y no se solicitó. | **Confirmado:** una consulta de prueba al endpoint de pronóstico (temperatura horaria, 1 día) respondió JSON sin clave. No se probó el endpoint histórico. |
| Cobertura | **Confirmado (README):** los 50 estados y D.C.; Alaska y Hawaii son nuevos en este release. Año meteorológico real 2018 (NOAA ISD, NSRDB, MesoWest). La guía técnica describe corridas de 550,000 muestras; no se ha contado ni inspeccionado el inventario publicado. | **No confirmado:** estados, sectores y rutas concretas. La propuesta menciona 48 estados contiguos para la demanda horaria; no se verificó. | **Confirmado (docs):** el API histórico indica datos desde 1940 con resolución horaria (ERA5, 0.25°; ERA5-Land, 0.1°, desde 1950). |
| Granularidad | **Confirmado (guía técnica):** salida con paso de 15 minutos. La guía estima unos 500 GB de salida para 550,000 muestras sin mejoras; no es medición del subconjunto ni del tamaño descargable del MVP. | **No confirmado:** frecuencia por ruta y retrasos de publicación. | **Confirmado:** horaria en la prueba de pronóstico y en la documentación histórica. |
| Formato | **Confirmado (README):** se ofrecen Parquet y CSV, entre otros formatos. **No confirmado:** formato por carpeta y tamaño real. | **Confirmado (docs):** API REST; devuelve como máximo 5,000 filas en JSON por consulta, con paginación mediante `offset`; también admite XML (`out=xml`). Desde v2.1.6 los valores JSON se devuelven como cadenas. | **Confirmado:** JSON (prueba realizada). |
| Licencia / atribución | **Parcial:** OEDI indica en su pie de página "Creative Commons Attribution 4.0 unless otherwise noted". El README pide una cita (APA) y esta leyenda: "Data includes information from the ResStock™ dataset developed by the National Renewable Energy Laboratory (NREL) with funding from the U.S. Department of Energy (DOE)". Incluye un descargo de responsabilidad: datos "as is", para investigación. **No confirmado:** que la licencia del release permita redistribuir. | **No confirmado:** términos de uso y atribución exigida; no se revisaron. | **Confirmado (términos):** el uso gratuito es no comercial, con datos bajo CC BY 4.0. Límites: menos de 10,000 llamadas/día, 5,000/hora y 600/min. Quedan los planes de pago para uso comercial. |
| Avisos de la fuente | **Confirmado (README):** 82 columnas de resultados se omitieron de este release y no se añadirán (cargas por componente y carga de respaldo de bomba de calor). Los agregados de las mejoras 29–32 no están en `timeseries_aggregates/`. | — | — |

## Pendientes

1. **ResStock:** listar (sin descargar) los archivos de `timeseries_aggregates` y `metadata_and_annual_results` para elegir candidatos del MVP y confirmar su formato, tamaño, cobertura y granularidad efectiva. Revisar `KNOWN_ISSUES.md` del repositorio de datos y confirmar la licencia vigente del release. Inspeccionar series individuales solo si una prueba acotada lo justifica.
2. **EIA:** decidir si el equipo solicita la clave gratuita (acción con cuenta personal, requiere acuerdo del equipo). Después, consultar los metadatos de las rutas `electricity/retail-sales` y `electricity/rto` para confirmar estados, sectores, unidades, fechas y retrasos. Revisar los términos de uso y la atribución.
3. **Open-Meteo:** probar el endpoint histórico con una ubicación y fechas de 2018. Verificar la alineación de zona horaria y las variables útiles. Confirmar si el proyecto cuenta como uso no comercial y estimar el número de llamadas necesarias.
4. **Comunes:** registrar hash, número de registros y versión en cada extracción, según el procedimiento de [fuentes-de-datos.md](fuentes-de-datos.md).

## Limitaciones de esta revisión

- Las páginas de ResStock se leyeron desde el espejo en OEDI y GitHub; `resstock.nrel.gov` no respondió desde este entorno. La guía técnica se consultó, pero no se descargaron ni inspeccionaron archivos de datos.
- Los datos de EIA y los términos de EIA no se revisaron.
- La granularidad de 15 minutos y la escala de 550,000 muestras/~500 GB se verificaron en la guía técnica, no en archivos descargados. La cifra de 350.4 millones de filas para 10,000 perfiles es una proyección aritmética de la propuesta, no una cantidad observada.
- Los términos de uso pueden cambiar; la fecha de consulta es la referencia.
