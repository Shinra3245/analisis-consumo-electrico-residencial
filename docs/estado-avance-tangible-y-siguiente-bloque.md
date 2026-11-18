# Estado tangible del proyecto y siguiente bloque de implementación

**Fecha de la revisión:** 17 de noviembre de 2026 (las marcas de GitHub aparecen en UTC del 18 de noviembre).
**Tipo de documento:** revisión de solo lectura de Claude en un worktree aislado. No se ejecutó código del proyecto, pruebas, builds, descargas ni despliegues; no se modificó el workspace principal ni se comentaron o cambiaron PRs. Las cifras que se citan de scripts o reportes son **las que esos archivos declaran**, no resultados que esta revisión haya reproducido.

## 0. Cómo leer este documento

Cada artefacto lleva exactamente una etiqueta:

| Etiqueta | Significado verificado |
|---|---|
| **Integrado en main** | Está en `origin/main` = `3157233` (merge del PR #3). |
| **PR abierto** | Está en una rama con PR abierto hacia `main`. |
| **Rama remota** | Está en una rama de `origin` sin PR abierto. |
| **Solo local sin commit** | Existe en el workspace principal pero en ninguna rama local ni remota (comprobado con `git ls-tree` sobre las 10 ramas de `origin`: 0 coincidencias para `demo/`, `scripts/job_spark_piloto.py`, `docs/ejecucion-job-spark-local.md`, `docs/plan-ejecucion-integral-90.md`, `docs/division-tareas-integrantes-90.md` y `presentaciones/avance-demo-preliminar/`). |
| **No implementado** | No existe código ni salida; solo diseño o nada. |

Fuentes consultadas: `gh pr list/view` y `gh api .../branches` sobre `Shinra3245/analisis-consumo-electrico-residencial`; `git ls-tree`, `git show`, `git diff`, `git merge-tree` (sin escribir) sobre las referencias remotas ya presentes en el clon; lectura de archivos del workspace principal `/home/omarbolanos/Documentos/SEMESTRE 9/BIG DATA/PARCIAL3/Propuesta proyecto final`. Los SHA de `gh api` coinciden con las referencias `origin/*` del clon, así que no hizo falta `fetch`.

## 1. Estado del repositorio

### 1.1 `main`

`origin/main` = `3157233` «Merge pull request #3 … arquitectura-aws-por-etapas». Contenido relevante (`git ls-tree origin/main`):

- `datos/` (9 archivos: Parquet piloto de 10 perfiles, CSV EIA de 5,304 filas, clima de 336 filas, selección de 10,000 IDs candidatos, cobertura, verificación Colorado 2018, `manifiesto-integracion.json`, `README.md`).
- `scripts/` de preparación y análisis exploratorio: `preparar_datos.py`, `preparar_eia.py`, `analizar_muestra_inicial.py`, `generar_presentacion.py`.
- `docs/` (contrato de datos v1, decisión de publicación, arquitectura AWS por etapas, plan de desarrollo, etc.), `presentaciones/` y `README.md`.

**No hay en `main`:** carpeta `demo/`, ningún job Spark, carpeta `analitica/`, carpeta `jobs/`, carpeta `tests/`, ni código de tablero.

### 1.2 Pull requests (`gh pr list --state all`)

| PR | Estado | Rama | Detalle verificado |
|---|---|---|---|
| #1 | **Cerrado** sin merge (18-nov 03:58 UTC) | `datos/piloto-resstock-eia` (`c025acd`) | 17 archivos / +17,291. Sustituido por el PR #2. |
| #2 | **Integrado** (17-nov 23:43 UTC) | `avance/datos-y-gobernanza` | 20 archivos / +17,455: datos, contrato v1, decisión de publicación, guía del piloto. |
| #3 | **Integrado** (18-nov 03:58 UTC) | `docs/arquitectura-aws-por-etapas` | 3 archivos / +102 −1: arquitectura AWS por etapas, prefijos `gold/v1/` y política de caché. |
| #4 | **Abierto**, no borrador | `feature/christian-spark` (`531921f`) | 22 archivos / +2,451. `mergeable=MERGEABLE`, `mergeStateStatus=CLEAN`, **0 revisiones, 0 comentarios**; única comprobación: GitGuardian = SUCCESS. Base declarada `fc02f2f` (anterior a #3); `git merge-tree` contra `origin/main` actual no reporta conflictos. |

### 1.3 Ramas remotas sin PR

| Rama | SHA | Relación con `main` | Contenido |
|---|---|---|---|
| `preparacion/emilio-contrato-gold` | `cb034d4` | Contiene `main` (3157233 es ancestro); merge limpio | 2 archivos / +262: `docs/contrato-gold-propuesta.md` (119 líneas), `docs/especificacion-tablero.md` (143 líneas). Solo documentos. |
| `ramificacion-emi-analitica` | `e57ec38` | Base `fc02f2f`; merge limpio | 1 commit, 20 archivos / +21,159: `analitica/` (3 scripts, 11 CSV `gold_*`, `manifiesto-gold.json`, `requirements.txt`, `README.md`), `docs/metodo-anomalias.md`, `docs/metodo-pronostico.md`, `.gitattributes`. |
| `ramificacion-emi8086` | `4dd4004` | — | Versión anterior (2 archivos / +251) de los mismos dos documentos de Emilio; la rama `preparacion/…` la reemplaza en la práctica. |
| `pr/1`, `datos/piloto-resstock-eia` | `c025acd` | — | Restos del PR #1 cerrado. |
| `avance/datos-y-gobernanza`, `docs/arquitectura-aws-por-etapas` | `51e8960`, `e3ce5f6` | Ya integradas por #2 y #3 | Sin contenido propio pendiente. |

### 1.4 Workspace principal (solo lectura)

La rama activa es `avance/datos-y-gobernanza` (`51e8960`, dos commits por detrás de `origin/main`) con **cambios sin commit** y archivos sin seguimiento:

- Modificados sin commit: `README.md`, `docs/arquitectura-aws-por-etapas.md`, `docs/esquema-inicial-calidad-datos.md`, `docs/plan-de-desarrollo.md`, `presentaciones/Avance_Big_Data_17_noviembre_2026.pptx` (42,736 → 6,158,130 bytes) y `scripts/generar_presentacion.py` (reescrito). Estas ediciones se hicieron sobre una base anterior a #3 y **difieren de `origin/main`** (por ejemplo, `plan-de-desarrollo.md` local reemplaza el calendario por fechas por una «Secuencia de implementación por requisitos»; el `main` actual conserva el calendario). No se evaluó línea a línea; hay que reconciliarlas antes de cualquier commit.
- Sin seguimiento (`??`): `demo/`, `scripts/job_spark_piloto.py`, `scripts/requirements-spark.txt`, `docs/ejecucion-job-spark-local.md`, `docs/plan-ejecucion-integral-90.md`, `docs/division-tareas-integrantes-90.md`, `presentaciones/avance-demo-preliminar/`, `presentaciones/assets/`, los PDF/DOCX de la propuesta, `c.html` y `p.html`.
- `data/raw/` (3 archivos: `up00-co-single-family_detached.csv`, `eia_sales_revenue.xlsx`, `openmeteo_denver_2018.json`) está en `.gitignore`; es la entrada del PR #4.
- Existe además la rama local `local/presentacion-evidencia-visual` (`5658795`), no publicada; difiere de `main` en 44 archivos (rama antigua anterior al PR #2).

## 2. Inventario por área

### 2.1 Demo web

| Artefacto | Etiqueta | Evidencia | Qué demuestra | Qué NO demuestra |
|---|---|---|---|---|
| `demo/index.html` (232 líneas), `demo/app.js` (592), `demo/styles.css` (820), `demo/README.md` (31) | **Solo local sin commit** | Secciones en `index.html:53,75,80,198`; datos incrustados en `app.js:8` (`const MONTHLY_DATA`); sin `fetch` ni `localStorage` (`grep`); `demo/README.md:5-31` | Visor estático sin dependencias de la comparación mensual ResStock vs EIA de **Colorado 2018** (12 meses), con gráfico de líneas/barras/razón, filtro por temporada y tabla. Las cifras de enero (1,812,597.23 y 1,653,911.40 MWh; 109.59 %) coinciden con `datos/demo_colorado_2018_verificacion.csv` (`origin/main`). | No lee ningún Gold ni JSON: los 12 meses están **escritos a mano en `app.js`**. No cubre otros estados, EIA 2018–2026, pronóstico, anomalías, clima, calidad ni replay. No tiene pruebas. Ninguna rama ni PR lo contiene, de modo que hoy un tercero no puede reproducirlo desde GitHub. |
| `presentaciones/avance-demo-preliminar/` (PDF de 7 páginas, `generar.py`, guiones, capturas) | **Solo local sin commit** | `README.md` de esa carpeta; `evidencia/demo-grafica.png` | Material de exposición de la demo. | Es presentación, no software. |
| `presentaciones/Avance_Big_Data_17_noviembre_2026.pptx/.pdf` | **Integrado en main** (versión anterior; la nueva está sin commit) | `git ls-tree origin/main` | Borrador de la presentación de avance. | El README de `main` lo califica como «borrador anterior». |
| `docs/evidencia/comparacion-resstock-eia-co-2018.svg` | **Integrado en main** | `git ls-tree origin/main` | Evidencia gráfica estática de la misma comparación. | — |

### 2.2 Datos Silver / Gold

| Artefacto | Etiqueta | Evidencia | Qué demuestra | Qué NO demuestra |
|---|---|---|---|---|
| Datos de entrada versionados `datos/*` | **Integrado en main** (PR #2) | `datos/README.md`, `datos/manifiesto-integracion.json`; `docs/decision-publicacion-datos.md:45-52` | 10 perfiles ResStock (350,400 filas), 5,304 filas EIA (51 jurisdicciones, 2018-01…2026-08; 4,896 Final y 408 Preliminary), 336 horas de clima en 2 puntos, selección candidata de 10,000 IDs; hashes y licencias documentados. EIA reproducido byte a byte desde el XLSX oficial (`docs/contrato-datos-v1.md:59`). | Los 10,000 perfiles **no** están descargados (`docs/arquitectura-aws-por-etapas.md:94`: «candidatos, no una descarga»). Los 10 perfiles no son representativos; el peso es idéntico (253.9) según `docs/especificacion-tablero.md` (rama de Emilio). Quedan pendientes el chequeo de material de terceros en el XLSX EIA y los crudos ResStock originales (`decision-publicacion-datos.md:47-48`). |
| `docs/contrato-datos-v1.md` (98 líneas) | **Integrado en main** | Tablas `silver.resstock_profile_interval`, `silver.eia_residential_sales_monthly`, `silver.climate_hourly_point` | Contrato **propuesto** de Silver en inglés `snake_case`, con trazabilidad y controles. | Su línea 3 dice que es propuesta «lista para revisión» y que no implica ingestión implementada. Las decisiones de la sección 6 (líneas 92-98) siguen abiertas. |
| Silver/Gold del job local | **Solo local sin commit** | `scripts/job_spark_piloto.py:651` (`transform_silver_dataframes`) y `:744` (`transform_gold_dataframes`) | Diseño completo: 3 tablas Silver, 2 Gold, nombres canónicos del contrato, resta de 15 min al fin de intervalo (`:764`) para obtener 12 meses de 2018. | **Nunca se ha ejecutado**: `docs/ejecucion-job-spark-local.md:271-284` deja sin marcar los 6 puntos de «Checklist de Validación Runtime». Solo hay revisión estática (`:263-269`). No hay salidas de ejemplo. |
| Bronze/Silver/Gold de PR #4 | **PR abierto** | `jobs/batch/crear_{bronze,silver,gold}_{resstock,eia}.py`; `docs/reporte_calidad_rendimiento_spark.md` | Pipeline por capas sobre el agregado ResStock de Colorado 2018 (35,040 intervalos) y EIA Colorado 2018 (12 meses); declara 0 rechazados, 12 meses por fuente, 16,809,653.30 MWh vs 19,286,952.00 MWh (87.16 %). Declara ejecución en Windows con Spark 4.1.1 (reporte del 2026-11-17T19:52:38-06:00). | Entrada = `data/raw/…` no versionado (`crear_bronze_resstock.py:13`, `crear_bronze_eia.py:19`), no los datos de `datos/`. Solo Colorado 2018. «Normalización explícita de marcas temporales de ResStock a UTC todavía está pendiente» (`docs/guia-ejecucion-spark.md:157`). Sin ejecución en AWS. No produce Gold de patrones, pronóstico ni anomalías. |
| Gold analítico (11 CSV) | **Rama remota** (`ramificacion-emi-analitica`) | `analitica/salidas/*.csv`, `manifiesto-gold.json` (11 archivos, `warnings: []`) | Salidas deterministas con hashes de entrada (ver 2.3). | CSV generados con pandas, **no** Parquet de Spark. El propio `contrato-gold-propuesta.md:4` (rama de Emilio) dice que no son una salida verificada del job de Christian. |
| Tablas Gold de estado de pipeline, replay y calidad (Q3/Q4) | **No implementado** | `especificacion-tablero.md` (rama de Emilio): Q3 y Q4 «Pendiente»; `contrato-gold-propuesta.md` §3: «No existe» | — | No existe `quality_status`/`replay_id` en ningún artefacto de datos. |

### 2.3 Análisis, pronóstico y anomalías

Todo vive en `ramificacion-emi-analitica` (**Rama remota**, sin PR). Declarado por la propia rama y **no reproducido aquí**:

| Artefacto | Evidencia | Qué demuestra | Qué NO demuestra |
|---|---|---|---|
| Pronóstico EIA: `analitica/pronostico_eia.py` (229 líneas), `docs/metodo-pronostico.md` | `analitica/README.md` («sMAPE suma 51 en backtest: 5.63 / 3.67 / 3.47 % (naive / media estacional / log-lineal)»); `metodo-pronostico.md`: ajuste 2018-2023, backtest 2024-2025, comprobación preliminar ene-ago 2026, escenario sep 2026–dic 2027 | Línea base estacional y un modelo log-lineal con partición cronológica y métricas MAE/RMSE/sMAPE por estado y para la suma de 51 jurisdicciones. | Una sola partición temporal; sin clima ni variables exógenas; sin intervalos de predicción; la proyección 2026-09…2027-12 es un escenario sin validación. Serie EIA agregada, no consumo por hogar. |
| Anomalías: `analitica/anomalias_resstock.py` (415 líneas), `docs/metodo-anomalias.md` | Evaluación CO declarada: caída F1 0.664, aumento F1 0.154 (recall 0.150), faltante 1.000 (`metodo-anomalias.md:36-44`); calibración en NY | Método robusto (mediana/MAD) con evaluación a nivel de evento sobre 10 perfiles. | Las etiquetas son **sintéticas** (`metodo-anomalias.md:5`): mide la lógica del método, no detección de eventos reales. Aumentos con F1 0.154 son un resultado débil que debe presentarse como tal. 10 perfiles (5 CO, 5 NY). |
| Gold: `gold_eia_monthly` (5,304), `gold_forecast_monthly` (7,344), `gold_forecast_annual` (459), `gold_forecast_metrics` (312), `gold_resstock_profile_summary` (10), `gold_resstock_monthly` (120), `gold_resstock_pattern`, 4 tablas `gold_anomaly_*` | `manifiesto-gold.json` (filas, bytes, SHA-256 de salida y de entrada); `contrato-gold-propuesta.md` §2 | Cadena de hashes desde `datos/` hasta cada salida. | `contrato-gold-propuesta.md:76` (rama de Emilio) exige la regla de hora local en `gold_resstock_pattern` (EST fijo → UTC → zona IANA) y dice que el conteo de filas se publicará «después de regenerar el Gold con esta regla»: el CSV de la rama puede no cumplirla. Verificarlo antes de usarlo. |
| Análisis descriptivo en `main` | **Integrado en main**: `scripts/analizar_muestra_inicial.py` (341 líneas), `docs/resultados-muestra-inicial.md` | Agregado Colorado 2018 (87.16 %). | Comparación de poblaciones distintas; no mide error. |

### 2.4 Tablero

| Artefacto | Etiqueta | Evidencia | Qué demuestra | Qué NO demuestra |
|---|---|---|---|---|
| Tablero con seis vistas (Resumen, Patrones, Clima, Anomalías, Estimaciones, Flujo/Calidad) | **No implementado** | No hay código de tablero en ninguna rama; solo la demo de 2.1 (una vista) | — | — |
| `docs/especificacion-tablero.md` (143 líneas) y `docs/contrato-gold-propuesta.md` (119) | **Rama remota** (`preparacion/emilio-contrato-gold`, sin PR) | Secciones 4.1–4.6 (fichas R1…Q4), §5 estados de interfaz, §9 verificaciones | Especificación de vistas, filtros, estados y fórmulas; propone un contrato Gold en inglés `snake_case`. | Los propios documentos se declaran «propuesta» sin aprobar (`contrato-gold-propuesta.md:119`; `especificacion-tablero.md:4`, ambos en la rama de Emilio). Sin revisión de Brian, Christian ni Omar. |

### 2.5 Spark local y AWS

| Artefacto | Etiqueta | Evidencia | Qué demuestra | Qué NO demuestra |
|---|---|---|---|---|
| `scripts/job_spark_piloto.py` (1,111 líneas), `scripts/requirements-spark.txt`, `docs/ejecucion-job-spark-local.md` (284 líneas) | **Solo local sin commit** | `validate_paths:56`, `define_schemas:127`, `execute_*_qc:166/322/454`, `publish_atomically_via_sibling_staging:899`, `main:964`; documento líneas 11-19 | Un único job con esquemas explícitos, **20 reglas de calidad** (6 ResStock + 7 EIA + 7 clima), puerta de bloqueo con `REJECTED` y código de salida 1 (`:1028-1047`), publicación atómica por directorio hermano (`:945`), reporte `reporte_calidad.json`. | Sin ejecución real ni pruebas automatizadas (`ejecucion-job-spark-local.md:271-284`). No enriquece `state_code`, `housing_type` ni `profile_weight` (`job_spark_piloto.py:298-299`; el contrato v1 los marca «requerido»). No genera JSON para el tablero. |
| Pipeline Spark por capas + 24 pruebas | **PR abierto** (#4) | `docs/guia-ejecucion-spark.md:112` («24 pruebas exitosas»: 8 EIA + 11 ResStock + 5 JSON); `tests/test_calidad_sintetica_eia.py`, `…_resstock.py`, `test_comparacion_json.py`; `exportar_comparacion_json.py:17-18` → `data/exports/comparacion_co_2018.json` | Es el único trabajo Spark con ejecución declarada y pruebas. Exporta un JSON para el tablero. | Alcance Colorado 2018 con nombres en español (`anio`, `mes`, `estado`, `resstock_mwh`; `exportar_comparacion_json.py:38-44`), no el contrato inglés. El cuerpo del PR dice «cinco pruebas»; la guía dice 24 (descripción desactualizada). Dice «No constituye una ejecución en AWS EMR» (`guia-ejecucion-spark.md:18`). |
| Arquitectura AWS objetivo | **Integrado en main** (diseño) | `docs/arquitectura-aws-por-etapas.md:3` («No se han creado recursos, no se aprobó presupuesto y no se desplegó») | Etapas 0–5 con criterios de salida; seguridad (CloudFront+OAC, Block Public Access) y caché inmutable. | Cero recursos AWS. No hay titular de facturación, monto máximo, región elegida ni estimación (`:61`, `:89-96`). |
| Replay con Kinesis, Spark Structured Streaming, EMR Serverless, S3 | **No implementado** | Ni scripts ni IaC en ninguna rama | — | Dos componentes comprometidos en la propuesta V2 siguen en cero. |

### 2.6 Publicación de datos

| Artefacto | Etiqueta | Evidencia | Qué demuestra | Qué NO demuestra |
|---|---|---|---|---|
| `docs/decision-publicacion-datos.md` (52 líneas), `datos/README.md`, `manifiesto-integracion.json` | **Integrado en main** | Matriz por fuente (ResStock CC BY 4.0; EIA dominio público con atribución; Open-Meteo CC BY 4.0, uso no comercial) | Qué se puede guardar y redistribuir, con atribución; interpretación operativa, no dictamen legal (`:43`). | Pendientes abiertos: material de terceros en el XLSX EIA y recuperar crudos ResStock (`:47-48`). |
| Convención de publicación web `site/data/v1/` + manifiesto + caché | **Integrado en main** (diseño) | `arquitectura-aws-por-etapas.md:48`; `contrato-gold-propuesta.md` §4 (rama de Emilio) | Reglas: JSON con SHA-256 en el nombre y `immutable`; manifiesto al final con `no-cache`; invalidar solo el manifiesto. | Ningún objeto publicado, ningún exportador de ese formato, ningún bucket ni distribución. |
| Reglas de qué Gold puede ser público | **No implementado** | `arquitectura-aws-por-etapas.md:96` lo deja como puerta pendiente | — | Nadie ha decidido qué tablas Gold se redistribuyen. |

## 3. Duplicación entre el job local y el PR #4

| Dimensión | Job local (`scripts/job_spark_piloto.py`) | PR #4 (`jobs/batch/*`) |
|---|---|---|
| Estado | Solo local, **sin ejecución** | Abierto, ejecución en Windows declarada, 24 pruebas declaradas |
| Entrada | `datos/` versionado: Parquet de 10 perfiles (350,400 filas), CSV EIA de 51 estados (5,304), clima (336) | `data/raw/` **no versionado**: agregado ResStock de Colorado 2018 (35,040 intervalos, columnas «96»), XLSX EIA |
| Alcance | 3 fuentes; Silver + Gold | 2 fuentes (sin clima); Bronze + Silver + Gold + comparación + JSON |
| Nombres de columna | Inglés del contrato v1 | Español propio |
| Calidad | 20 reglas + puerta `REJECTED` + publicación atómica | Validación de registros y rechazados + pruebas sintéticas |
| Corrección de fin de intervalo | Resta 15 min (`:764`) | También resta 15 min al agrupar (`guia-ejecucion-spark.md:156`) |
| Salida para tablero | Ninguna | `data/exports/comparacion_co_2018.json` |
| Estructura | Un script monolítico | Un script por paso (10 jobs) |
| PySpark | `>=3.5.0,<4.1.0` (`scripts/requirements-spark.txt`) | `pyspark==4.1.1` (`requirements-spark.txt` en la raíz) |
| Java | 8/11/17 (3.5.x) o 17+ (4.x) | Java 21 |

**Qué se duplica:** la lógica de Silver/Gold mensual de ResStock y de EIA, la corrección de fin de intervalo, la regla «no usar la razón como precisión» y la verificación de conteos. **Qué NO se duplica:** el job local es el único que cubre las 51 jurisdicciones EIA, el clima y las reglas formales del contrato; el PR #4 es el único con pruebas, evidencia de ejecución, JSON de salida y recálculo desde el agregado crudo (lo que `contrato-gold-propuesta.md` §3 pide para `demo_colorado_2018_verificacion.csv`: «Recalcular desde el agregado crudo»).

**Conflictos concretos si ambos entran:**
1. Dos pins de PySpark incompatibles entre sí (`<4.1.0` frente a `==4.1.1`) en dos archivos `requirements-spark.txt` distintos (`scripts/` y raíz); la guía existente en `main` (`docs/ejecucion-piloto-datos.md:3`) menciona además un PySpark 4.0.1 reportado en el PR de Brian. Hay tres versiones citadas.
2. Dos esquemas de nombres (inglés frente a español) para la misma tabla EIA mensual; `contrato-gold-propuesta.md` §5 pide no mantener nombres paralelos en español.
3. Dos directorios de salida (`salidas_spark/` frente a `data/{bronze,silver,gold,exports}/`) y dos reglas de «destino».
4. Dos silvers de EIA con distinto origen (CSV derivado de 51 estados frente a XLSX crudo filtrado a CO).

**Conclusión (recomendación, no decisión tomada):** no son equivalentes ni descartables. Tratar el job local como productor del contrato v1 sobre el piloto de 10 perfiles y el PR #4 como la ruta de verificación independiente de Colorado 2018, con un único contrato de nombres y un único archivo de dependencias. Fusionar el PR #4 tal cual y añadir después el job local sin reconciliar crearía dos «fuentes de verdad».

## 4. Siguiente bloque recomendado: «Gold v1 local, verificable de punta a punta»

**Un solo bloque.** Meta: dejar en GitHub una cadena que, desde `datos/`, produzca Silver/Gold con calidad comprobada y un JSON versionado con manifiesto, sin tocar AWS. El tablero que lo consuma es el bloque siguiente; no se mezcla.

**Por qué este y no otro:** (a) el tablero y la publicación dependen de un Gold con contrato acordado; (b) el job local más cercano a ese contrato no se ha ejecutado y aún no está en Git; (c) el PR #4 aporta ejecución y pruebas declaradas, pero procesa otra población y usa otro esquema; (d) el análisis está en una rama sin PR; (e) AWS depende de decisiones de cuenta y presupuesto que no se resuelven con cambios de código. Por eso conviene cerrar primero la cadena local desde datos hasta una salida JSON versionada y reproducible.

### Tareas, en orden

| # | Tarea | Archivos de salida | Criterio de aceptación comprobable |
|---|---|---|---|
| T0 | **Acordar antes de generar Gold final** D1 (roles de ambos pipelines), D3 (esquema canónico) y D4 (una versión de runtime); registrar cada decisión en `docs/seguimiento.md` con alternativas, decisión y responsable. D2 se resuelve antes de aceptar la analítica de Emilio como Gold canónico; D5 no bloquea este bloque porque se recomienda mantener los 10 perfiles. | Filas nuevas en `docs/seguimiento.md` | D1, D3 y D4 tienen una decisión y responsable; D2 se registra como decisión previa a T5/T6. No se vincula el avance a fechas de entrega. |
| T1 | **Revisar el PR #4** por alguien distinto del autor; corregir la descripción («cinco pruebas» → 24), reconciliar `requirements-spark.txt` y confirmar que ni `data/raw/` ni `data/*` se versionan. | Comentarios de revisión; edición del cuerpo del PR; ajuste de `requirements-spark.txt` según T0 | `gh pr view 4` muestra ≥1 revisión aprobada; el revisor ejecuta `python -m unittest discover -s tests -p "test_*.py"` en su equipo y reporta 24 OK; el JSON de salida mantiene totales 16,809,653.30 y 19,286,952.00 MWh. |
| T2 | **Ejecutar el job local por primera vez** siguiendo `docs/ejecucion-job-spark-local.md:271-284`: prueba positiva, prueba negativa (CSV corrupto), salida no vacía. | `docs/evidencia/ejecucion-job-spark-piloto.md` (comando, versiones de Java/PySpark, código de salida, conteos, SHA-256 de `reporte_calidad.json`) | Positiva: código 0, `estado_global = VALID_WITH_WARNINGS`, `reglas_fallidas = 0`, 350,400 filas ResStock, 12 periodos (2018-01…2018-12), 5,304 filas EIA, 336 de clima, 3 tablas Silver y 2 Gold. Negativa: código 1, `REJECTED`, `bloqueo_publicacion_capas = true`, sin tablas. Directorio no vacío: aborta antes de transformar. |
| T3 | **Cerrar los defectos conocidos del job** antes de generarlo como Gold de producto: enriquecer `state_code`/`housing_type`/`profile_weight` desde metadatos del mismo release, haciendo el join por `bldg_id` y verificando coincidencia 1:1 (no asumir que la selección de 10,000 candidatos contiene los IDs del piloto); normalizar `event_time_utc = timestamp_end_est + 5 h` (contrato v1 §2), unificar `version_job` (el código dice `1.3.0` en `:854`, la doc muestra `1.2.0` en `ejecucion-job-spark-local.md:213`) y añadir pruebas sintéticas mínimas (reutilizando las de #4 cuando apliquen). | Cambios en `scripts/job_spark_piloto.py`; `tests/test_job_piloto_*.py` | Silver ResStock con 0 nulos en `state_code` y `housing_type`; 5 perfiles CO y 5 NY; `event_time_utc` de la primera fila = `2018-01-01 05:15:00`; join completo, único y desde el mismo release; pruebas pasan; `reporte_calidad.json` muestra el mismo `version_job` que la doc. |
| T4 | **Abrir el PR del job local** (`scripts/job_spark_piloto.py`, `scripts/requirements-spark.txt` o archivo unificado, `docs/ejecucion-job-spark-local.md`) con la evidencia de T2. | PR nuevo desde rama `feature/spark-piloto-silver-gold` | PR con pasos de reproducción, resultado observado y revisor distinto del autor (Definition of Done de `docs/plan-de-desarrollo.md:78`). |
| T5 | **Abrir los PR de Emilio** en orden: primero solo documentos (`preparacion/emilio-contrato-gold`), luego código y salidas (`ramificacion-emi-analitica`, con `.gitattributes` `analitica/salidas/** -text`). Antes de integrarlo, verificar que `gold_resstock_pattern` cumpla la conversión EST→UTC→zona local de `contrato-gold-propuesta.md` §1. | 2 PR; `docs/estado-…` actualizado | Los hashes de `manifiesto-gold.json` coinciden con los de `datos/manifiesto-integracion.json` (el propio manifiesto advierte si no); el revisor repite los 3 comandos de `analitica/README.md` y obtiene los números documentados (5.63/3.67/3.47 % y F1 CO 0.664/0.154/1.000) con `warnings: []`. |
| T6 | **Exportar JSON versionado + manifiesto** desde las tablas Gold según `contrato-gold-propuesta.md` §4 (nombre `tabla.<sha256>.json`, `manifest.json` al final), en una carpeta local equivalente a `site/data/v1/`. | `jobs/` o `scripts/exportar_gold_json.py`; `site/data/v1/manifest.json` y `site/data/v1/<tabla>.<sha256>.json` | Cada archivo del manifiesto existe y su SHA-256 coincide con el nombre; `schema_version = "1.0"`; el manifiesto lleva linaje, filas y versiones, y la descripción de cada tabla conserva avisos como eventos sintéticos y «razón descriptiva ≠ precisión»; no se incluyen `raw/`, `bronze/`, `silver/` ni crudos. |

**Fuera del bloque, a propósito:** reescritura del tablero, cualquier recurso AWS, Kinesis, ampliación a más de 10 perfiles.

### Bloqueos concretos

1. **Entorno de ejecución:** T1–T3 requieren JVM y PySpark instalados; el job local nunca se ha probado en este equipo (sin verificación aquí de Java). La guía de #4 exige Java 21 y la local acepta 17+ para PySpark 4.x.
2. **Revisión humana:** PR #4 tiene 0 revisiones; los PR de Emilio no existen; el contrato Gold sigue siendo «propuesta» hasta que Brian, Christian y Omar la confirmen en un PR.
3. **Decisión de la fuente de verdad** (6.2-D1): sin ella, T1/T4 reproducen la duplicación de la sección 3.
4. **Workspace principal con cambios sin commit:** `README.md`, `plan-de-desarrollo.md` y `arquitectura-aws-por-etapas.md` locales divergen de `main`; hay que reconciliarlos o descartarlos antes de abrir los PR de T4, o se arrastrarán por accidente.
5. **AWS (fuera de este bloque):** sin titular, monto máximo, región ni estimación, no se puede iniciar la etapa 1 (`arquitectura-aws-por-etapas.md:76`, «continuar localmente»).

## 5. Estado resumido frente a lo comprometido en la propuesta V2

| Componente comprometido | Estado verificado |
|---|---|
| Análisis descriptivo y patrones | Parcial: demo local de Colorado 2018 (solo local) y Gold de patrones en rama remota. |
| Estimaciones | Rama remota, sin PR; backtest 2024-2025 declarado. |
| Detección de anomalías | Rama remota, sin PR; solo etiquetas sintéticas. |
| Tablero interactivo | Una vista, sin datos externos, solo local. Seis vistas especificadas, no construidas. |
| Spark | Integrado: ninguno. PR abierto: pipeline CO 2018. Solo local: job del piloto sin ejecutar. |
| S3, EMR, Kinesis, replay | No implementado. Diseño integrado en `main`. |
| Calidad/gobernanza de datos | Integrada en `main` (contrato v1, publicación, manifiestos); controles en código aún no integrados. |

## 6. Qué ya está escrito y qué falta decidir

### 6.1 Recomendaciones ya escritas (en archivos; no son decisiones tomadas)

| Recomendación | Dónde | Estado |
|---|---|---|
| Conservar 10 perfiles como alcance del primer tablero; no esperar los 10,000 | `contrato-gold-propuesta.md` §5; `especificacion-tablero.md` §7 y §9.4 (rama de Emilio) | «Valor por defecto para revisión» |
| Nombres en inglés `snake_case`; Parquet canónico; JSON versionado para el tablero; CSV opcional | `contrato-gold-propuesta.md` §1 y §5 | Propuesta sin aprobar |
| Convertir EST fijo → UTC → zona IANA antes de agrupar por hora/día/mes | `contrato-datos-v1.md:51`; `contrato-gold-propuesta.md` §1 | Propuesta; implementada en el job local solo a medias (sin `event_time_utc` ni zona) |
| `gold/v1/` privado; web solo con JSON aprobado; JSON inmutable; manifiesto al final con invalidación | `arquitectura-aws-por-etapas.md:48`; `contrato-gold-propuesta.md` §4 | Integrado en `main` como diseño |
| Continuar localmente si falta titular, monto, notificaciones o responsable de limpieza | `arquitectura-aws-por-etapas.md:76` | Integrado en `main` |
| Reducir alcance antes que presentar funciones sin validar | `plan-de-desarrollo.md:22` | Integrado en `main` |
| Rotular la razón 87.16 % como «descriptiva», nunca «precisión»; eventos sintéticos y escenario 2026-09…2027-12 rotulados | `especificacion-tablero.md` §2 | Propuesta |

### 6.2 Decisiones que todavía debe responder una persona

| ID | Decisión | Quién | Bloquea |
|---|---|---|---|
| D1 | ¿Cuál es la fuente de verdad de Silver/Gold: job local (contrato v1) sobre el piloto de 10 perfiles, PR #4 (Colorado 2018 crudo) o ambos con roles distintos como se recomienda en la sección 3? | Christian (autor de #4), con Omar | T1, T4 |
| D2 | ¿Se acepta que pronóstico y anomalías (pandas, CSV) sean el Gold analítico final, o deben reescribirse en Spark? Hoy el contrato dice Parquet canónico. | Diego y Christian | T5, T6 |
| D3 | ¿Se aprueba el contrato Gold en inglés `snake_case` y se convierte el JSON del PR #4 a ese esquema? | Christian, Brian, Omar | T1, T6 |
| D4 | ¿Una sola versión de PySpark/Java para todos (4.0.1, 4.1.1 o `<4.1`)? | Christian y Omar | T1, T2 |
| D5 | Confirmar que 10 perfiles son el alcance inicial y si se autoriza planear una muestra mayor más adelante. | Brian | Ampliación de datos; no bloquea el bloque |
| D6 | ¿Qué hacer con los cambios sin commit del workspace principal (README, plan, arquitectura, PPTX)? | Omar | T4 |
| D7 | ¿La demo y la presentación nueva entran al repositorio? ¿En qué rama y PR? | Omar | Tablero |
| D8 | Titular de la cuenta AWS, método de acceso, monto máximo total y por ejecución, región (`mx-central-1` frente a `us-east-1`), número de perfiles a subir, duración y tope de eventos del replay, retención. | Omar con el equipo | Todo lo de AWS |
| D9 | ¿Qué artefactos Gold son redistribuibles y pueden ser públicos vía tablero? | Brian y Omar | Publicación |

## 7. Inconsistencias detectadas (para corregir, no para interpretar)

1. `docs/ejecucion-job-spark-local.md:213` muestra `version_job: "1.2.0"`; el código (`scripts/job_spark_piloto.py:854`) emite `1.3.0`.
2. El cuerpo del PR #4 dice «Cinco pruebas automatizadas»; `docs/guia-ejecucion-spark.md:112` documenta 24.
3. El README de `main` conserva casillas de estado anteriores al PR #2 (no marca el piloto de 10 perfiles, la muestra de clima ni la selección de 10,000 IDs); el README local sin commit sí las añade. Ninguno enlaza la demo ni los contratos Gold.
4. `docs/ejecucion-piloto-datos.md:3` y `:94` citan una comprobación en PySpark 4.0.1 «reportada» por el PR de Mares y aclaran que no se reprodujo; `main` no contiene el pin ni la evidencia de esa ejecución, y ese PR no aparece en `gh pr list` (#1 cerrado, #2 integrado).
5. `docs/seguimiento.md` en `main` no tiene filas para PR #4, las ramas de analítica ni el contrato Gold.
6. El workspace principal está en una rama ya integrada (`avance/datos-y-gobernanza`) con cambios que no están en `main`.

## 8. Límites de esta revisión

- No se reprodujo ninguna cifra (87.16 %, 24 pruebas, sMAPE, F1, conteos del job local).
- No se verificó la instalación de Java/PySpark ni se ejecutó nada.
- No se revisó línea a línea `p.html`, `c.html`, los PDF/DOCX de la propuesta ni el PPTX nuevo.
- El juicio sobre duplicación se basa en el código y la documentación leídos, no en una ejecución comparada.
- Las rutas con líneas apuntan al estado del 17-nov-2026; si el PR #4 o las ramas cambian, hay que repetir la comprobación.
