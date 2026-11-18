# Guía breve para demostrar el proyecto

## Qué busca hacer

El proyecto explora el consumo eléctrico residencial en Estados Unidos con tres fuentes que se mantienen identificadas por separado: perfiles de vivienda modelados, ventas eléctricas oficiales y clima de reanálisis. El tablero permite revisar patrones, cambios inusuales, una evaluación temporal de estimaciones y la procedencia/calidad de los datos.

## Fuentes consultadas

| Fuente | Qué aporta | Enlace y alcance usado |
|---|---|---|
| ResStock 2025.1 / OEDI | Perfiles residenciales simulados con intervalos de 15 minutos | [Archivo agregado de Colorado](https://oedi-data-lake.s3.amazonaws.com/nrel-pds-building-stock/end-use-load-profiles-for-us-building-stock/2025/resstock_amy2018_release_1/timeseries_aggregates/by_state/upgrade=0/state=CO/up00-co-single-family_detached.csv), [README del release](https://oedi-data-lake.s3.amazonaws.com/nrel-pds-building-stock/end-use-load-profiles-for-us-building-stock/2025/resstock_amy2018_release_1/README.md) y [registro del conjunto OEDI](https://data.openei.org/submissions/4520). El dashboard del repositorio incluye 10 perfiles; el lote local exploratorio amplió a 50. |
| EIA-861M | Ventas mensuales de electricidad al sector residencial por jurisdicción | [Descarga mensual EIA-861M](https://www.eia.gov/electricity/data/eia861m/). El backtest usa meses `Final` de 2018–2025; los preliminares de 2026 se excluyen del ajuste. |
| Open-Meteo / ERA5-Land | Temperatura horaria de reanálisis para puntos consultados | [API histórica](https://open-meteo.com/en/docs/historical-weather-api), [términos](https://open-meteo.com/en/terms) y [licencia de datos](https://open-meteo.com/en/license). La serie se muestra en UTC y todavía no se une al consumo. |
| NOAA/NWS | Límites de condados y referencia para resolver zonas IANA | [Cartografía de condados](https://www.weather.gov/gis/Counties), versión `c_16ap26` usada para el lote de 50. |

Las reglas de atribución, licencias y publicación se detallan en [`decision-publicacion-datos.md`](decision-publicacion-datos.md). Los datos del dashboard no deben describirse como mediciones de medidores domésticos.

## Cómo recorrer el tablero

La versión incluida en el repositorio se abre localmente con:

```bash
python3 -m http.server 8000 -d tablero
```

Abre `http://localhost:8000/`. En la sesión actual también está disponible, mientras el servidor local siga activo, el paquete ampliado de 50 perfiles en `http://localhost:8768/`. Es una demo local, no un sitio público.

1. **Resumen:** presenta de qué fuente viene cada dato y cuántos perfiles modelados incluye el manifiesto cargado.
2. **Patrones:** compara perfiles por mes y muestra un mapa horario en hora local; cambia día laboral/fin de semana y zona horaria. Los meses parciales se marcan.
3. **Clima:** permite ver las lecturas horarias por punto en UTC. No hay unión con consumo ni afirmación de causalidad.
4. **Anomalías:** lista candidatos de variación interanual. La tabla sintética mide sensibilidad a cambios artificialmente inyectados; no valida eventos reales.
5. **Estimaciones:** compara ventas observadas, una línea base estacional y el modelo log-lineal en el holdout 2024–2025. Es backtest histórico, no una proyección futura.
6. **Flujo/Calidad:** muestra cobertura, manifiesto y hashes para explicar cómo se revisa la integridad.

## Resultados que se pueden explicar

- La versión principal del dashboard incorpora 10 perfiles ResStock; cada uno tiene 35,040 intervalos de 15 minutos en 2018. La ampliación exploratoria de 50 perfiles y 1,752,000 intervalos se ejecutó localmente y sus archivos Gold permanecen en `/tmp`.
- En 5,304 filas EIA se detectaron 43 candidatos estadísticos en meses `Final` y 3 candidatos separados en meses preliminares. Son señales para revisar, no anomalías confirmadas.
- En el test sintético, el detector recuperó 57.5% de los cambios inyectados de ±30% y 94.1% de los de ±50%; el test no demuestra desempeño ante eventos reales.
- Para el backtest de 2024–2025, la mediana sMAPE fue 5.71% para el modelo y 7.05% para la baseline; el modelo mejoró en 46 de 51 jurisdicciones. Solo se probó un corte temporal.
- La razón descriptiva 87.16% entre ResStock y EIA no se reproduce desde el agregado fuente que falta; no se debe presentar como precisión ni como validación.

## Qué se hizo en AWS

Se almacenó un HTML autónomo de 8.5 MB en el prefijo `site/` de un bucket S3 del equipo, región `us-east-1`. El objeto incluye el dashboard y las tablas Gold versionadas del piloto de 10 perfiles. El bucket continúa privado; se generó una URL prefirmada temporal desde la consola, de cuatro horas como máximo o hasta que venza la sesión del Learner Lab. El enlace se copió al portapapeles y no se guarda en Git. Instrucciones: [`despliegue-temporal-s3.md`](despliegue-temporal-s3.md).

La nube no constituye todavía un flujo integral: EMR Serverless no inició por falta de permisos, Kinesis no tiene un stream creado y CloudFront no está desplegado. Por ello no existe una dirección permanente ni ingestión continua en AWS. En la presentación, describir S3 como almacenamiento de un artefacto web privado, no como el pipeline completo.

## Documentos de apoyo

- [Resultados y cobertura de la muestra inicial](resultados-muestra-inicial.md)
- [Lote exploratorio de 50 perfiles](lote-resstock-50.md)
- [Métodos y métricas de anomalías y backtest](analitica-anomalias-pronostico.md)
- [Despliegue temporal privado de S3](despliegue-temporal-s3.md)
