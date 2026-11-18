# Analítica de anomalías y pronóstico (EIA mensual)

Bloque reproducible: `scripts/analitica_anomalias_pronostico.py`. Lee `datos/eia_residencial_mensual.csv` (y, solo para describir, `data/raw/up00-co-single-family_detached.csv`) sin modificarlos y escribe en `/tmp/analitica_anomalias_pronostico` por defecto. No usa AWS.

```bash
python3 scripts/analitica_anomalias_pronostico.py [--salida DIR] [--k-mad 3.5] [--meses-prueba 24] [--meses-min-entrenamiento 48] [--semilla 42]
```
Dependencias: pandas y numpy. Se rechaza una salida dentro de `datos/`, `data/` o `docs/`.

## Datos inspeccionados
- EIA: 5 304 filas = 51 estados × 104 meses (2018-01 a 2026-08), sin nulos ni duplicados. `Final` hasta 2025-12 (96 meses); 2026-01 a 2026-08 son `Preliminar` y se excluyen del ajuste y la evaluación (solo se puntúan aparte, informativo).
- ResStock piloto: 35 040 filas a 15 min, 2018, un solo estrato (Colorado, unifamiliar aislada; el archivo es local y puede no existir en otras ramas: el script lo omite). Solo descripción (total 16 809 653 MWh; pico en 2018-01 con 1 811 955 MWh). No se usa para anomalías ni forecast: un año no permite baseline temporal.

## Definición de anomalía
Para cada estado se calcula el cambio logarítmico interanual `log(y_t) − log(y_{t−12})` (compara el mismo mes y elimina estacionalidad). Para cada estado × estación (DEF, MAM, JJA, SON) se estiman mediana y MAD escalado (×1,4826, piso 0,01) **solo con el entrenamiento** (2019-2023, ~15 valores por grupo). Un mes es *candidato estadístico* si queda fuera de `mediana ± k·MAD` (k = 3,5). Interpretación: «ese mes varió respecto al año previo mucho más de lo habitual para ese estado en esa estación». Un candidato **no** es una anomalía real confirmada (puede ser clima, cambios de reporte o revisión de datos); no se contrastó con eventos reales.

## Evaluación (solo sintética, etiquetada `SINTETICO`)
En todo el periodo de prueba (2024-01…2025-12) se inyectan 3 alteraciones multiplicativas (±m, signo aleatorio) por estado (153 por magnitud), semilla 42; el YoY de 2024 usa 2023 como referencia. Los meses t+12 de una inyección (efecto de arrastre en el interanual) se excluyen del conteo de falsos positivos.

| magnitud | recall | precisión | tasa FP |
|---|---|---|---|
| ±10 % | 0,05 | 0,39 | 0,011 |
| ±20 % | 0,26 | 0,78 | 0,011 |
| ±30 % | 0,58 | 0,90 | 0,010 |
| ±50 % | 0,94 | 0,93 | 0,011 |

Lectura: el detector es conservador; solo detecta con fiabilidad desvíos ≳30 %. Estas cifras valen para este tipo de inyección, no para anomalías reales.

## Candidatos sobre datos reales (sin afirmar anomalías)
De 4 284 puntuaciones: 31 candidatos en entrenamiento, 12 en prueba, 3 de 408 en 2026 preliminar. Los de mayor |z| (p. ej. NV y AZ en 2020-05, z≈8,9 y 7,0) están en `candidatos_estadisticos.csv` para revisión humana.

## Pronóstico
Holdout temporal: entrenamiento 2018-01…2023-12 (72 meses), prueba 2024-01…2025-12 (24 meses), horizonte hasta 24 meses sin reajuste. Modelos por estado, ajustados solo con entrenamiento:
- **Baseline ingenua estacional**: repite el último ciclo anual de entrenamiento.
- **Modelo**: regresión log-lineal con dummies de mes + tendencia lineal, con corrección de retransformación.

Métricas MAE, RMSE y sMAPE por estado en `forecast_metricas_por_estado.csv`.

**Serie para la vista Estimaciones:** `forecast_serie.csv` (columnas `estado,period,real_mwh,naive_mwh,modelo_mwh,particion`) con 1 224 filas (51 estados × 24 meses, 2024-01…2025-12, ≈63 KB), generada con el mismo ajuste sin fuga. Es un **backtest** sobre el holdout (`particion = holdout`), **no una proyección futura**: no contiene meses posteriores a 2025-12 ni usa los meses preliminares de 2026. El resumen (`resumen.json`, `forecast.forecast_serie`) registra filas, estados y periodos. Dos corridas dieron el mismo SHA-256 (`bd3aaaf9…dd70`). Medianas entre 51 estados:

| | sMAPE % | RMSE (MWh) |
|---|---|---|
| Naive estacional | 7,05 | 145 476 |
| Log-lineal + mes | 5,71 | 117 331 |

El modelo supera a la naive en sMAPE en 46 de 51 estados. Regla de suficiencia: si el entrenamiento tiene menos de `--meses-min-entrenamiento` (48) meses el script reporta insuficiencia en lugar de métricas; aquí se cumple.

## Limitaciones y no verificado
- Un solo split (24 meses) y solo 6 años de entrenamiento: sin validación de origen móvil ni intervalos de predicción; la tendencia lineal puede extrapolar mal más allá de 2025.
- 2020 (COVID) está en el entrenamiento y puede inflar o sesgar límites y tendencia.
- Ajuste por estado sin clima ni calendario; los datos Open-Meteo no se usan.
- Los candidatos no se validaron contra eventos externos; la detección solo se evaluó con inyecciones sintéticas.
- El pronóstico de 2026 preliminar no se evaluó.
- ResStock es un solo año/estrato; no es comparable como serie temporal con EIA (ver `datos/demo_colorado_2018_verificacion.csv` para la comparación descriptiva existente).
