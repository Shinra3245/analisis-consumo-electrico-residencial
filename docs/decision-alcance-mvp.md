# Decisión inicial de alcance y MVP

**Fecha:** 16 de noviembre de 2026  
**Estado:** Recomendación técnica para ejecutar; revisar con el equipo después del avance del 17 de noviembre.  
**Base:** Propuesta V2 aprobada sin observaciones, guía de entrega del curso y revisión documental de fuentes. Esta decisión organiza el desarrollo y no cambia los objetivos académicos aprobados.

## Decisión ejecutiva

Construir primero un MVP reproducible, medible y demostrable con un subconjunto acotado de datos. No iniciar con la descarga y procesamiento de todos los perfiles individuales de ResStock ni activar infraestructura de nube hasta verificar acceso, formato, licencia, tamaño y costo.

El MVP usará como eje los **agregados geográficos de ResStock**, una muestra documentada de **estadística residencial oficial de EIA** y una extracción pequeña de **clima histórico de Open-Meteo**. Se mantendrán las tres fuentes en capas separadas; solo se compararán en una escala temporal y geográfica común cuando los datos lo permitan. La detección de anomalías se implementará sobre la serie de perfiles elegida y se evaluará con reglas o periodos de referencia explícitos. La estimación se presentará como escenario, salvo que la cobertura temporal permita una validación separada.

## Qué entra primero

1. **ResStock:** comenzar por `timeseries_aggregates` y `metadata_and_annual_results`. Inspeccionar el inventario de archivos y sus particiones; elegir una geografía y periodo que puedan procesarse en el entorno disponible. No fijar todavía cuántos estados, filas o perfiles se usarán: se decidirá después de ver tamaño, columnas, resolución y condiciones de uso.
2. **EIA residencial:** seleccionar una serie oficial de ventas residenciales por estado y periodo compatible con el análisis. Preferir inicialmente archivo público descargable o consulta manual reproducible; solicitar una clave gratuita de API solo si se necesita automatización, y acordarlo entre el equipo antes de gestionar la cuenta.
3. **Open-Meteo:** probar una ubicación representativa y el periodo histórico 2018 con una o dos variables justificadas. Mantener las peticiones acotadas, guardar atribución y comprobar el huso horario antes de unir la serie con perfiles.
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

1. Revisar este acuerdo después de la exposición del 17 de noviembre y registrar ajustes del profesor/equipo.
2. Hacer inventario de ResStock sin descargar el conjunto completo; identificar archivos agregados candidatos, tamaños y particiones.
3. Elegir un extracto de ResStock y una serie residencial EIA con intersección geográfica/temporal justificable.
4. Probar la consulta histórica de Open-Meteo para esa geografía y periodo.
5. Incorporar una muestra pequeña solo después de verificar sus condiciones de uso; registrar fuente, URL, fecha, periodo, tamaño, formato, hash, unidades y huso horario.
6. Implementar el primer flujo reproducible y actualizar el seguimiento con evidencia real.

## Evidencia y límites de la decisión

- El README de ResStock distingue resultados anuales/características, series agregadas geográficamente y series individuales; recomienda al menos 1,000 modelos para conclusiones con incertidumbre de 15%: [README oficial del release 2025.1 (OEDI)](https://oedi-data-lake.s3.amazonaws.com/nrel-pds-building-stock/end-use-load-profiles-for-us-building-stock/2025/resstock_amy2018_release_1/README_resstock_20251.pdf).
- La guía técnica indica que 550,000 muestras sin mejoras, a paso de 15 minutos, producen aproximadamente 500 GB: [ResStock Technical Reference Guide 2025.1](https://oedi-data-lake.s3.amazonaws.com/nrel-pds-building-stock/end-use-load-profiles-for-us-building-stock/2025/resstock_amy2018_release_1/ResStockTechnicalReferenceGuide_2025_1.pdf). Es una señal de escala; no equivale a un tamaño medido de los archivos que usará el MVP.
- La API v2 de EIA requiere una clave: [documentación oficial de EIA](https://www.eia.gov/opendata/documentation.php). No se solicitó ni se guardó ninguna clave.
- EIA describe EIA-930 como demanda calculada por Balancing Authority y explica convenciones horarias y transiciones DST: [EIA-930, información oficial](https://www.eia.gov/electricity/930-content/about.html).
- Open-Meteo limita el uso gratuito a casos no comerciales y exige atribución conforme a sus términos: [términos de Open-Meteo](https://open-meteo.com/en/terms). El equipo debe verificar que su uso académico concreto encaje en esos términos antes de incorporarlo.

La inspección hasta ahora ha sido documental. Esta recomendación no afirma que se descargaron datos, se probó el pipeline, se estimó rendimiento ni se aprobó un presupuesto cloud.
