# Tablero (primera versión)

Frontend estático sin dependencias ni paso de compilación (HTML + ES modules + SVG). Seis vistas: Resumen, Patrones, Clima, Anomalías, Estimaciones y Flujo/Calidad, según `docs/especificacion-tablero.md`.

## Ejecutar

```bash
python3 -m http.server 8000 -d tablero
# abrir http://localhost:8000/  (usar localhost/HTTPS: la verificación SHA-256 requiere contexto seguro)
```

## Datos

Lee solo JSON versionados bajo `tablero/data/v1/` (cambiar con `?data=<url-base>/`):
`manifest.json`, `gold_eia_monthly`, `gold_resstock_monthly`, `gold_resstock_pattern`, `gold_resstock_pattern_aggregate`, `gold_resstock_profile_summary`, `gold_climate`.

Para regenerar las tablas desde `datos/`, instala las dependencias del exportador y ejecuta el comando seguro documentado en [`docs/ejecucion-job-spark-local.md`](../docs/ejecucion-job-spark-local.md). La interfaz en sí no requiere paquetes, compilación ni conexión externa.

- Cada tabla es un arreglo de filas (o `{"rows": [...]}`) con las columnas en inglés `snake_case` de `docs/contrato-gold-propuesta.md` (columnas obligatorias en `js/config.js`). No hay alias.
- `manifest.json`: `schema_version` = `1.0` y `tables` (arreglo u objeto) con `file`, `rows`, `bytes`, `sha256`. Se verifican filas, bytes y SHA-256; una tabla que no coincide se rechaza con mensaje de error.
- Con manifiesto presente solo se piden las tablas listadas; las demás aparecen como "esperando datos". Sin manifiesto se intentan leer las tablas sin validarlas (aviso visible).
- `gold_climate` usa `point_id, state_code, timestamp_utc, temperature_c, model` (§7 de la especificación).

## Estado

| Vista | Estado |
|---|---|
| Resumen, Patrones (P1, P1b, P2, P3), Clima (C1, C2), Flujo/Calidad (Q1, Q2) | Funcionan con las tablas anteriores |
| R2 | Solo cobertura; la razón ResStock/EIA (87.16 %) no se publica sin evidencia reproducible |
| Anomalías, Estimaciones, Q3, Q4 | Esperan salidas de datos; sin cifras de relleno |

Filtros sin campo en la fuente se deshabilitan con explicación. Respeta `prefers-reduced-motion`.
