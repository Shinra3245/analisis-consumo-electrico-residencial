# Método de estimación mensual y anual (EIA residencial)

**Responsable:** Diego · **Revisión pendiente:** Brian (años y definición de la serie)
**Código:** [`analitica/pronostico_eia.py`](../analitica/pronostico_eia.py) · **Salidas:** `gold_forecast_*`, `gold_eia_monthly`
**Estado:** resultados reproducibles sobre los datos integrados en `datos/`. Evaluación con una sola partición temporal.

## 1. Qué se estima

Ventas residenciales mensuales por estado (MWh) de EIA-861M, 50 estados y DC. Es una serie **oficial agregada**, no consumo medido de hogares ni los perfiles ResStock. Los perfiles ResStock 2018 se tratan aparte como perfil/escenario.

## 2. Datos y partición temporal

Los 51 territorios tienen los 96 meses de 2018–2025 como `Final`; 2026 trae ene–ago como `Preliminary`.

| Ventana | Ajuste con | Horizonte | Contra qué se compara | ¿Cuenta en métricas titulares? |
|---|---|---|---|---|
| `backtest` | 2018-01…2023-12 | 2024-01…2025-12 | Datos `Final` | **Sí** |
| `preliminary_check` | 2018-01…2023-12 | 2026-01…2026-08 | Datos `Preliminary` | No (el dato puede cambiar) |
| `forward` | 2018-01…2025-12 | 2026-09…2027-12 | Nada (no hay dato real) | No: es un **escenario** |

La partición es siempre cronológica; no se mezclan meses al azar.

## 3. Modelos

| `model_id` | Qué hace |
|---|---|
| `seasonal_naive` | Repite el valor del mismo mes del último año de entrenamiento |
| `seasonal_mean` | Promedio histórico del mismo mes (sin tendencia) |
| `log_linear_trend` | `log(y) = a + b·t + efecto del mes`, por mínimos cuadrados, con corrección de sesgo (Duan) al regresar a MWh |

Los dos primeros son el baseline estacional; el tercero es el modelo sencillo. Cada estado se ajusta por separado. No se usa clima, ni variables exógenas, ni intervalos de predicción.

## 4. Métricas

MAE y RMSE en MWh; sMAPE en %. Se calculan por estado y para la suma mensual de las 51 jurisdicciones (`scope = all_51`). Un mes se marca no interpretable si `|real| + |pronóstico| < 1 MWh`; en esta corrida hubo **0** casos.

## 5. Resultados (corrida del 17 de noviembre de 2026)

**Suma de 51 jurisdicciones, backtest 2024–2025:**

| Modelo | MAE (MWh) | RMSE (MWh) | sMAPE |
|---|---:|---:|---:|
| `seasonal_naive` | 7,107,744 | 8,944,312 | 5.63 % |
| `seasonal_mean` | 4,721,103 | 6,149,162 | 3.67 % |
| `log_linear_trend` | 4,456,189 | 5,756,822 | 3.47 % |

**Por estado (backtest), sMAPE:**

| Modelo | Media | Mediana | Mín | Máx |
|---|---:|---:|---:|---:|
| `seasonal_naive` | 7.20 % | 7.05 % | 3.48 % | 11.88 % |
| `seasonal_mean` | 5.51 % | 5.35 % | 2.16 % | 11.06 % |
| `log_linear_trend` | 5.77 % | 5.71 % | 3.02 % | 8.74 % |

Menor sMAPE por estado: `seasonal_mean` en 34, `log_linear_trend` en 16, `seasonal_naive` en 1.

**Comprobación preliminar (ene–ago 2026, suma 51):** sMAPE 6.70 % (naive), 5.06 % (media estacional), 4.13 % (log-lineal). Es una referencia, no una métrica validada.

## 6. Cómo leer los resultados

- En la **suma nacional** el modelo log-lineal es el mejor, pero **por estado** no domina: gana en 16 de 51. El error del total es menor que el error típico por estado porque los errores se compensan parcialmente.
- La tendencia ayuda cuando el consumo crece de forma estable y perjudica cuando la serie se aplana; por eso `seasonal_mean` gana en muchos estados.
- No se debe afirmar que "el modelo predice con 3.5 % de error": eso es solo la suma de las 51 jurisdicciones en una ventana de 24 meses.

## 7. Límites

1. **Una sola partición** (24 meses de prueba). No hay validación con origen móvil; la estabilidad del ranking de modelos no está comprobada.
2. **Historia corta:** 6 años de ajuste, que incluyen 2020, un periodo atípico. No se trató de forma especial.
3. **Sin clima ni variables explicativas.** Un año muy frío o caluroso no se anticipa.
4. **Los meses de 2026 son preliminares** y pueden revisarse.
5. **`forward` es un escenario**: extrapola la tendencia hasta 24 meses después del último mes de ajuste (se muestran sep 2026–dic 2027), sin dato real y sin intervalos de predicción.
6. **Pronóstico diario no se ofrece:** no hay serie diaria que lo sostenga.
7. EIA mide ventas a clientes residenciales, que no equivalen a consumo medido de los hogares.

## 8. Reproducir

```bash
python -m pip install -r analitica/requirements.txt
python analitica/pronostico_eia.py
```
Con los mismos datos de entrada, las salidas son idénticas byte a byte (comprobado con `cmp` entre dos ejecuciones).
