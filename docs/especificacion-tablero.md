# Especificación del tablero

**Responsable:** Diego (analítica y producto) · **Revisión pendiente:** Brian (procedencia y población) y Christian (esquema gold)
**Estado:** propuesta revisada para acordar alcance y lecturas del tablero antes de conectarlo a Gold. No certifica implementación.
**Datos de referencia:** la rama remota `ramificacion-emi-analitica` contiene salidas exploratorias en `analitica/salidas/`; no están integradas en `main`. El esquema propuesto está en [`contrato-gold-propuesta.md`](contrato-gold-propuesta.md). El tablero debe consumir la exportación JSON versionada de Gold, no depender de rutas locales de trabajo.

## 1. Pregunta central

> ¿Cómo se comporta el consumo eléctrico residencial en Estados Unidos, qué patrones y comportamientos inusuales se observan en los perfiles modelados, y qué estimaciones pueden sostenerse con la historia disponible?

| Vista | Pregunta que responde |
|---|---|
| Resumen | ¿Qué datos hay, de qué fuente y qué tan grande es el consumo residencial? |
| Patrones | ¿Cómo varía el consumo por mes, hora, día de la semana y tipo de vivienda? |
| Clima | ¿Qué información climática hay y por qué todavía no se une al consumo? |
| Anomalías | ¿Qué es un comportamiento atípico, cómo se detecta y qué tan bien funciona el método? |
| Estimaciones | ¿Cuánto consumo residencial se esperaría y qué error tuvo el método en meses ya conocidos? |
| Flujo/Calidad | ¿De dónde viene cada cifra, qué cobertura tiene y qué controles pasó? |

## Dirección visual para la siguiente iteración

Se adopta como referencia visual el [reel isométrico de **Code Boss**](https://www.facebook.com/share/v/19w4Hzb211/) compartido por el equipo: vivienda ilustrada en perspectiva como foco visual, navegación lateral, tarjetas claras, jerarquía marcada y transiciones suaves. La vivienda se usará como ilustración conceptual, sobre todo en Resumen y Patrones; cada vista conservará sus gráficas y tablas como representación de los datos.

- Enlazar la selección visual solo con metadatos existentes, como estado, tipo de vivienda y perfil; mostrar kWh, periodo, hora local y procedencia solo cuando estén disponibles en Gold.
- No representar planos reales, habitaciones, termostatos, interruptores ni consumo por cuarto: las fuentes actuales no contienen esas variables.
- Diferenciar claramente ResStock modelado, ventas EIA, clima y estados `Final`/`Preliminary` mediante color, texto, unidad y etiqueta de fuente; no depender solo del color.
- Animar de forma breve navegación, selección y cambio de periodo/serie; no simular telemetría viva. Respetar `prefers-reduced-motion`.
- Mantener superficies claras, contraste suficiente, textos legibles y controles accesibles en escritorio y móvil.

Esta dirección define trabajo pendiente de diseño e implementación; no afirma que el tablero ya tenga estos elementos.

## 2. Reglas de lectura (lo que el tablero NO afirma)

1. **La razón 87.16 % no es "precisión".** Compara el total modelado de ResStock (solo unifamiliar aislada de Colorado, 2018) con las ventas residenciales EIA de todo el estado: poblaciones y definiciones distintas. Se rotula "razón descriptiva".
2. **ResStock son perfiles modelados, no mediciones de hogares.** El piloto son 10 perfiles (5 de CO y 5 de NY, uno por tipo de vivienda en cada estado). No representan al estado ni al país. El peso de todos es idéntico (253.9), así que no se usa para estimar totales.
3. **No hay relación clima-consumo.** El clima disponible son 2 puntos de Colorado durante 7 días de enero de 2018. No se grafica correlación ni se sugiere causalidad.
4. **Los eventos de anomalía son sintéticos.** Demuestran la lógica del método; no son hechos reales de la red eléctrica ni de un hogar.
5. **El pronóstico se evalúa con meses ya conocidos (backtest).** Los meses de 2026 son preliminares y se muestran aparte. La proyección sep 2026–dic 2027 es un **escenario** sin validación posterior.
6. **El replay de Kinesis es una reproducción de históricos** con sus fechas originales, no telemetría en vivo.
7. **Los timestamps originales de ResStock representan EST fijo (UTC−5), no la hora local de cada estado.** Para el eje de hora del día, se toma el inicio del intervalo (fin menos 15 minutos), se convierte de EST fijo a UTC y luego a la zona IANA del estado. El eje indica la zona local, por ejemplo `Hora local · America/Denver` o `Hora local · America/New_York`. No se cambia solo la etiqueta: la conversión ocurre antes de agrupar por periodo local, día y hora. Los datos horarios conservan el timestamp de origen, UTC, hora local y desplazamiento UTC. Las comparaciones de total mensual ResStock/EIA conservan el calendario fuente del release y se rotulan como comparación de poblaciones distintas; no se recalculan con periodos locales parciales.

## 3. Filtros globales

Un filtro que no aplica a la vista activa se **deshabilita con una explicación**; nunca se ignora en silencio.

| Filtro | Valores | Aplica a | Nota |
|---|---|---|---|
| Estado | EIA: 51 (50 + DC) y "Suma 51". ResStock piloto: CO, NY. Clima: CO | Todas | Al cambiar de fuente, si el estado no existe en ella, se muestra estado vacío |
| Tipo de vivienda | 5 tipos RECS | Solo ResStock | Sin efecto en EIA ni clima |
| Periodo | EIA 2018-01…2026-08; ResStock 2018; clima 2018-01-01…07 | Todas | Se limita al rango de la fuente |
| Fuente | EIA · ResStock · Open-Meteo | Resumen, Flujo/Calidad | Las demás vistas ya están ligadas a una fuente |
| Granularidad | Mensual (EIA, ResStock) · Horaria (perfiles, clima) | Patrones, Clima | No se ofrece "diaria": no hay tabla gold diaria |
| Datos finales/preliminares | Mostrar preliminares sí/no | EIA, Estimaciones | Por defecto sí, con marca visual distinta |

## 4. Vistas y fichas de gráfica

Convención: **Datos** = tabla gold · grano · unidad. Todas las gráficas muestran junto a ellas el chip de procedencia (sección 8).

### 4.1 Resumen

| ID | Pregunta | Datos | Diseño | Lectura correcta y límite |
|---|---|---|---|---|
| R1 | ¿Qué magnitud y cobertura tiene lo que se muestra? | 4 tarjetas: (a) ventas EIA 2025 del estado o suma 51 (`gold_eia_monthly`, MWh, anual); (b) meses finales y preliminares (`cobertura_eia`); (c) perfiles ResStock en piloto = 10; (d) sMAPE del mejor modelo en backtest (`gold_forecast_metrics`) | Tarjetas con valor, unidad, año y chip de fuente | Cada cifra nombra población y periodo. (c) no dice "10,000 perfiles": son 10 descargados |
| R2 | ¿Cómo se comparan las escalas de ResStock y EIA en Colorado 2018? | `demo_colorado_2018_verificacion` (interino), calendario publicado del release, mensual, MWh | Barras agrupadas por mes (ResStock/EIA) + línea de razón en eje secundario | Rótulo fijo: "razón descriptiva entre poblaciones distintas, no precisión". Fuente interina: aún no recalculada de forma independiente. Mantener el calendario fuente EST para reproducir esta comparación; no mezclarla con los periodos locales parciales de P2. |

### 4.2 Patrones

| ID | Pregunta | Datos | Diseño | Lectura correcta y límite |
|---|---|---|---|---|
| P1 | ¿Cómo es la estacionalidad residencial del estado y cómo ha cambiado por año? | `gold_eia_monthly`, mensual, MWh | Líneas, eje x = mes (1–12), una línea por año; 2026 punteada y rotulada "preliminar" | Muestra ventas, no consumo medido por hogar. Filtro: estado |
| P2 | ¿A qué horas y en qué meses consume más un perfil? | `gold_resstock_pattern.median_kwh`, hora local × periodo local, kWh por hora | Mapa de calor; conmutador laboral/fin de semana; selector de perfil | Un perfil modelado. Eje en hora local, con zona visible según el estado. Los periodos locales incompletos se identifican visualmente y no se comparan como meses completos. Filtros: estado, tipo de vivienda |
| P3 | ¿Cómo difiere el consumo anual entre tipos de vivienda? | `gold_resstock_profile_summary.annual_kwh`, anual, kWh por perfil | Barras agrupadas por estado, color por tipo | Un perfil por tipo y estado: **exploratorio**, no una comparación estadística |

### 4.3 Clima

| ID | Pregunta | Datos | Diseño | Lectura correcta y límite |
|---|---|---|---|---|
| C1 | ¿Qué temperatura hubo en los dos puntos consultados? | `clima_open_meteo_muestra` (interino), horaria UTC, °C | Líneas por punto (Denver, Grand Junction); eje x en UTC | Celdas de reanálisis ERA5-Land, no estaciones. 1–7 ene 2018 |
| C2 | ¿Se puede relacionar clima y consumo? | — | Panel de estado "dato no comparable" con el motivo (cobertura de 7 días y 2 puntos; EST vs UTC; sin regla de unión) | No hay gráfica de correlación hasta que exista un mapeo geográfico y horario documentado |

### 4.4 Anomalías

Un aviso fijo en la parte superior: **"Eventos inyectados de forma sintética para evaluar el método. No son eventos reales."**

| ID | Pregunta | Datos | Diseño | Lectura correcta y límite |
|---|---|---|---|---|
| A1 | ¿Qué ve el método alrededor de un caso? | `gold_anomaly_case_series`, horaria, kWh (±48 h), con tiempo de origen, UTC y local | Líneas: observado, línea base, original (antes de inyectar); zonas sombreadas = alerta; selector de caso (5) | El caso "no detectado" y la "alerta sin etiqueta" se muestran igual que los demás. El eje usa hora local del estado y muestra la zona; los datos originales EST se conservan para auditoría. |
| A2 | ¿Qué disparó cada caso? | `gold_anomaly_cases` | Tabla: observado, referencia, diferencia, métrica disparadora, regla, resultado, etiqueta "sintético" | La alerta sin etiqueta no es un evento confirmado |
| A3 | ¿Qué tan bien detecta el método? | `gold_anomaly_metrics`, `gold_anomaly_sensitivity` | Tabla/barras de precision, recall y F1 por categoría y conjunto (calibración NY / evaluación CO); recall por magnitud | Las métricas comparan predicciones con etiquetas sintéticas; solo se presentarán tras integrar la documentación metodológica y salidas analíticas correspondientes. |

### 4.5 Estimaciones

| ID | Pregunta | Datos | Diseño | Lectura correcta y límite |
|---|---|---|---|---|
| E1 | ¿Qué tan cerca estuvo el pronóstico de lo ocurrido en 2024–2025? | `gold_forecast_monthly` (split `backtest`), mensual, MWh | Real vs pronóstico; selector de modelo (3); 2026 preliminar punteado (`preliminary_check`) | Modelo ajustado solo con 2018–2023. Filtro: estado o suma 51 |
| E2 | ¿Cuál es el error de cada modelo? | `gold_forecast_metrics`, MAE/RMSE (MWh), sMAPE (%) | Tabla ordenable por modelo y estado | Métricas titulares = solo `backtest`. Si `n_not_interpretable` > 0, se marca el mes |
| E3 | ¿Cuánto sumó el año real y el estimado? | `gold_forecast_annual` | Barras real vs pronóstico por año (2024, 2025) | Años completos únicamente |
| E4 | ¿Qué se proyecta para sep 2026–dic 2027? | `gold_forecast_monthly` (split `forward`) | Línea con banda de rótulo "Escenario" | **Escenario**, no pronóstico validado. Sin intervalos de predicción |

Los perfiles ResStock 2018 se presentan siempre como **perfil/escenario**, nunca como pronóstico longitudinal.

### 4.6 Flujo/Calidad

| ID | Pregunta | Datos | Diseño | Lectura correcta y límite |
|---|---|---|---|---|
| Q1 | ¿Qué cobertura temporal tiene EIA? | `cobertura_eia` (interino), año × estado | Cuadrícula con meses finales, preliminares y faltantes | 2026 trae 8 meses preliminares y 4 faltantes por diseño |
| Q2 | ¿De dónde viene cada tabla? | `manifiesto-gold.json`, `manifiesto-integracion.json` | Tabla: archivo, filas, bytes, SHA-256 (abreviado), fuente, entradas | Muestra la cadena de hashes hasta los datos de entrada |
| Q3 | ¿Qué estado tiene el replay y el pipeline? | Pendiente (Christian/Omar) | Panel "no disponible todavía" con estado de carga/error | No se simula un estado "en vivo" |
| Q4 | ¿Qué controles de calidad se pasaron? | Pendiente (`quality_status` de Christian) | Lista de controles con válido / válido con avisos / rechazado | Se llena cuando exista el gold de Spark |

## 5. Estados de interfaz

| Estado | Cuándo aparece | Texto de ejemplo |
|---|---|---|
| Cargando | Mientras se leen las tablas gold | "Cargando datos…" con esqueleto de la gráfica |
| Sin datos | Filtros sin filas (p. ej., Texas en ResStock) | "No hay perfiles ResStock para TX en el piloto. Disponibles: CO, NY." |
| Dato no comparable | Mezcla de fuentes sin unión válida | "Clima y consumo no se unen: 7 días, 2 puntos y husos horarios distintos." |
| Error de carga | Falla al leer o validar el archivo | "No se pudo cargar `gold_forecast_monthly.csv` (versión de esquema 1.0 esperada)." |
| Preliminar | Datos EIA con `Preliminary` | Marca visual distinta + "Preliminar, puede cambiar" |

Requisitos transversales: diseño responsive (escritorio y móvil), navegación completa por teclado, contraste suficiente, gráficas con resumen textual para lectores de pantalla, y consola del navegador sin errores.

## 6. Diccionario de fórmulas

| Término | Fórmula | Nota |
|---|---|---|
| Razón descriptiva | `ResStock_mes_MWh / EIA_mes_MWh × 100` | No es precisión ni error |
| Hora de un intervalo | `timestamp_inicio_est = timestamp_fin_est − 15 min`; convertir EST fijo a UTC sumando 5 h y después convertir a la zona IANA del estado | Cada hora local agrega los intervalos que caen en esa hora después de la conversión. `period_local`, `day_type` y `hour_local` se calculan con el inicio local del intervalo. Guardar `utc_offset_minutes` para distinguir horas repetidas por DST. |
| Línea base | Mediana del perfil por (mes, tipo de día, hora) | Tipo de día: laboral o fin de semana. No modela festivos |
| Score robusto | `(x − mediana) / max(1.4826 × MAD, piso)` | Piso = 10 % de la mediana horaria del perfil (mín. 0.01 kWh) |
| Razón vs línea base | `x / mediana` | Se usa para caídas |
| MAE / RMSE | `mean|f−a|` · `sqrt(mean (f−a)²)` | MWh |
| sMAPE | `200 × |f−a| / (|a|+|f|)` | No interpretable si `|a|+|f| < 1 MWh` |
| Precision / recall / F1 | A nivel de **evento** | Recall = eventos detectados / eventos inyectados; precision = alertas que tocan un evento / alertas |
| Escenario | Pronóstico sin dato real posterior | Siempre rotulado |

## 7. Variables, filtros y agregados para revisar (Brian)

- **EIA mensual:** `period`, `state_code`, `data_status`, `sales_mwh`; cobertura por año/estado con meses finales, preliminares y faltantes. En los datos integrados actuales hay 5,304 registros de 51 jurisdicciones, desde 2018-01; las etiquetas Final/Preliminary se conservan.
- **ResStock:** `bldg_id`, `state_code`, `housing_type`, `profile_weight`, kWh por intervalo/perfil, timestamps fuente/UTC/local, `time_zone`, `utc_offset_minutes` y conteo de perfiles por estado/tipo. El piloto integrado actual contiene 10 perfiles; son una muestra exploratoria, no una estimación representativa.
- **Clima:** `point_id`, `state_code`, coordenadas consultadas y de celda, `timestamp_utc`, `temperature_c`, `model`. Se presenta separado hasta definir una correspondencia geográfica reproducible; no se calcula relación clima-consumo con la muestra disponible.
- **Filtros globales:** estado, periodo y fuente cuando existan; tipo de vivienda solo para ResStock; `data_status` solo para EIA/pronósticos; día de semana/fin de semana solo para patrones y anomalías. Cada control fuera de ámbito se deshabilita y explica el motivo.
- **Recomendación de alcance para Brian:** conservar los 10 perfiles actuales en el primer tablero y etiquetar todas las vistas como exploratorias; no bloquear el avance esperando 10,000 perfiles. Ampliar después solo con una selección versionada, QC aprobado, procedencia y confirmación de disponibilidad/licencia.
- **Confirmaciones concretas solicitadas:** Brian valida si 10 perfiles siguen siendo el alcance del primer tablero y si autoriza planear una muestra mayor para una fase posterior; Christian confirma el esquema inglés `snake_case`, Parquet canónico y exportación JSON para el tablero, además de la conversión horaria indicada en el contrato.

## 8. Procedencia junto a cada KPI

Chip con: fuente · tipo (modelado / oficial / reanálisis / sintético) · periodo · unidad · cobertura · versión de esquema. Ejemplo: `EIA-861M · oficial · 2018–2025 Final · MWh · 51 jurisdicciones · esquema 1.0`.

## 9. Verificaciones de integración

1. Antes de conectar las seis vistas, verificar que el PR de analítica haya sido integrado y que sus hashes de salida coincidan con el manifiesto de Gold.
2. Verificar que el job Spark produzca las columnas del contrato inglés `snake_case` y que `schema_version`, hashes de entradas y `quality_status` queden en manifiesto/metadatos; `quality_flags` se conserva en las filas o rechazos según el contrato. No conectar tablas con nombres distintos mediante alias invisibles en la interfaz.
3. Verificar una conversión temporal de prueba para Colorado y Nueva York, incluidos límites de mes/año y el cambio de horario estacional, antes de generar el agregado horario local.
4. Mantener el piloto de 10 perfiles como alcance inicial. La ampliación de muestra es una decisión de fase posterior y no debe mezclarse con las cifras de la primera versión del tablero.
