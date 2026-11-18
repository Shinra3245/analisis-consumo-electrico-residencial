# Método de detección de anomalías (perfiles ResStock)

**Responsable:** Diego · **Revisión pendiente:** Christian (etiquetas y protocolo) y Brian (significado de los perfiles)
**Código:** [`analitica/anomalias_resstock.py`](../analitica/anomalias_resstock.py) · **Salidas:** `gold_anomaly_*`, `gold_resstock_*`
**Estado:** resultados reproducibles sobre 10 perfiles. Los eventos son **sintéticos**; las métricas solo valen contra esas etiquetas.

## 1. Unidad de análisis y definición de "atípico" (escrita antes de elegir parámetros)

- **Unidad:** un perfil ResStock modelado (`bldg_id`), agregado por **hora** (suma de 4 intervalos de 15 min). El piloto tiene 10 perfiles × 8,760 horas.
- **Atípico:** una hora cuyo consumo se aleja de lo normal para ese mismo perfil en horas comparables: mismo **mes**, mismo **tipo de día** (laboral o fin de semana) y misma **hora**.
- **Línea base:** mediana de esa celda. Con un solo año hay entre 8 y 23 observaciones por celda.
- Las horas son EST fijo; no se convirtieron a hora local. No se modelan festivos.

## 2. Tres categorías, tres reglas

| Categoría | Regla | Por qué |
|---|---|---|
| `aumento` | score robusto `(x − mediana) / max(1.4826·MAD, piso) ≥ z_up` | Los aumentos no tienen techo |
| `caida` | `x ≤ ratio_down × mediana` y mediana ≥ mediana horaria del perfil | Una caída está acotada por 0; un score simétrico casi nunca la alcanzaría. Se excluyen horas donde lo normal ya es casi nulo |
| `faltante` | valor ausente | Regla determinista, no estadística |

Aumentos y caídas exigen **al menos 2 horas consecutivas** (`min_run_hours = 2`) para alertar. Las alertas son tramos continuos de horas con la misma categoría.

## 3. Protocolo de evaluación

1. Se hace una **copia** de las horas originales; los originales no se modifican.
2. En la copia se inyectan, por perfil y sin traslape (margen de 24 h): **8 aumentos** (3–6 h), **8 caídas** (6–12 h) y **4 faltantes** (6–24 h), con semilla fija. Aumento: se suma 0.5, 1.0 o 2.0 veces el percentil 95 horario del perfil. Caída: se elimina 50, 75 o 95 % del consumo.
3. Los perfiles se separan por estado: **calibración = NY** (5 perfiles, se eligen `z_up` y `ratio_down`) y **evaluación = CO** (5 perfiles, solo se mide).
4. Precision, recall y F1 se calculan a **nivel de evento**: un evento se detecta si alguna alerta de su misma categoría lo toca; una alerta es verdadera si toca un evento de su misma categoría.
5. La línea base se ajusta sobre la copia ya inyectada (como ocurriría con datos reales que traen sus propias anomalías); la mediana y el MAD limitan la influencia.

Parámetros elegidos en calibración (NY): `z_up = 19`, `ratio_down = 0.20`, `min_run_hours = 2`.

## 4. Resultados (corrida del 17 de noviembre de 2026)

**Evaluación (CO, 5 perfiles), etiquetas sintéticas:**

| Categoría | Eventos | Detectados | Recall | Alertas | Precision | F1 |
|---|---:|---:|---:|---:|---:|---:|
| `aumento` | 40 | 6 | 0.150 | 38 | 0.158 | 0.154 |
| `caida` | 40 | 24 | 0.600 | 35 | 0.743 | 0.664 |
| `faltante` | 20 | 20 | 1.000 | 20 | 1.000 | 1.000 |

**Calibración (NY, 5 perfiles):** `aumento` F1 0.384 (recall 0.600, precision 0.282) · `caida` F1 0.710 (recall 0.550, precision 1.000) · `faltante` 1.000.

**Recall por magnitud (evaluación):** aumentos 0.06 (bajo), 0.13 (medio), 0.38 (alto); caídas 0.10 (50 %), 0.36 (75 %), 1.00 (95 %).

**Sensibilidad a la duración mínima (evaluación):**

| `min_run_hours` | Aumento: recall / precision | Caída: recall / precision |
|---:|---|---|
| 1 | 0.200 / 0.065 | 0.675 / 0.541 |
| 2 | 0.150 / 0.158 | 0.600 / 0.743 |
| 3 | 0.150 / 0.600 | 0.525 / 0.957 |

## 5. Conclusiones que sí se sostienen

- **Faltantes:** se detectan siempre, pero por una regla trivial; el resultado no mide un método estadístico.
- **Caídas:** el método funciona razonablemente (F1 0.66) cuando la caída es profunda; las caídas de 50 % casi no se detectan (recall 0.10), algo esperable: su razón vs línea base ronda 0.5 y la regla exige ≤ 0.20.
- **Aumentos:** **el método no está validado.** Recall 0.15 y precision 0.16 en CO. El umbral calibrado en NY no generaliza a CO.

## 6. Por qué los aumentos fallan y qué se hizo al respecto

Los perfiles modelados varían mucho de un día a otro por el clima (calefacción, enfriamiento). Una hora fría legítima produce un aumento fuerte respecto a la mediana del mes, y el método no puede distinguirlo de un evento anómalo porque **no incorpora clima**. La unión climática sigue bloqueada (clima disponible: 2 puntos, 7 días).

Transparencia sobre la calibración: una primera rejilla de `z_up` llegaba hasta 10; el óptimo quedaba en el borde, por lo que se amplió a 20 (solo con datos de NY). Con la rejilla corta, el recall de aumentos en CO era mayor (0.45, F1 0.24); con la ampliada baja a 0.15. Es decir, **la calibración del umbral de aumentos es inestable** con 5 perfiles. No se eligió el resultado con mejor aspecto en evaluación.

## 7. Casos para el tablero

`gold_anomaly_cases` trae 5: aumento detectado, caída detectada, faltante detectado, un aumento **no detectado** (magnitud baja) y una **alerta sin etiqueta** (caída en horas sin evento inyectado; su causa no se investigó y no es un evento confirmado). Cada caso lleva observado, referencia, diferencia, métrica disparadora y regla.

## 8. Límites

1. **10 perfiles, un año**, de dos estados. No es un estimador nacional ni representa el parque residencial.
2. **Eventos sintéticos creados por nosotros:** la dificultad depende de cómo se inyectaron (magnitudes, duraciones). Las métricas no se extrapolan a eventos reales.
3. `min_run_hours = 2` se eligió tras explorar 1–3 sobre la calibración; con 3 horas la precision de aumentos sube a 0.60 pero el recall no mejora.
4. Calibración con 5 perfiles de un solo estado: el ajuste es frágil.
5. La línea base de un solo año no distingue estacionalidad de anomalía a escala de meses.
6. Sin festivos ni conversión a hora local.

## 9. Siguiente mejora sugerida

Cuando exista una unión climática válida, condicionar la línea base de aumentos a la temperatura (p. ej., regresión robusta por perfil) y recalibrar con más perfiles y más estados. Hasta entonces, los aumentos se muestran como método no validado.

## 10. Reproducir

```bash
python -m pip install -r analitica/requirements.txt
python analitica/anomalias_resstock.py
```
Determinista: la semilla es fija (`20261117`) y las salidas son idénticas entre ejecuciones.
