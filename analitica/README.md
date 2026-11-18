# Analítica: pronóstico, anomalías y salidas gold

Scripts que producen las tablas gold que consumirá el tablero. Descripción de columnas: [`docs/contrato-gold-propuesta.md`](../docs/contrato-gold-propuesta.md). Métodos y límites: [`docs/metodo-pronostico.md`](../docs/metodo-pronostico.md) y [`docs/metodo-anomalias.md`](../docs/metodo-anomalias.md).

## Ejecutar (desde la raíz del repositorio)

```bash
python -m pip install -r analitica/requirements.txt
python analitica/pronostico_eia.py
python analitica/anomalias_resstock.py
python analitica/generar_manifiesto.py
```

Orden obligatorio: el manifiesto se genera al final. Cada script acepta `--root <ruta>` si lo ejecutas fuera de la raíz.

## Qué debes ver

| Script | Resultado esperado en consola |
|---|---|
| `pronostico_eia.py` | 51 estados; sMAPE suma 51 en backtest: 5.63 / 3.67 / 3.47 % (naive / media estacional / log-lineal) |
| `anomalias_resstock.py` | `z_up = 19`, `ratio_down = 0.20`; evaluación CO: caída F1 0.664, aumento F1 0.154, faltante 1.000 |
| `generar_manifiesto.py` | 11 archivos, avisos: ninguno |

Si tus números difieren, revisa la versión de pandas/pyarrow y que `datos/` no haya cambiado. El manifiesto avisa si el hash de una entrada no coincide con `datos/manifiesto-integracion.json`.

## Salidas (`analitica/salidas/`)

11 CSV `gold_*` + `manifiesto-gold.json`. Son **derivadas y deterministas**: mismas entradas, mismos bytes (semilla fija `20261117`). Conservan atribución: EIA-861M (EIA) y ResStock 2025 R1 (NREL/DOE, CC BY 4.0); las anomalías usan eventos sintéticos.

## Línea sugerida para `.gitattributes`

Para que Git no cambie los saltos de línea y los hashes del manifiesto sigan válidos:

```
analitica/salidas/** -text
```

## Flujo de rama y PR

1. Rama de trabajo: `analitica/tablero`.
2. PR 1 — solo documentos (`docs/especificacion-tablero.md`, `docs/contrato-gold-propuesta.md`): para revisión de Brian, Christian y Omar.
3. PR 2 — scripts, `salidas/` y documentos de método.
4. En cada PR: comando para repetir, resultado observado y quién revisa (Definition of Done del plan).
