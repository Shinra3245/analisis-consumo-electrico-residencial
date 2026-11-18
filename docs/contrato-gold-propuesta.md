# Propuesta de contrato gold — capa de consumo para el tablero

**Responsable:** Diego · **Para revisión de:** Brian (variables y población), Christian (esquema y Spark) y Omar (rutas S3 y publicación)
**Estado:** propuesta revisada para acordar un único contrato antes de conectar el tablero. La rama remota `ramificacion-emi-analitica` contiene scripts y salidas exploratorias; todavía no están integrados en `main` y no son una salida verificada del job Spark de Christian. Las cifras y esquemas aquí descritos deben cotejarse con sus manifiestos y con el contrato v1 antes de publicarse.
**Relación con el [contrato v1](contrato-datos-v1.md):** el v1 define silver y trazabilidad; este define las agregaciones gold que consume el tablero (punto 4 de su sección 6).

## 1. Convenciones

| Tema | Regla |
|---|---|
| Formato canónico | Parquet para Silver/Gold en S3; conservar tipos, esquema y particiones. |
| Formato para el tablero | JSON UTF-8 derivado desde Gold bajo `site/data/v1/`; CSV UTF-8 puede conservarse como exportación de intercambio, no como salida canónica. |
| Nombres de columna | Inglés `snake_case`, igual que las tablas silver del contrato v1 |
| Periodos | `YYYY-MM` para agregados mensuales. Las comparaciones mensuales ResStock/EIA conservan el calendario de publicación del release; los patrones por hora local derivan su mes tras convertir el inicio de intervalo a la zona IANA del estado y marcan periodos parciales. |
| Timestamps ResStock | El origen `timestamp_end_est` es EST fijo (UTC−5), sin horario de verano. Se conserva; `event_time_utc = timestamp_end_est + 5 h`; después se deriva la hora local con la zona IANA del estado (por ejemplo, `America/Denver` para CO y `America/New_York` para NY). No se debe renombrar un timestamp sin convertirlo. |
| Unidades | MWh para EIA y pronósticos; kWh para perfiles ResStock; °C para clima |
| Fuentes | ResStock, EIA y clima **no se fusionan** en una misma fila |
| Datos preliminares | Se conservan como `Preliminary`; nunca se rotulan `Final` |
| Eventos sintéticos | Toda tabla de anomalías lleva `is_synthetic*` explícito |
| Versión | `schema_version` = `1.0` en `manifest.json`; cambios incompatibles incrementan la versión mayor del prefijo. |
| Hash/linaje | El manifiesto lista filas, bytes, SHA-256, hashes de entradas y versiones de código/esquema que produjeron cada salida. |
| Tiempos horarios | Conservar timestamp fuente EST, instante UTC y hora local. Los totales mensuales usados en comparaciones mantienen el calendario fuente; los patrones horarios calculan `period_local`, `day_type` y `hour_local` desde el inicio convertido a hora local. Marcar periodos locales parciales y conservar el desplazamiento UTC en horas repetidas por DST. |

## 2. Tablas que produce analítica (ya generadas)

### 2.1 `gold_eia_monthly` — ventas residenciales mensuales EIA
PK `(period, state_code)` · 5,304 filas · origen `datos/eia_residencial_mensual.csv`

| Columna | Tipo | Regla |
|---|---|---|
| `period` | `YYYY-MM` | 2018-01…2026-08 |
| `state_code` | texto(2) | 50 estados + `DC` |
| `data_status` | enum | `Final` · `Preliminary` |
| `sales_mwh` | decimal | MWh; finito y no negativo (validado) |

El sector (`RES`) es constante y se omite.

### 2.2 `gold_forecast_monthly` — real vs pronóstico
PK `(state_code, period, model_id, split)` · 7,344 filas

| Columna | Tipo | Regla |
|---|---|---|
| `state_code`, `period` | — | como arriba |
| `model_id` | enum | `seasonal_naive` · `seasonal_mean` · `log_linear_trend` |
| `split` | enum | `backtest` (ajuste 2018-2023, evalúa 2024-2025) · `preliminary_check` (ene-ago 2026 vs dato preliminar) · `forward` (ajuste 2018-2025, proyecta sep 2026-dic 2027) |
| `actual_status` | enum/vacío | `Final`/`Preliminary`; vacío en `forward` |
| `actual_mwh` | decimal/vacío | vacío en `forward` |
| `forecast_mwh` | decimal | pronóstico |
| `in_headline_metrics` | bool | `true` solo en `backtest` |

### 2.3 `gold_forecast_annual`
PK `(state_code, year, model_id, split)` · 459 filas. Solo **años completos** (2024, 2025, 2027).
Columnas: `state_code, year, model_id, split, actual_mwh, forecast_mwh, pct_error` (`pct_error` vacío sin dato real).

### 2.4 `gold_forecast_metrics`
PK `(scope, state_code, model_id, split)` · 312 filas

| Columna | Regla |
|---|---|
| `scope` | `state` o `all_51` (suma mensual de las 51 jurisdicciones; `state_code = ALL`) |
| `split` | `backtest` o `preliminary_check` |
| `eval_window` | p. ej. `2024-01..2025-12` |
| `n_months`, `mae_mwh`, `rmse_mwh`, `smape_pct` | métricas |
| `n_not_interpretable` | meses con sMAPE no interpretable (denominador < 1 MWh) |
| `in_headline_metrics` | `true` solo en `backtest` |

### 2.5 `gold_resstock_profile_summary`
PK `bldg_id` · 10 filas.
`bldg_id, source_year, annual_kwh, mean_hour_kwh, peak_hour_kwh, n_hours, state_code, housing_type, profile_weight`. `source_year` conserva el año del release; `n_hours` = 8,760 por perfil. `profile_weight` es idéntico en los 10: no usar como estimador. No se presenta como total del año civil local si los límites del periodo difieren.

### 2.6 `gold_resstock_monthly`
PK `(bldg_id, source_period)` · 120 filas para los 10 perfiles. `bldg_id, source_period, kwh_month, state_code, housing_type`. `source_period` conserva el calendario mensual del release en EST fijo y el mes se asigna por el inicio del intervalo EST. Esta tabla permite reproducir las comparaciones con el agregado del release; no se interpreta como total de un mes civil en hora local.

### 2.7 `gold_resstock_pattern`
PK `(bldg_id, period_local, day_type, hour_local, utc_offset_minutes)`.
`bldg_id, period_local, day_type (weekday|weekend), hour_local (0-23), utc_offset_minutes, is_partial_period, median_kwh, mean_kwh, p10_kwh, p90_kwh, n_obs, state_code, housing_type, time_zone`. Se calcula desde los intervalos originales después de convertirlos a hora local. Un año de datos etiquetado 2018 en EST fijo puede abarcar partes de diciembre de 2017 y diciembre de 2018 en la hora local de Colorado; esas filas deben marcarse `is_partial_period=true` y no presentarse como meses completos. La cantidad de filas se publicará en el manifiesto después de regenerar el Gold con esta regla. En horas repetidas por horario de verano, `utc_offset_minutes` distingue ambos instantes.

### 2.8 Anomalías (etiquetas sintéticas)

**`gold_anomaly_metrics`** — PK `(eval_set, category, magnitude)`: `eval_set` (`calibration`=NY, `evaluation`=CO), `category` (`aumento`, `caida`, `faltante`, `aumento+caida`), `magnitude` (`all`, `low`, `mid`, `high`), `n_events, n_detected, recall, n_alerts, n_true_alerts, precision, f1`, parámetros usados (`z_up, ratio_down, min_run_hours`), `method`, `is_synthetic_labels`. Por magnitud solo hay `recall`.

**`gold_anomaly_sensitivity`** — `min_run_hours, category, n_events, n_detected, recall, n_alerts, n_true_alerts, precision, f1` (evaluación).

**`gold_anomaly_cases`** — PK `case_id`: `case_id, kind` (`synthetic_detected`, `synthetic_missed`, `unlabeled_alert`), `outcome, bldg_id, state_code, housing_type, category, magnitude, start_est, end_est, n_hours, observed_kwh, baseline_kwh, diff_kwh, trigger_metric, trigger_value, rule, is_synthetic`.

**`gold_anomaly_case_series`** — PK `(case_id, timestamp_start_est)`: `timestamp_start_est, event_time_utc, timestamp_start_local, utc_offset_minutes, observed_kwh, original_kwh, baseline_kwh, score, ratio_to_baseline, alert` (`aumento`/`caida`/`faltante`/vacío). `original_kwh` es el valor antes de inyectar. El timestamp EST se conserva como clave de origen; el eje de la vista usa la hora local del perfil y muestra su zona.

## 3. Tablas de otros integrantes (interinas, sin cambios por analítica)

| Necesidad del tablero | Fuente interina hoy | Propietario del gold final | Pendiente |
|---|---|---|---|
| Comparación ResStock/EIA Colorado 2018 (R2) | `datos/demo_colorado_2018_verificacion.csv` | Christian + Brian | Recalcular desde el agregado crudo (hoy sin verificación independiente) |
| Cobertura EIA (Q1) | `datos/cobertura_eia.csv` | Brian | Decidir si se renombra a inglés |
| Clima (C1) | `datos/clima_open_meteo_muestra.csv` | Brian + Christian | Regla de unión geográfica y de huso horario |
| Estado de pipeline/replay (Q3) y controles de calidad (Q4) | No existe | Christian + Omar | `quality_status`, `quality_flags`, `replay_id`, `ingested_at_utc` |

## 4. Publicación propuesta en S3 (Omar)

```
s3://<bucket>/gold/v1/<tabla>/part-*.parquet
s3://<bucket>/gold/v1/manifest.json
s3://<bucket>/site/data/v1/<tabla>.<sha256>.json
s3://<bucket>/site/data/v1/manifest.json
```
Gold canónico permanece privado y el tablero consume solo las exportaciones JSON aprobadas en `site/data/v1/`. Los objetos JSON con nombre basado en contenido reciben `Cache-Control: public, max-age=31536000, immutable`; el manifiesto mutable recibe `Cache-Control: no-cache, max-age=0, must-revalidate`. La política de caché de CloudFront debe tener TTL mínimo 0 y respetar esos encabezados. Al publicar una versión completa, se escriben primero todos los objetos inmutables y después el manifiesto; al final se invalida únicamente `/site/data/v1/manifest.json`. No se sobrescriben objetos Gold de una publicación ya emitida.

El tablero lee una URL base configurada para `site/data/v1/`; cambiar el bucket o distribución no debe requerir cambiar el esquema. La rama de analítica puede seguir generando CSV locales como evidencia/intercambio, pero la exportación JSON debe ser reproducible desde la misma tabla Gold y quedar registrada en el manifiesto.

## 5. Recomendaciones de contrato para confirmar

| Tema | Recomendación concreta | Revisión necesaria |
|---|---|---|
| Nombres | Inglés `snake_case`, coincidente con `contrato-datos-v1.md` y este documento. No mantener nombres paralelos en español en Gold. | Christian confirma que el job puede emitir el contrato; Brian revisa variables. |
| Formato | Parquet es la fuente Gold canónica; JSON versionado es el formato de lectura del tablero estático; CSV queda como exportación opcional. | Christian y Omar confirman compatibilidad con el job y la publicación. |
| Hora | Convertir EST fijo → UTC → zona IANA del estado antes de calcular hora, día o mes; mostrar hora local con zona explícita. Mantener ambos timestamps y offset. | Brian valida interpretación del dato fuente; Christian implementa la transformación. |
| Tamaño ResStock | Mantener el piloto actual de 10 perfiles como alcance exploratorio del primer tablero. No afirmar representatividad ni escalar antes de cerrar calidad, disponibilidad, costo y alcance. Una ampliación posterior requiere una nueva versión de muestra y manifiesto. | Brian confirma si existe una ampliación aprobada; la recomendación por defecto es no bloquear el tablero inicial. |
| S3 y caché | `gold/v1/` privado; exportaciones web en `site/data/v1/`; JSON inmutable con caché de un año y manifiesto sin caché, con invalidación del manifiesto al publicar. | Omar confirma la implementación al preparar la distribución CloudFront. |

Estas recomendaciones son valores por defecto para revisión. Hasta que las personas indicadas las confirmen en el PR, el tablero debe tratar el documento como propuesta y no como contrato aprobado.
