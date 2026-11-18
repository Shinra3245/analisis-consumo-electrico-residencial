# Propuesta de contrato gold — capa de consumo para el tablero

**Responsable:** Diego · **Para revisión de:** Christian (esquema y Spark) y Omar (rutas S3 y publicación)
**Estado:** propuesta. Las tablas de este documento **ya se generan** con `analitica/*.py` a partir de los datos integrados en `datos/`. No implica que Spark/EMR las produzca todavía: cuando Christian entregue el gold real, debe respetar estas columnas o acordar cambios aquí.
**Relación con el [contrato v1](contrato-datos-v1.md):** el v1 define silver y trazabilidad; este define las agregaciones gold que consume el tablero (punto 4 de su sección 6).

## 1. Convenciones

| Tema | Regla |
|---|---|
| Formato | CSV UTF-8, coma, encabezado, saltos de línea `\n`, punto decimal |
| Nombres de columna | Inglés `snake_case`, igual que las tablas silver del contrato v1 |
| Periodos | `YYYY-MM` para meses (no se convierten en horas) |
| Timestamps ResStock | `*_est` = EST fijo (UTC−5), sin horario de verano, sin zona en el texto. No convertidos a hora local |
| Unidades | MWh para EIA y pronósticos; kWh para perfiles ResStock; °C para clima |
| Fuentes | ResStock, EIA y clima **no se fusionan** en una misma fila |
| Datos preliminares | Se conservan como `Preliminary`; nunca se rotulan `Final` |
| Eventos sintéticos | Toda tabla de anomalías lleva `is_synthetic*` explícito |
| Versión | `schema_version` = `1.0` en `manifiesto-gold.json` |
| Hash/linaje | `manifiesto-gold.json` lista filas, bytes, SHA-256 y los hashes de las entradas en `datos/` |

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
`bldg_id, annual_kwh, mean_hour_kwh, peak_hour_kwh, n_hours, state_code, housing_type, profile_weight`. `n_hours` = 8,760 por perfil. `profile_weight` es idéntico en los 10: no usar como estimador.

### 2.6 `gold_resstock_monthly`
PK `(bldg_id, month)` · 120 filas. `bldg_id, month, kwh_month, state_code, housing_type`. El mes se asigna por el **inicio** del intervalo.

### 2.7 `gold_resstock_pattern`
PK `(bldg_id, month, day_type, hour)` · 5,760 filas.
`bldg_id, month, day_type (weekday|weekend), hour (0-23 EST), median_kwh, mean_kwh, p10_kwh, p90_kwh, n_obs, state_code, housing_type`. Calculada sobre los datos **originales**.

### 2.8 Anomalías (etiquetas sintéticas)

**`gold_anomaly_metrics`** — PK `(eval_set, category, magnitude)`: `eval_set` (`calibration`=NY, `evaluation`=CO), `category` (`aumento`, `caida`, `faltante`, `aumento+caida`), `magnitude` (`all`, `low`, `mid`, `high`), `n_events, n_detected, recall, n_alerts, n_true_alerts, precision, f1`, parámetros usados (`z_up, ratio_down, min_run_hours`), `method`, `is_synthetic_labels`. Por magnitud solo hay `recall`.

**`gold_anomaly_sensitivity`** — `min_run_hours, category, n_events, n_detected, recall, n_alerts, n_true_alerts, precision, f1` (evaluación).

**`gold_anomaly_cases`** — PK `case_id`: `case_id, kind` (`synthetic_detected`, `synthetic_missed`, `unlabeled_alert`), `outcome, bldg_id, state_code, housing_type, category, magnitude, start_est, end_est, n_hours, observed_kwh, baseline_kwh, diff_kwh, trigger_metric, trigger_value, rule, is_synthetic`.

**`gold_anomaly_case_series`** — PK `(case_id, timestamp_start_est)`: `observed_kwh, original_kwh, baseline_kwh, score, ratio_to_baseline, alert` (`aumento`/`caida`/`faltante`/vacío). `original_kwh` es el valor antes de inyectar.

## 3. Tablas de otros integrantes (interinas, sin cambios por analítica)

| Necesidad del tablero | Fuente interina hoy | Propietario del gold final | Pendiente |
|---|---|---|---|
| Comparación ResStock/EIA Colorado 2018 (R2) | `datos/demo_colorado_2018_verificacion.csv` | Christian + Brian | Recalcular desde el agregado crudo (hoy sin verificación independiente) |
| Cobertura EIA (Q1) | `datos/cobertura_eia.csv` | Brian | Decidir si se renombra a inglés |
| Clima (C1) | `datos/clima_open_meteo_muestra.csv` | Brian + Christian | Regla de unión geográfica y de huso horario |
| Estado de pipeline/replay (Q3) y controles de calidad (Q4) | No existe | Christian + Omar | `quality_status`, `quality_flags`, `replay_id`, `ingested_at_utc` |

## 4. Prefijos de salida (propuesta para Omar)

```
s3://<bucket>/gold/v1/<tabla>.csv
s3://<bucket>/gold/v1/manifiesto-gold.json
```
El tablero lee **solo** `gold/v1/`. Cambiar de `analitica/salidas/` local a S3 no debe modificar el tablero, solo la URL base.

## 5. Decisiones que necesito del equipo

| # | Decisión | Con quién |
|---|---|---|
| 1 | ¿Nombres de columna en inglés (propuesto) o español? | Christian, Brian |
| 2 | ¿CSV (propuesto, simple para un sitio estático) o Parquet/JSON en el gold final? | Christian, Omar |
| 3 | Regla de conversión EST → hora local para mostrar horas del día | Brian, Christian |
| 4 | ¿Se amplía el piloto de ResStock más allá de 10 perfiles? | Brian |
| 5 | Prefijo y versión de S3, y política de caché al publicar | Omar |
