# Decisión inicial de alcance y MVP

**Fecha:** 16 de noviembre de 2026  
**Estado:** Piloto inicial medido el 16 de noviembre; revisar con el equipo después del avance del 17 de noviembre.
**Base:** Propuesta V2 aprobada sin observaciones, guía de entrega del curso y revisión documental de fuentes. Esta decisión organiza el desarrollo y no cambia los objetivos académicos aprobados.

## Decisión ejecutiva

Construir primero un MVP reproducible, medible y demostrable con un subconjunto acotado de datos. No iniciar con la descarga y procesamiento de todos los perfiles individuales de ResStock ni activar infraestructura de nube hasta verificar acceso, formato, licencia, tamaño y costo.

El MVP usará como eje los **agregados geográficos de ResStock**, una muestra documentada de **estadística residencial oficial de EIA** y una extracción pequeña de **clima histórico de Open-Meteo**. Se mantendrán las tres fuentes en capas separadas; solo se compararán en una escala temporal y geográfica común cuando los datos lo permitan. La detección de anomalías se implementará sobre la serie de perfiles elegida y se evaluará con reglas o periodos de referencia explícitos. La estimación se presentará como escenario, salvo que la cobertura temporal permita una validación separada.

## Qué entra primero

1. **ResStock:** empezar por `timeseries_aggregates` y `metadata_and_annual_results`. La primera candidata medida es Colorado, `upgrade=0`, vivienda unifamiliar separada; su agregado de 31 MB permite un piloto local. No implica que esta categoría/estado sea el alcance total final.
2. **EIA residencial:** usar como referencia inicial el libro público mensual `sales_revenue.xlsx`, hoja `Monthly-States`; se extrajeron los 12 meses finales de Colorado para 2018. Solicitar una clave de API solo si luego se necesita automatización, con acuerdo del equipo.
3. **Open-Meteo:** la prueba histórica de 2018 se hizo para temperatura en un punto de Denver. Se conserva separada hasta resolver representatividad espacial y alineación horaria con el perfil estatal.
4. **Procesamiento:** implementar primero inventario, validación de esquema, trazabilidad y agregaciones reproducibles; después análisis descriptivo y una detección de anomalías sencilla con métricas o ejemplos verificables.
5. **Demostración de flujo:** reproducir históricamente una muestra ya validada para mostrar procesamiento progresivo, rotulándolo siempre como replay simulado y no como telemetría en vivo.

## Elementos pospuestos o condicionados

- **10,000 perfiles individuales y 350.4 millones de filas:** meta de escala de la propuesta, no criterio para el primer MVP. La guía técnica de ResStock estima unos 500 GB de salida para 550,000 muestras a intervalos de 15 minutos. Primero se medirá el subconjunto real y luego se decidirá si una muestra individual es viable. ResStock recomienda al menos 1,000 modelos representativos para limitar la incertidumbre a 15%; si el trabajo usa menos, se describirá como demostración exploratoria y no como estimación representativa del parque residencial.
- **EIA-930 (demanda horaria de red):** opcional y posterior a la validación del eje residencial. Es una serie de demanda de sistemas eléctricos, no consumo doméstico; sus marcas usan convenciones de hora de cierre y pueden presentar días de 23/25 horas por horario de verano. Si se incluye, aparecerá como contexto independiente y se documentará el tratamiento de zona horaria.
- **AWS S3, Kinesis y EMR:** conservar como arquitectura objetivo de la propuesta, pero iniciar localmente con datos pequeños. Cualquier recurso con costo requiere estimación y acuerdo del equipo antes de activarse. La prueba cloud se decide cuando haya una operación reproducible y volumen medido que justifique la migración.
- **Cobertura nacional completa, tablero final y automatización:** se incorporan después de cerrar los contratos de datos y medir el MVP. No se presentará como logrado hasta tener evidencia integrada.

## Criterios para ampliar el alcance

Se podrá pasar de la muestra inicial a más perfiles/estados o a nube cuando estén documentados: (a) licencia y atribución; (b) inventario y volumen descargable; (c) columnas, unidades, zona horaria y cobertura; (d) consumo de recursos y tiempo de procesamiento en una prueba local; y (e) una decisión de equipo sobre costos. Si el tamaño o acceso no resulta viable antes de la entrega, se conservará el agregado geográfico y se explicará la limitación; no se sustituirán datos ausentes por cifras inventadas.

## Próximo bloque de trabajo

1. Presentar el resultado de la muestra y registrar comentarios del profesor/equipo después de la revisión del 17 de noviembre.
2. Revisar el aviso de columnas del release y los términos/atribuciones específicas de ResStock y EIA.
3. Ajustar el piloto mensual por tipo de vivienda y validar que la comparación con EIA se comunique como exploratoria.
4. Resolver qué cobertura climática representa la geografía y cómo alinear EST de ResStock con UTC/clima local antes de fusionar.
5. Ampliar el flujo solo con base en datos y costo medidos; mantener las fuentes originales fuera de Git.

La primera muestra ya fue procesada; cifras, hashes y controles están en [`resultados-muestra-inicial.md`](resultados-muestra-inicial.md), con reproducción mediante `scripts/analizar_muestra_inicial.py`.

## Evidencia y límites de la decisión

- La documentación de ResStock distingue resultados anuales/características, series agregadas geográficamente y series individuales; recomienda al menos 1,000 modelos para conclusiones con incertidumbre de 15%: [datos oficiales de ResStock](https://natlabrockies.github.io/ResStock.github.io/docs/data.html) y [FAQ](https://natlabrockies.github.io/ResStock.github.io/docs/FAQ.html).
- La guía técnica indica que 550,000 muestras sin mejoras, a paso de 15 minutos, producen aproximadamente 500 GB: [ResStock Technical Reference Guide 2025.1](https://oedi-data-lake.s3.amazonaws.com/nrel-pds-building-stock/end-use-load-profiles-for-us-building-stock/2025/resstock_amy2018_release_1/ResStockTechnicalReferenceGuide_2025_1.pdf). Es una señal de escala; no equivale a un tamaño medido de los archivos que usará el MVP.
- La API v2 de EIA requiere una clave: [documentación oficial de EIA](https://www.eia.gov/opendata/documentation.php). No se solicitó ni se guardó ninguna clave.
- EIA describe EIA-930 como demanda calculada por Balancing Authority y explica convenciones horarias y transiciones DST: [EIA-930, información oficial](https://www.eia.gov/electricity/930-content/about.html).
- Open-Meteo limita el uso gratuito a casos no comerciales y exige atribución conforme a sus términos: [términos de Open-Meteo](https://open-meteo.com/en/terms). El equipo debe verificar que su uso académico concreto encaje en esos términos antes de incorporarlo.

La muestra local y sus controles se documentan en [`resultados-muestra-inicial.md`](resultados-muestra-inicial.md). Se midió solo este agregado: no se descargó el conjunto completo, no se implementó un pipeline de producción, no se midió escalamiento ni se aprobó un presupuesto cloud.
