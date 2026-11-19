# División del desarrollo en cuatro bloques de trabajo

**Base:** [`plan-operativo-desarrollo-v2.md`](plan-operativo-desarrollo-v2.md), propuesta V2 aprobada y observaciones del profesor.  
**Propósito:** permitir que cada integrante entregue un bloque delimitado, reproducible y revisable mediante una rama y un Pull Request (PR). Omar conserva la integración, coordinación y nube.  
**Estado:** plan de asignación; todavía no implica que los bloques estén iniciados o terminados.

## 1. Reglas comunes de trabajo

1. Una vez que este plan esté integrado en `main`, cada integrante actualizará su copia local, creará una rama propia desde ese `main` y limitará sus cambios a las rutas asignadas abajo.
2. Nadie trabaja sobre la misma rama ni hace push directamente a `main`. Cada bloque se entrega por PR hacia `main`; Omar coordina el orden de revisión, resuelve integraciones y realiza los merges.
3. Los contratos de datos de este documento son las interfaces compartidas. Se pueden implementar los bloques en paralelo sin que los responsables editen el mismo código o manifiesto.
4. Los datos originales descargados se guardan localmente en carpetas ignoradas por Git. Solo se versionan código, documentación y derivados pequeños cuya procedencia, licencia y utilidad para reproducir estén justificadas.
5. No se suben credenciales, archivos de sesión AWS, URLs prefirmadas, capturas con identificadores ni archivos fuente cuya redistribución no esté autorizada.
6. Cada PR debe explicar: alcance, archivos cambiados, fuentes y fechas, comando para reproducir, conteos/hash, validación realizada, limitaciones y evidencia visual cuando afecte al dashboard.
7. Un bloque se considera listo para merge cuando el PR corresponde exactamente a su alcance, sus criterios de aceptación están demostrados y Omar puede integrarlo sin resolver cambios de responsabilidad ajena.

## 2. Contratos compartidos para evitar conflictos

Los tres bloques de datos/análisis producirán resultados independientes y no modificarán el manifest principal del dashboard. Omar será el único responsable de integrar las nuevas tablas al dashboard y publicarlas en S3.

### Tabla demográfica y energética anual — Brian

Archivo de salida propuesto: `datos/demografia_estatal/energy_demography_state_year_v1.csv`

```text
state_fips,state_code,year,population_estimate,land_area_sq_mi_2020,
population_density_per_sq_mi,residential_sales_mwh,residential_kwh_per_capita,
eia_data_status,census_vintage,source_version
```

- Geografía: 50 estados más DC como jurisdicción separada.
- Periodo integrado: 2020–2025, una sola Census Vintage y ventas EIA `Final` completas.
- `state_fips` debe ser texto con ceros iniciales preservados; `state_code`, mayúsculas.
- `residential_kwh_per_capita = residential_sales_mwh * 1000 / population_estimate`.
- La densidad anual derivada se calcula como población anual / superficie terrestre 2020 y se etiqueta como estimación calculada.

### Tabla climática estatal mensual — Christian

Archivo de salida propuesto: `datos/clima_estatal/noaa_state_climate_monthly_v1.csv`

```text
state_fips,state_code,period,temperature_mean_c,precipitation_mm,hdd,cdd,
climate_data_status,climate_source,climate_vintage,source_version
```

- Grano: estado × mes; `period` tiene formato `YYYY-MM`.
- Variables, unidades, cobertura estatal y estados preliminares/finales se documentan conforme al recurso NOAA/NCEI seleccionado.
- No unir ni renombrar la muestra de dos puntos Open-Meteo como si fuera clima estatal.

### Interfaces para el bloque de Diego

- EIA existente: `datos/eia_residencial_mensual.csv`, columnas `periodo,estado,sector,estado_dato,ventas_mwh`.
- Demografía de Brian: tabla anual definida arriba.
- Clima de Christian: tabla mensual definida arriba.
- Para una predicción histórica, ninguna variable del periodo objetivo puede derivarse de valores observados después de la fecha de emisión. Las normales climáticas de cada estado/mes se calculan exclusivamente con el periodo de entrenamiento; no se usa el clima observado del test como si hubiera estado disponible por adelantado.

## 3. Bloque 1 — Brian García Mares: demografía y comparación estatal de energía

**Responsabilidad:** datos demográficos, población y densidad estatal; comparación anual con ventas residenciales EIA.

**Rama sugerida:** `feat/brian-demografia-estatal`  
**PR destino:** `main`  
**Secciones de la propuesta:** 2 (objetivos), 4 (alcance), 5 (requisitos), 7 (fuentes/metodología), 11 (métricas).

### Archivos bajo su responsabilidad

- `scripts/preparar_demografia_estado.py`
- `datos/demografia_estatal/energy_demography_state_year_v1.csv`
- `datos/demografia_estatal/manifest.json` o manifiesto equivalente con metadatos y hash del derivado
- `docs/demografia-estatal.md`

No modificar `tablero/`, `tablero/data/v1/manifest.json`, `README.md`, los contratos compartidos ni los archivos AWS. Datos fuente descargados se guardan fuera del repositorio o en una ruta ignorada.

### Pasos

1. Obtener de la fuente oficial Census Bureau la estimación anual de población 2020–2025 y el dato de superficie terrestre del Censo 2020; registrar vintage, URL, fecha de consulta y bytes/hash.
2. Leer la serie EIA versionada del repositorio; filtrar sector `RES` y ventas finales. Agregar los 12 meses de cada estado por año 2020–2025; excluir o marcar explícitamente años incompletos.
3. Normalizar y validar FIPS y abreviaturas para los 50 estados y DC. No incluir filas nacionales o regionales como si fueran estados.
4. Unir población y ventas por jurisdicción/año y calcular densidad anual estimada y ventas residenciales per cápita según el contrato de la sección 2.
5. Generar un artefacto CSV determinista y manifiesto con filas, bytes, SHA-256, cobertura, unidades, fuentes, fecha y vintage.
6. Documentar el ranking de población total por separado del ranking de densidad. Indicar año de referencia para ambos; no describir una correlación como causal.
7. Reproducir el CSV desde un comando del script en una carpeta temporal vacía y comparar sus conteos/hash con el manifiesto.

### Criterios de aceptación

- La salida cubre estados/años disponibles sin duplicados y sus faltantes se explican.
- Comparación usa EIA `RES`, ventas anuales completas y Census Vintage única.
- Conversión MWh→kWh y denominador poblacional están documentados.
- California y Nueva Jersey no se confunden: el primero es ejemplo de mayor población; el segundo, de mayor densidad de acuerdo con sus respectivos años/fuentes.
- El PR incluye comando de reproducción, conteos, hash y limitaciones.

### Dependencias

No depende de los bloques de Christian o Diego. Usa EIA ya versionada. Su salida es una entrada que Omar integrará después.

## 4. Bloque 2 — Christian Raul Páramo Bautista: clima mensual estatal

**Responsabilidad:** obtener, normalizar y validar variables climáticas mensuales comparables por estado, conservando Open-Meteo puntual separado.

**Rama sugerida:** `feat/christian-clima-estatal`  
**PR destino:** `main`  
**Secciones de la propuesta:** 4 (alcance), 5 (requisitos), 6 (arquitectura/datos), 7 (metodología), 10 (riesgos).

### Archivos bajo su responsabilidad

- `scripts/preparar_clima_estatal.py`
- `datos/clima_estatal/noaa_state_climate_monthly_v1.csv`
- `datos/clima_estatal/manifest.json` o manifiesto equivalente
- `docs/clima-estatal-noaa.md`

No modificar `tablero/`, el manifest Gold principal, los scripts de Brian/Diego, `README.md` ni documentos de arquitectura AWS. No subir los archivos raw descargados.

### Pasos

1. Usar NOAA/NCEI nClimDiv como candidato para temperatura media, precipitación y grados-día de calefacción/enfriamiento (HDD/CDD). Confirmar nombres, unidades, geografía, cobertura de Alaska/Hawái/DC y reglas de datos preliminares contra la documentación del dataset.
2. Descargar el subconjunto estatal/mensual necesario para cruzar con EIA, preferentemente 2020–2025; conservar archivo original solo localmente.
3. Transformar a una fila por estado y `period=YYYY-MM`; normalizar claves y unidades. Si el recurso no ofrece un valor estatal para alguna jurisdicción, registrarlo como faltante y no imputarlo silenciosamente.
4. Producir el CSV según el contrato compartido, con manifiesto de fuente, versión/vintage, fechas, unidades, filas, bytes y SHA-256.
5. Verificar unicidad, continuidad temporal esperada, rangos plausibles, valores ausentes y estados del dato.
6. Contrastar la cobertura espacial/temporal con EIA sin editar el archivo de EIA. Mantener el resultado climático como una tabla separada.
7. Documentar que la muestra Open-Meteo actual cubre solo dos puntos por siete días de 2018 y no representa el clima estatal.
8. Definir para una etapa posterior el uso de Open-Meteo Forecast como contexto de corto plazo. No crear una variable nacional de pronóstico basada en una ciudad capital sin describirla como proxy local.

### Criterios de aceptación

- Contrato exacto de la sección 2 y granularidad estado-mes.
- Unidades, periodo, fuente, vintage y cobertura descritos.
- Faltantes geográficos/temporales explícitos; ningún join artificial con ResStock.
- Script reproducible y manifiesto con conteos/hash.
- El PR no presenta clima observado como pronóstico ni la muestra puntual como dato estatal.

### Dependencias

No depende de Brian o Diego para descargar/normalizar su tabla. Debe conservar `state_fips`, `state_code` y `period` conforme al contrato para que Omar y Diego puedan integrarla.

## 5. Bloque 3 — Diego Emilio Ortiz Vilchez: modelo ML y anomalías

**Responsabilidad:** añadir un modelo de aprendizaje automático para estimar ventas residenciales mensuales por estado y completar el análisis de anomalías en perfiles ResStock. No construir vistas ni editar el frontend; Omar integrará sus salidas.

**Rama sugerida:** `feat/diego-ml-anomalias`  
**PR destino:** `main`  
**Secciones de la propuesta:** 2 (objetivos), 5 (análisis), 7 (metodología/ML), 10 (riesgos), 11 (métricas).

### Archivos bajo su responsabilidad

- `scripts/modelo_ml_consumo_estatal.py`
- `scripts/detectar_anomalias_resstock.py`
- `datos/analitica_v2/` con predicciones y resúmenes pequeños reproducibles
- `docs/modelo-ml-y-anomalias.md`

No modificar `tablero/`, `tablero/data/v1/manifest.json`, los scripts de demografía/clima, `README.md` ni los documentos de AWS. No añadir ni versionar datos fuente descargados.

### Parte A: predicción estatal mensual

1. Usar ventas EIA `RES` por estado y mes como variable objetivo; conservar separado el significado de ventas agregadas y consumo residencial modelado.
2. Comparar Seasonal Naive y regresión log-lineal existentes con un `RandomForestRegressor` global. Si se modifica un método existente, mantener resultados anteriores identificables.
3. Consumir los contratos de Brian y Christian por rutas configurables. Mientras las tablas compañeras aún no estén integradas, implementar/validar los lectores contra fixtures temporales con el mismo esquema; no incluir cifras sintéticas como resultados reales.
4. Usar estado, calendario, lags de consumo, población conocida al corte y densidad. Incorporar clima solo mediante normales por estado/mes calculadas desde entrenamiento o variables conocidas en el origen de pronóstico. No usar clima observado del mes objetivo para afirmar un pronóstico anticipado.
5. Definir evaluación cronológica, no aleatoria: entrenamiento 2020–2023, validación 2024 y prueba final 2025 para el modelo con variables demográficas. Cualquier cambio de partición se documenta antes de mirar métricas del test.
6. Reportar MAE, RMSE y sMAPE por estado y globalmente; comparar en las mismas filas contra las baselines. No declarar al ML mejor si no las supera.
7. Escribir CSV de predicción con estado, periodo, observado, baseline, modelo y partición; JSON de resumen con cobertura, features, versión/hash de entradas y métricas.

### Parte B: anomalías de consumo ResStock

1. Usar como entrada reproducible inicial el Parquet de los 10 perfiles versionados. El lote de 50 puede usarse solo si el operador lo obtiene localmente y aporta su manifiesto; no es requisito para que el PR sea reproducible.
2. Crear patrón esperado por perfil y periodo local (por ejemplo, mediana/MAD por día laboral/fin de semana y cuarto de hora); documentar explícitamente las decisiones temporales.
3. Marcar candidatos de picos, caídas y periodos faltantes con timestamp, perfil, valor observado, valor esperado, score/umbral y tipo de señal.
4. Evaluar detección inyectando anomalías sintéticas en una copia temporal, conservando datos originales. Registrar semilla, número y magnitud de inyecciones, recall, precisión y falsos positivos.
5. Separar resultados sintéticos y candidatos observados; no etiquetar un candidato como falla o anomalía real confirmada.

### Criterios de aceptación

- El ML tiene objetivo, grano, partición temporal y baselines claros; todos los features están disponibles al origen de predicción.
- Resultados son deterministas o describen semilla/variación; scripts y comandos reproducen salidas.
- El detector distingue candidatos reales de pruebas sintéticas y conserva fuente intacta.
- El PR puede revisarse sin abrir dashboard ni AWS; el bloque entrega contratos consumibles por Omar.
- Si resultados integrados reales requieren que los PRs de Brian/Christian se fusionen primero, el PR de Diego separa claramente: validación de interfaz realizada, evaluación real pendiente de integración. Omar no marcará la etapa de ML integrada como completa hasta ejecutar con ambas tablas reales.

### Dependencias

La implementación del código puede comenzar en paralelo usando contratos estables. La evaluación final con variables demográficas y climáticas reales depende de los artefactos de Brian y Christian ya integrados en `main`.

## 6. Bloque 4 — Omar Gadiel Bolaños García: nube, integración y publicación

**Responsabilidad:** orquestar los tres PRs, integrar sus tablas en Gold/dashboard, reparar la publicación S3 y avanzar la nube según los permisos reales de AWS Academy Learner Lab.

**Rama sugerida:** `feat/omar-aws-integracion-dashboard`  
**PR destino:** `main`  
**Secciones de la propuesta:** 5 (visualización), 6 (arquitectura), 7 (flujo), 8 (hitos), 9 (coordinación), 10 (seguridad/riesgos), 11 (métricas).

### Archivos bajo su responsabilidad

- `tablero/` y `tablero/data/v2/`
- `scripts/empaquetar_tablero_autonomo.py` y validadores de integración/publicación
- `docs/arquitectura-aws-por-etapas.md`
- `docs/despliegue-temporal-s3.md`
- `docs/seguimiento.md` y README de entrega cuando los bloques estén integrados

Omar será el único que modifique el manifest principal del dashboard, las vistas JS, la estructura `tablero/data/v2/`, los documentos de estado AWS y la publicación S3 durante esta etapa.

### Secuencia del bloque

**A. Nube y artefacto web existente, trabajo paralelo a los PRs**

1. Registrar estado real del bucket privado en `us-east-1`, prefijos, objetos, región, acceso y límites de Learner Lab; actualizar la documentación que aún diga `mx-central-1` o ausencia de recursos.
2. Reproducir localmente el empaquetado del HTML autónomo. Diagnosticar por qué el objeto actual en S3 abre con gráficas vacías; validar manifiesto, tablas embebidas, solicitudes de red, consola del navegador y carga de datos.
3. Generar una build con nombre/version nuevo; no sobrescribir la ya cargada. Inspeccionar primero en servidor local que tenga las diez tablas esperadas y todas las vistas.
4. Cargar únicamente la build revisada en un prefijo de release privado y crear una URL prefirmada nueva. Abrirla en navegador separado y comprobar que no esté vacía antes de compartirla.
5. Documentar que una URL prefirmada es temporal y no una URL pública permanente.

**B. Integración tras revisión/merge de Brian y Christian**

6. Revisar PRs por procedencia, esquema, unidades, cobertura y hash; solicitar correcciones antes de hacer merge si no cumplen contratos.
7. Integrar outputs en `tablero/data/v2/`, crear manifest v2 con filas/bytes/hashes y mantener intacto v1.
8. Integrar en el dashboard comparación demográfica, clima histórico y predicción/anomalías en vistas existentes; no añadir datos climáticos locales al nivel estatal sin rotular geografía.
9. Ejecutar validación local del manifest, filtros, cifras, estados faltantes y vistas con outputs reales. Resolver errores visuales o de carga.

**C. Integración del bloque Diego y AWS**

10. Tras merge del PR de Diego y cuando se hayan integrado las tablas reales de Brian y Christian, ejecutar modelo/análisis en el entorno local limpio y reproducir las métricas.
11. Publicar artefactos Gold derivados autorizados a prefijos versionados de S3; separar `raw/`, `silver/`, `gold/v2/` y `site/data/v2/`. No subir raw por defecto.
12. Reintentar EMR Serverless solo tras inspeccionar permisos actuales y documentar acción concreta; si Learner Lab la niega, conservar procesamiento local y registrar denegación exacta.
13. Crear stream Kinesis solo cuando los permisos y la estimación de costo sean aceptables; limitar evento/lote, identificarlo como replay y definir terminación/limpieza antes de crear.
14. Intentar CloudFront/OAC solo si el rol lo permite. Mantener bucket privado; no habilitar acceso público como atajo. Si CloudFront está bloqueado, presentar la URL prefirmada como demo temporal.
15. En cada operación, guardar fecha, región, conteos, costo observado si está disponible, recurso creado/denegado y evidencia sin account ID ni secretos.

### Criterios de aceptación

- Los tres PRs de contribución se revisaron y el historial conserva autoría; ningún merge se hace sin revisión de datos/código.
- El dashboard local carga tablas demográficas, clima y analítica desde Gold v2 con manifest validado.
- La build de S3 abre sin vacíos y fue probada desde una URL nueva antes de compartirla.
- El bucket permanece privado y ningún raw/credencial se hace público.
- La documentación coincide con la consola: `us-east-1`, S3 presente, estado real de EMR/Kinesis/CloudFront y limitación de Learner Lab.
- Cada servicio cloud se etiqueta como ejecutado, denegado o pendiente; no se dibuja el flujo objetivo como si ya estuviera activo.

## 7. Orden de ejecución y dependencias

```text
Bloque 1 Brian (Census + EIA anual) ─────┐
                                         ├─> Bloque 3 Diego (ML con población/clima)
Bloque 2 Christian (NOAA mensual) ──────┘

Bloque 4 Omar: reparación S3/local en paralelo
Bloque 4 Omar: integración dashboard + Gold v2 después de revisar PRs 1–3
Bloque 4 Omar: EMR/Kinesis/CloudFront solo si permisos lo permiten
```

- Brian y Christian pueden desarrollar y abrir PRs en paralelo porque sus rutas y contratos son independientes.
- Diego puede implementar estructura/modelo/detector contra contratos y fixtures temporales; evaluación final con features reales ocurre después de que las tablas de Brian y Christian estén integradas.
- Omar puede corregir el HTML, alinear documentos AWS y preparar publicación mientras los otros avanzan. La integración de sus outputs al dashboard espera los PRs revisados.
- No se recomienda mergear PRs que cambien un contrato común sin actualizar este plan y coordinar el impacto con los demás bloques.

## 8. Flujo requerido de rama y Pull Request

Una vez que la asignación esté integrada en `main`, cada persona debe verificar primero que su rama sugerida no exista ya en el remoto. Después, desde un checkout limpio:

```bash
git fetch origin
git switch main
git pull --ff-only origin main
git switch -c <rama-asignada>
```

Antes de publicar:

```bash
git status --short
git diff --check
```

Agregar solo las rutas de su bloque, crear commits descriptivos, hacer push de su propia rama y abrir PR hacia `main`. No incluir `--force`, no mezclar ramas de otro integrante y no borrar artefactos ajenos. Si las políticas del repositorio requieren squash/rebase o una plantilla PR específica, seguirlas.

### Plantilla de descripción del PR

```text
Bloque/responsable:
Objetivo y alcance:
Fuentes, vintage y licencias/atribución:
Archivos de entrada y salida:
Cobertura (geografía, periodo, granularidad, unidades):
Comando reproducible:
Filas/bytes/SHA-256:
Controles y resultado:
Limitaciones/no verificado:
Servicios AWS usados (si aplica; nunca incluir secretos):
Capturas o evidencia:
Checklist de criterios del bloque:
```

## 9. Checklist de revisión de Omar antes de cada merge

- [ ] PR parte de `main` actualizado y toca solo el ámbito asignado.
- [ ] No incluye claves, credenciales, URLs prefirmadas, IDs de cuenta o datos crudos no autorizados.
- [ ] Fuente, vintage, fecha, esquema, unidades y uso están documentados.
- [ ] Filas, cobertura, hashes y controles se pueden reproducir.
- [ ] Datos Final/Preliminary, modelos/sintéticos y resultados reales están distinguidos.
- [ ] Métricas no usan información posterior al origen de predicción.
- [ ] El frontend no está modificado por integrantes de los bloques 1–3.
- [ ] La documentación no llama a recursos planeados “desplegados”.
- [ ] Un revisor distinto del autor inspeccionó el PR antes del merge.

## 10. Definición de terminado del conjunto de cuatro bloques

El trabajo se considera consolidado cuando:

1. Brian y Christian entregaron y se integraron sus tablas con procedencia, manifests y conteos verificados.
2. Diego reprodujo un modelo ML estatal comparado con baselines, además de candidatos de anomalía con evaluación sintética identificada.
3. Omar conectó los artefactos al dashboard en una versión Gold v2 sin reemplazar v1.
4. La versión local del dashboard funciona; la versión S3 está verificada, o su impedimento queda demostrado y descrito con precisión.
5. La consola y los documentos distinguen S3 activo, EMR/Kinesis/CloudFront operativos, denegados o pendientes.
6. Los cuatro PRs tienen revisión, autoría y criterios de aceptación documentados; entrega académica puede reproducirse sin depender de archivos temporales secretos o cuentas personales de agentes.

