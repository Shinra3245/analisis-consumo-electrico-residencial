# Plan operativo de desarrollo — propuesta V2 y observaciones del profesor

**Estado:** guía de trabajo para los siguientes bloques del proyecto.  
**Base académica:** propuesta V2 aprobada por el profesor; plantilla *Big Data Project Proposal Template*; observaciones recibidas después de la demostración.  
**Regla de uso:** este documento define el orden, los pasos, los entregables y los criterios de cierre. Cada bloque debe actualizar su estado con evidencia antes de iniciar los que dependan de él. No se deben presentar metas, candidatos, salidas locales o diseños como resultados ya desplegados.

## 1. Propósito

Continuar el desarrollo de una plataforma que analice consumo eléctrico residencial de Estados Unidos incorporando contexto demográfico y meteorológico, estimaciones reproducibles, detección de anomalías, un dashboard explicativo y almacenamiento organizado en AWS.

La plantilla de Big Data contiene doce secciones. Este plan contribuye a objetivos SMART, alcance, requisitos, arquitectura, fuentes y metodología, riesgos y métricas. Los números ilustrativos de la plantilla (por ejemplo, disponibilidad de 99.9%, carga en menos de 3 segundos o fases de 24 semanas) no se consideran requisitos del profesor si no fueron establecidos como tales.

## 2. Principios que todo bloque debe respetar

1. **Separar universos de datos.** ResStock contiene perfiles de viviendas modelados; EIA publica ventas eléctricas agregadas por estado y sector; clima y población son fuentes externas de contexto. No se deben fusionar como si describieran los mismos hogares.
2. **Mantener el grano explícito.** Cada tabla, métrica y gráfica indica su unidad geográfica, periodo, frecuencia, unidad física y fuente.
3. **Alinear periodos antes de comparar.** El primer cruce demográfico se realizará para 2020–2025, periodo cubierto por las estimaciones estatales del Census Bureau y por los datos históricos de EIA. Las ventas EIA de 2018–2019 pueden seguir mostrándose como historial, pero no se incorporarán a la tabla demográfica hasta decidir y documentar una serie poblacional compatible.
4. **Prevenir fuga de información.** Ningún atributo observado después de la fecha de predicción puede utilizarse como entrada de una predicción histórica. Los meses de prueba se conservan fuera del ajuste y selección del modelo.
5. **Separar predicción de escenario.** Una estimación condicionada a clima observado no es un pronóstico operativo. Una previsión meteorológica de pocos días no sustenta por sí sola un pronóstico de energía anual.
6. **Etiquetar el nivel de evidencia.** Usar `VERIFICADO`, `PARCIAL`, `CANDIDATO`, `SINTÉTICO`, `NO REPRODUCIDO` o `PENDIENTE` según corresponda. Una alerta estadística no demuestra una anomalía real ni una falla eléctrica.
7. **No ampliar sin medición.** Los 10,000 identificadores ResStock son candidatos, no perfiles descargados. La muestra local de 50 perfiles equivale a 1,752,000 intervalos; el paquete versionado en Git/S3 contiene 10 perfiles (350,400 intervalos).
8. **Mantener AWS privado y acotado.** No hacer público el bucket para facilitar una demostración. No subir secretos. Los archivos fuente solo se conservarán o redistribuirán si su licencia y las reglas del proyecto lo permiten.

## 3. Estado de partida conocido

La revisión del repositorio y la demostración permiten fijar este punto inicial. Debe actualizarse si cambia la evidencia:

- El dashboard local tiene seis vistas y consume datos Gold del manifiesto; la versión actual de S3 abrió con visualizaciones vacías y todavía debe corregirse y verificarse antes de presentarse como publicación funcional.
- El conjunto versionado contiene 10 perfiles ResStock de 2018, datos mensuales EIA y una muestra climática horaria de dos puntos en Colorado. La serie EIA llega a agosto de 2026; los datos recientes preliminares se mantienen separados.
- Se procesó localmente un lote exploratorio de 50 perfiles (1,752,000 intervalos, 21 controles de calidad aprobados). No está en el dashboard versionado ni en S3.
- El análisis EIA actual incluye un detector estadístico exploratorio y un backtest de regresión log-lineal frente a una línea base estacional. No es todavía un modelo de ML aprobado como resultado final y no produce predicción futura verificada.
- La consola de Learner Lab mostró la región `us-east-1` y un bucket S3 privado con prefijos `gold/` y `site/`. EMR Serverless no inició por permisos insuficientes; no se creó Kinesis ni se desplegó CloudFront.
- La documentación de arquitectura aún contiene datos de planeación antiguos que indican `mx-central-1` y ausencia de recursos. Antes de usarla como descripción del estado real, armonizarla con la consola observada y mantener separadas arquitectura objetivo y configuración efectiva.

## 4. Decisiones iniciales de alcance

Estas decisiones acotan la primera implementación adicional; pueden cambiarse solo mediante una decisión de equipo documentada.

| Tema | Decisión de trabajo | Motivo y límite |
|---|---|---|
| Geografía inicial | 50 estados y District of Columbia, presentando DC como jurisdicción separada | EIA proporciona ventas por estado/sector; la población y superficie deben unirse por FIPS o código estatal validado. |
| Comparación energía-demografía | Estado × año; primer periodo integrado 2020–2025 | Coincide con las estimaciones estatales Census Vintage 2025. Se excluye 2026 preliminar de totales anuales. |
| Métricas de comparación | Ventas residenciales totales (MWh/año), población, densidad (personas/milla²) y consumo residencial per cápita (kWh/persona/año) | El total favorece estados poblados; per cápita permite una comparación normalizada. Densidad es una variable contextual, no causal. |
| Predicción inicial | Ventas eléctricas mensuales EIA del sector residencial por estado | Es una serie histórica real agregada y tiene más de un año; no equivale a predicción de una vivienda. |
| Predicción por vivienda | Pospuesta | ResStock disponible para el análisis detallado corresponde a 2018; un año y 50 modelos no permiten demostrar una predicción longitudinal residencial fiable. |
| Comparación por ciudad | Fase posterior y condicionada a una fuente de energía con geografía municipal comparable | EIA integrado está por estado. No se debe unir población de una ciudad con ventas estatales. |
| Clima histórico estatal | NOAA NClimDiv mensual, incluyendo temperatura, HDD y CDD | Alinea mejor con EIA mensual/estatal que la muestra puntual actual. Open-Meteo de dos puntos se conserva como muestra separada. |
| Clima futuro | Open-Meteo Forecast solo como contexto de corto plazo en una primera iteración | Su horizonte general llega hasta 16 días; no equivale a previsión climática anual. No usar clima observado futuro como entrada de un backtest. |
| Modelo de ML adicional | Random Forest global para la serie mensual EIA por estado, comparado con Seasonal Naive y el modelo log-lineal actual | Debe demostrar evaluación cronológica y reproducibilidad; no se asumirá que ML mejora hasta medirlo. |

El Census Bureau publica estimaciones anuales estatales 2020–2025 y aclara que las series de cada vintage revisan años previos desde el último censo. Usar una sola vintage para la comparación. Para contexto, California fue el estado más poblado en la estimación de julio de 2025; Nueva Jersey tuvo la densidad más alta en el Censo de 2020. Población total y densidad son indicadores diferentes.

## 5. Bloques de trabajo y pasos obligatorios

### Bloque 0 — Congelar contratos, estado y reproducibilidad

**Objetivo:** asegurar una base común antes de agregar fuentes y métricas.

**Pasos**

1. Confirmar rama y commit base de trabajo; revisar el árbol de Git y conservar cambios ajenos.
2. Registrar las versiones actuales de los contratos Gold, manifiesto, EIA, ResStock y clima.
3. Definir un diccionario breve: `state_fips`, `state_code`, `period`, `data_status`, unidades, zona horaria y campos de procedencia.
4. Corregir la documentación AWS para distinguir: configuración observada, objetivos de arquitectura y servicios bloqueados. Resolver región documentada versus región observada.
5. Abrir la copia local del dashboard y la URL S3 temporal por separado; registrar qué versión funciona y qué error muestra la publicación S3. No reutilizar la URL prefirmada expirada.

**Entregables:** registro del estado inicial, contrato de geografía/tiempo/unidades y discrepancias documentales identificadas.

**Criterio de salida:** el equipo puede decir qué versión tiene 10 perfiles, cuál contiene 50, qué se encuentra en S3 y qué servicios no están activos, sin contradicciones.

### Bloque 1 — Integrar demografía y densidad poblacional

**Fuentes de referencia**

- Census Bureau, población estatal 2020–2025, Vintage 2025: <https://www.census.gov/data/datasets/time-series/demo/popest/2020s-state-total.html>
- Census Bureau, densidad por estados y años censales: <https://www.census.gov/data/tables/time-series/dec/population-density.html>
- Población estimada por ciudades 2020–2025, solo como fuente de población para una futura fase municipal: <https://www.census.gov/data/tables/time-series/demo/popest/2020s-total-cities-and-towns.html>

**Pasos**

1. Obtener las estimaciones oficiales 2020–2025 y registrar descarga, vintage, fecha de consulta, licencia/atribución, tamaño y SHA-256.
2. Seleccionar los campos de población residente por estado, año y FIPS. Verificar claves únicas y excluir totales agregados nacionales/regionales del join.
3. Obtener superficie terrestre estatal del Census 2020. Calcular densidad anual como `población estimada del año / superficie terrestre 2020` y nombrarla `estimated_population_per_sq_mile`; no mezclarla con una densidad oficial decenal sin indicarlo.
4. Filtrar EIA a `sector=RES`, sumar los 12 meses finales de cada estado/año para 2020–2025 y rechazar años con meses faltantes o preliminares no resueltos.
5. Unir por FIPS/estado y año. Validar las 51 jurisdicciones y el número esperado de combinaciones; documentar cualquier jurisdicción sin equivalencia.
6. Calcular `residential_kwh_per_capita = residential_sales_mwh * 1000 / population_estimate`. Usar población de mitad de año como denominador aproximado del consumo anual y declarar esta convención.
7. Producir una tabla ordenable con ventas totales, población, densidad y kWh/persona; conservar la población total y el consumo total, no ocultarlos al normalizar.
8. Añadir controles de rango, duplicados, nulos, valores positivos, cobertura temporal y consistencia de conversiones.

**Contrato propuesto para `gold_state_energy_demographics`**

`state_fips, state_code, year, population_estimate, land_area_sq_mi_2020, estimated_population_per_sq_mile, residential_sales_mwh, residential_kwh_per_capita, eia_data_status, census_vintage, source_version`.

**Criterios de salida**

- Todos los registros se pueden rastrear a un archivo fuente y a su vintage.
- Las cifras de 2020–2025 usan el mismo criterio de datos finales EIA y una sola vintage Census.
- Se identifica correctamente el estado de mayor población y se muestra por separado el de mayor densidad, con su año de referencia.
- Una revisión independiente reproduce cálculos y conteos desde las fuentes documentadas.

### Bloque 2 — Clima estatal y alineación temporal

**Fuentes**

- NOAA/NCEI, base mensual nClimDiv con cobertura estatal, temperatura, precipitación, HDD y CDD: <https://www.ncei.noaa.gov/metadata/geoportal/rest/metadata/item/gov.noaa.ncdc%3AC00005/html>
- Resumen y descarga del dataset: <https://www.drought.gov/data-maps-tools/climate-division-datasets-nclimdiv>
- Open-Meteo Historical Weather: <https://open-meteo.com/en/docs/historical-weather-api>
- Open-Meteo Forecast: <https://open-meteo.com/en/docs>

**Pasos**

1. Adquirir serie mensual estatal de temperatura media, grados-día de calefacción y grados-día de enfriamiento (HDD/CDD) para los años que coincidan con EIA; registrar si cada mes es final o preliminar según NOAA.
2. Confirmar la cobertura por estado y las reglas especiales para Alaska, Hawái y DC; documentar ausencias en vez de imputarlas en silencio.
3. Normalizar periodos a `YYYY-MM`, unidades y estado de publicación; no convertir una agregación estatal en una medición de ciudad.
4. Conservar la muestra Open-Meteo de dos puntos como producto de punto/localidad. No presentarla como clima estatal ni unirla directamente a perfiles ResStock nacionales.
5. Crear vistas descriptivas que permitan comparar consumo y clima por estado/mes. Usar lenguaje de asociación o coincidencia temporal, no de causalidad.
6. Añadir pronóstico meteorológico Open-Meteo separado del clima histórico, mostrando ubicación, hora local, fecha de consulta y horizonte. La API general puede entregar hasta 16 días; no extrapolar ese horizonte a un pronóstico anual.
7. Para modelar, usar solo variables conocidas al instante de emisión. No introducir temperaturas observadas del periodo objetivo en una evaluación presentada como pronóstico. Si se requiere evaluar un modelo condicionado a clima real, etiquetarlo como retrospectivo/condicional y mantenerlo separado del pronóstico operativo.

**Contrato propuesto para `gold_state_climate_monthly`**

`state_fips, state_code, period, temperature_mean_c, precipitation_mm, hdd, cdd, climate_data_status, climate_source, climate_vintage, source_version`.

**Criterios de salida**

- La cobertura geográfica y mensual está declarada y se comprueba antes de unirla con EIA.
- El dashboard distingue clima histórico estatal, muestra histórica puntual y pronóstico meteorológico.
- No se afirma que clima y consumo se hayan relacionado causalmente.

### Bloque 3 — Comparación estatal y componente demográfico del dashboard

**Pasos**

1. Mantener las seis vistas existentes y ampliar **Resumen** y/o **Patrones** con una sección de comparación entre estados.
2. Mostrar ranking de población, ranking de densidad y ranking de ventas eléctricas como clasificaciones distintas.
3. Construir un gráfico de dispersión: eje X = densidad estimada; eje Y = kWh residenciales por persona/año; tamaño del punto = población; tooltip = estado, ventas MWh, población y año.
4. Permitir escoger año 2020–2025 y filtrar el estado. Indicar `Final`/`Preliminary` cuando aplique y excluir años incompletos del ranking anual.
5. No usar mapa por ciudad o polígonos si las fronteras y datos del consumo no tienen el mismo nivel geográfico.
6. Añadir en la vista Flujo/Calidad cantidad de filas, periodo, claves, hash y fecha de cada tabla cargada.
7. Mantener etiquetas visibles: “ventas residenciales agregadas”, “perfiles modelados” y “datos climáticos”.

**Criterios de salida**

- Al cambiar el año, todos los rankings y gráficas reflejan el mismo año y filtros.
- La visualización deja claro que mayor población, mayor densidad y mayor consumo total no son equivalentes.
- Totales y valores per cápita usan unidades visibles y su cálculo queda documentado.

### Bloque 4 — Modelo de aprendizaje automático para predicción

**Objetivo definido:** estimar ventas eléctricas mensuales del sector residencial por estado, usando como base la serie EIA. El resultado no es consumo individual de viviendas.

**Modelos a comparar**

1. Baseline estacional ingenua.
2. Regresión log-lineal actual, conservada como referencia.
3. Modelo de ML `RandomForestRegressor` global con codificación de estado y variables temporales/externas disponibles al momento de predecir.

**Variables candidatas**

- Estado, mes del año y tendencia temporal.
- Ventas residenciales rezagadas (`lag_1`, `lag_12`) y medias móviles calculadas solo con meses previos.
- Población estimada disponible en la fecha de corte y densidad derivada de superficie Census 2020.
- Normales climáticas estatales por mes calculadas únicamente con el conjunto de entrenamiento, o variables climáticas rezagadas conocidas en la fecha de corte.
- Temperatura observada del mes objetivo no se admite como predictor de un pronóstico que supuestamente se emitió antes de ese mes. La muestra Open-Meteo actual no se usa para este modelo por su cobertura limitada.

**Pasos**

1. Formar panel mensual de estados y sector RES con identificadores, target MWh y estados de publicación.
2. Crear variables usando ventanas *shifted* para que no incluyan el target ni meses posteriores.
3. Congelar el plan temporal antes de ajustar: datos previos para entrenamiento, 2024 como validación y 2025 como prueba final para el primer modelo con demografía. Los resultados actuales 2018–2025 se conservan como experimento previo y no se mezclan si no comparten exactamente las mismas observaciones.
4. Ajustar hiperparámetros solo con entrenamiento/validación; no consultar el test para elegir modelo ni umbral.
5. Reportar MAE, RMSE y sMAPE globales y por estado, además del resultado de cada baseline. Incluir mediana estatal y distribución para que los estados de mayor consumo no oculten errores de otros.
6. Repetir la corrida con la misma versión de fuentes, semilla y configuración; guardar métricas, predicciones, fecha de corte, versión del código y hashes.
7. Si el modelo ML no supera la baseline, mostrar el resultado como evaluación válida pero no afirmar que predice mejor.
8. Desplegar en dashboard las predicciones del holdout primero. Una proyección futura se añade solo si el modelo se reajusta con todo el historial permitido, se dispone de variables futuras válidas y se etiqueta su fecha/horizonte.

**Criterios de salida**

- Un comando reproduce entrenamiento, evaluación, predicciones, métricas y manifiesto.
- El test final permanece fuera del ajuste y se documenta ausencia de fuga.
- Dashboard distingue observado, backtest e inferencia futura.
- El modelo se describe como ML; no se atribuyen capacidades de IA generativa ni decisiones automatizadas.

### Bloque 5 — Detección de anomalías en consumo

**Alcance en dos escalas**

- Conservar el detector EIA mensual como señal estadística de cambios interanuales por estado y estación.
- Añadir detección de intervalos inusuales en perfiles ResStock modelados, para estudiar cambios respecto al patrón temporal de cada perfil. No afirmar que sean anomalías reales de hogares.

**Pasos para perfiles ResStock**

1. Usar Parquet de 50 perfiles solo en el entorno local controlado mientras no se apruebe su publicación; validar roster y 1,752,000 intervalos de 15 minutos.
2. Convertir timestamps a zona local con el contrato temporal ya implementado y crear atributos de día laboral/fin de semana y cuarto de hora local.
3. Crear baseline robusta por perfil y franja temporal (mediana y MAD o cuantiles) con una partición temporal de referencia; excluir datos de evaluación del cálculo de baseline.
4. Marcar candidatos de aumento, disminución o hueco. Guardar perfil, estado, tipo de vivienda, timestamp, consumo, esperado, residuo/score y regla aplicada.
5. Evaluar el detector con alteraciones sintéticas (picos, caídas y periodos faltantes) sobre una copia; registrar seed, magnitudes, recall, precisión y falsos positivos.
6. Revisar manualmente candidatos reales sin llamarlos fallas, fraude o eventos confirmados si no existe etiqueta/contraste externo.
7. Mantener separados los candidatos sintéticos de los candidatos observados en las vistas y tablas Gold.

**Criterios de salida**

- Datos fuente originales intactos; inyecciones sintéticas versionadas separadamente.
- Cada alerta explica periodo, línea base, diferencia y umbral.
- Métricas sintéticas se muestran con advertencia de que no miden desempeño ante eventos reales.

### Bloque 6 — Organización de datos y manifiestos en S3

**Estructura objetivo sugerida**

```text
<bucket-privado>/
├── raw/
│   ├── eia/eia861m/<vintage>/
│   ├── census/state-population/<vintage>/
│   ├── noaa/nclimdiv/<vintage>/
│   ├── open-meteo/<query-id>/
│   └── resstock/<release>/             # solo con licencia/decisión de retención revisada
├── silver/
│   ├── demographics/state-year/v1/
│   ├── climate/state-month/v1/
│   └── energy/state-month/v1/
├── gold/
│   ├── v1/pilot/                        # artefactos actuales: no sobrescribir
│   └── v2/
│       ├── state-energy-demographics/
│       ├── state-climate-energy/
│       ├── forecasts/
│       └── anomaly-candidates/
└── site/
    ├── releases/v1/                     # HTML actual: publicación rota, preservar
    └── data/v2/                         # exportaciones JSON aprobadas + manifest
```

Los prefijos son claves de objetos, no carpetas físicas. El bucket observado actualmente contiene `gold/` y `site/`; la estructura superior es una **propuesta**, no configuración ya creada.

**Pasos**

1. Crear inventario local por fuente antes de subir: nombre, vintage, fecha de adquisición, cobertura, unidad, esquema, bytes, hash, licencia/atribución y autorización de publicación.
2. Mantener originales en `raw/` solo si se permite conservarlos; si no, guardar derivados autorizados y manifiesto con instrucciones/enlace de obtención.
3. Versionar salidas por contrato. Nunca sobrescribir `gold/v1/pilot/` ni objetos usados por una URL previa.
4. Subir a un prefijo de staging de versión nueva; validar conteos, esquema, hashes y lectura; publicar `manifest.json` al final.
5. Conservar S3 Block Public Access. No publicar `raw/`, `silver/`, Parquet Gold ni datos que no hayan sido revisados.
6. Actualizar el HTML autónomo solo después de validar su salida local. Generar un objeto con nombre/version nuevo; probar su URL prefirmada en navegador antes de compartir.
7. Mantener `site/` como frontend y datos JSON aprobados. CloudFront/OAC es el objetivo para URL estable, no una capacidad existente.
8. Registrar en la documentación qué operación se ejecutó en AWS y cuál se ejecutó localmente.

**Criterios de salida**

- Manifiesto permite verificar cada artefacto por filas, bytes, hash, versión y fuente.
- El bucket permanece privado y no contiene secretos.
- HTML de S3 presenta las mismas tablas y vistas que la build local, sin consola/network errors críticos.
- No se declara CloudFront, EMR o Kinesis hasta que la consola muestre un recurso operativo y exista evidencia de flujo.

### Bloque 7 — Conectar resultados al dashboard

**Pasos**

1. Diseñar el nuevo contrato Gold v2 antes de programar adaptadores.
2. Añadir a Resumen: población del estado, densidad, ventas residenciales totales y per cápita con año visible.
3. Añadir a Patrones/Comparación: gráfico de dispersión y tabla comparativa por estado, filtros por año y etiquetas de fuentes.
4. Añadir a Clima: indicador climático estatal mensual de NOAA; mantener un panel distinto para la muestra por punto de Open-Meteo y el pronóstico meteorológico actual.
5. Añadir a Estimaciones: observado vs Seasonal Naive vs regresión vs Random Forest, con filtro estado/año y métricas del holdout.
6. Añadir a Anomalías: candidatos EIA mensual y candidatos de perfil en paneles separados; incluir controles para diferenciar observado/sintético.
7. Añadir a Flujo/Calidad: capas S3, cobertura de datos, último manifiesto, hash válido/no válido y estado real de AWS.
8. Asegurar que meses o estados sin datos aparezcan como “sin dato”, no como cero.
9. Mantener interfaz responsiva, navegación accesible y explicaciones legibles; visualizaciones no deben ocultar unidad, periodo o población.
10. Empaquetar y servir localmente. Solo después de inspección visual publicar un HTML nuevo en S3 y probar la URL en navegador.

**Criterios de salida**

- Todas las cifras visibles corresponden al manifiesto cargado y muestran unidad/periodo.
- Los filtros no implican una cobertura común que las fuentes no tienen.
- Tablero local funciona; versión de S3 se verifica individualmente antes de difusión.

### Bloque 8 — Cloud, flujo integral y limitaciones de Learner Lab

1. Mantener desarrollo y validación en Spark local mientras EMR Serverless esté denegado.
2. Ejecutar pruebas de permisos en modo de solo lectura antes de intentar crear servicios; registrar acción denegada y servicio exacto.
3. Usar S3 para almacenamiento versionado y publicación privada de la build validada.
4. Si el rol del Learner Lab autoriza EMR, procesar primero una muestra pequeña; comparar filas, hashes, tiempo y costo con la salida local; detener el job y registrar limpieza.
5. Si se autoriza Kinesis, crear un replay corto y acotado identificado como simulación, consumirlo y detener productor/stream/job según permisos. No llamarlo transmisión de medidores en vivo.
6. Si CloudFront está permitido, usar S3 privado con OAC y servir únicamente `site/` y JSON aprobados. Verificar URL HTTPS, acceso directo denegado y estado de caché.
7. Si los servicios no están permitidos, registrar formalmente la limitación; entregar S3 como almacenamiento y demostrar Spark/replay en local. No sustituir componentes por servicios nuevos sin actualizar arquitectura y costo.
8. Revisar la región real de la consola (`us-east-1`) y reemplazar referencias antiguas `mx-central-1` en los documentos que describan despliegue efectivo.

**Criterio de salida:** cada componente se clasifica como `configurado`, `ejecutado y verificado`, `intentado y denegado`, o `no implementado`; el diagrama final refleja el estado observado, no el deseado.

### Bloque 9 — Evaluación, riesgos, costos y entrega académica

1. Registrar cantidad de filas/bytes por fuente y capa, tiempos de procesamiento local/cloud y controles de calidad.
2. Registrar costos reales de AWS visibles en la cuenta por periodo/servicio; el crédito del Learner Lab no es un presupuesto mensual ni tope duro.
3. Documentar riesgos: perfiles modelados no representativos, EIA agregado, datos preliminares, faltantes de ciudad, muestra climática, fuga temporal, licencias y permisos AWS.
4. Preparar código, base de datos/artefactos permitidos y documentación para Google Classroom. No subir datos con redistribución no confirmada ni secretos.
5. Congelar versiones de fuentes, manifest, scripts y resultados; reproducir desde instrucciones limpias.
6. Actualizar la explicación al profesor para separar evidencia local, evidencia S3 y servicios cloud realmente ejecutados.

## 6. Métricas y reglas de aceptación del proyecto

| Área | Métrica/validación | Regla de aceptación |
|---|---|---|
| Cobertura demográfica | Estados/jurisdicciones y años presentes; claves únicas; campos faltantes | Cobertura y faltantes explicados; no se imputan silenciosamente. |
| Comparación energía-población | MWh/año, población, personas/milla², kWh/persona/año | Recalcular desde fuentes; misma clave geográfica y año; conversiones documentadas. |
| Clima | Estados, meses, unidad, estado de publicación | Cobertura compatible declarada; históricos y forecast separados. |
| ML | MAE, RMSE, sMAPE, resultados por estado, baseline y modelo | Holdout temporal intacto; resultados reproducibles; se reporta si el ML pierde. |
| Anomalías | candidatos, recall/precisión/FPR en inyecciones sintéticas, candidatos observados | Sintético y observado separados; no se afirman eventos reales sin confirmación. |
| Dashboard | carga de manifest, tablas, filtros y unidades | Sin errores críticos; valores trazables a Gold; ausencia de datos no se dibuja como cero. |
| Escala | filas/bytes realmente procesados | Cifra ligada a archivo, comando, versión y fecha; candidatos no cuentan como procesados. |
| AWS | archivos, región, prefijos, servicio, estado, costo observado | Evidencia de consola/manifest; no se declara servicio por estar listado en “visitados recientemente”. |

No se fija de antemano precisión mínima o disponibilidad productiva sin requerimiento explícito y medición. El criterio es presentar evaluación honesta frente a baseline, limitaciones y resultados reales.

## 7. Relación con las secciones de Big Data Project Proposal

| Sección de la plantilla | Cómo se satisface con este plan |
|---|---|
| 1. Resumen ejecutivo | Explicar plataforma, fuentes, problema, tecnologías y estado real cloud. |
| 2. Objetivos SMART | Medir comparaciones estatales, registros, controles, predicción y dashboard con alcance definido. |
| 3. Justificación | Mostrar por qué población y normalización per cápita contextualizan consumo; beneficios académicos sin ROI inventado. |
| 4. Alcance | Definir estado-mes-sector residencial como foco; ciudades y consumo individual quedan condicionados. |
| 5. Requisitos | Describir filtros, tablas, anomalías, predicción, tiempos, escalabilidad y seguridad que se implementarán/medirán. |
| 6. Arquitectura | Actualizar diagrama según S3 actual y EMR/Kinesis/CloudFront realmente disponibles. |
| 7. Fuentes y metodología | Integrar Census, EIA y NOAA con grano, claves, licencias, validación, particiones y modelo. |
| 8. Hitos | Seguir los bloques 0–9 y registrar criterios de salida sin declarar fechas ficticias. |
| 9. Recursos y equipo | Mantener roles del equipo y registrar herramientas efectivamente usadas. |
| 10. Riesgos | Mitigar cobertura incompleta, diferencias entre fuentes, sesgos, fugas, licencias y límites de Learner Lab. |
| 11. Métricas | Aplicar métricas y reglas de aceptación de la sección 6. |
| 12. Conclusión | Resumir beneficio demostrado, evidencia, costo observado y limitaciones pendientes. |

## 8. Registro de avance por bloque

Usar esta plantilla al cerrar cada bloque:

```text
Bloque:
Estado: PENDIENTE | EN CURSO | BLOQUEADO | COMPLETADO
Fuentes/versions:
Archivos o recursos producidos:
Filas/bytes/periodo/geografía:
Comando y entorno usados:
Controles de calidad y resultados:
Validación del dashboard/AWS:
Limitaciones conocidas:
Evidencia verificable:
Siguiente dependencia:
```

Un bloque solo cambia a `COMPLETADO` cuando sus criterios de salida están verificados y la evidencia está anotada. `BLOQUEADO` requiere indicar el error o permiso denegado y una alternativa viable. Los bloques 1 y 2 pueden desarrollarse en paralelo; el bloque 3 depende de ambos. Los bloques 4 y 5 pueden avanzar después de estabilizar sus tablas de entrada; la integración del bloque 7 depende de resultados y contratos aceptados. La publicación S3 del bloque 6 debe hacerse después de validar la build del bloque 7.

## 9. Fuentes oficiales de referencia

- Census Bureau, población estatal 2020–2025: <https://www.census.gov/data/datasets/time-series/demo/popest/2020s-state-total.html>
- Census Bureau, densidad poblacional: <https://www.census.gov/data/tables/time-series/dec/population-density.html>
- Census Bureau, población de ciudades: <https://www.census.gov/data/tables/time-series/demo/popest/2020s-total-cities-and-towns.html>
- EIA Form 861M, ventas por estado y sector: <https://www.eia.gov/electricity/data/eia861m/index.php>
- NOAA/NCEI nClimDiv, metadatos: <https://www.ncei.noaa.gov/metadata/geoportal/rest/metadata/item/gov.noaa.ncdc%3AC00005/html>
- NOAA nClimDiv, explicación y descargas: <https://www.drought.gov/data-maps-tools/climate-division-datasets-nclimdiv>
- Open-Meteo Historical Weather API: <https://open-meteo.com/en/docs/historical-weather-api>
- Open-Meteo Forecast API: <https://open-meteo.com/en/docs>

