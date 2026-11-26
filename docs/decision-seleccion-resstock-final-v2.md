# Decisión: selección analítica final v2 de 10,000 perfiles ResStock

**Estado: `raw_validated_s3_pending_spark` (26-nov-2026).** Una adenda de verificación confirmó 10,000 Parquets únicos aceptados en la clave canónica de S3 que espera el procesador (9,998 primarios + los reemplazos 432862 WI y 491767 CT), 35,040 filas por perfil, SHA-256/checksum, `ContentLength` y relectura exactos, y 25 manifiestos de ingesta. Los rechazados originales 294772 y 481740 quedaron aislados y excluidos. **El job Spark, el QC de 21 reglas y los Silver/Gold de la selección v2 NO se han ejecutado a escala 10,000: no se afirma 10,000 procesados ni publicado.** La selección v1 (`datos/resstock_seleccion_propuesta.csv`, SHA-256 `caaf96067883d6a7c2b79010647614e66bd631f6d30aab38190015a4a2a8f826`) y el diario de ingesta original se conservan íntegros, incluidos los dos rechazados.

## Motivo

Dos perfiles de v1 fueron rechazados de forma permanente por energía negativa en la validación por perfil: **294772** (WI, Single-Family Detached, condado G5500350) y **481740** (CT, Multi-Family with 2 - 4 Units, condado G0900030). Un rechazado no cuenta como aceptado; para llegar a 10,000 perfiles *válidos* se sustituyen en el mismo índice por IDs del mismo estrato, sin borrar ni reescribir el historial (el diario original conserva los dos rechazos).

## Derivación reproducible

1. Metadata oficial: `metadata_and_annual_results/national/full/parquet/upgrade0.parquet` del release `resstock_amy2018_release_1` — ETag multipart `dcaa5c1d994a279be79d1dbc061e078d-9`, version-id `hCkLSyMEL7M9_swgWRQhzTkqdRK2HS6d`, Last-Modified 2025-10-21T12:24:44Z, 465,060,991 bytes, 549,971 filas; lectura por rangos con `If-Match` (2,486,799 bytes), sin descargar series en esa derivación (los Parquet de los perfiles se validaron después; ver la sección de evidencia). Con él se reprodujo exactamente v1 (254 estratos, `allocate_profiles`, `random.Random(22030511)`), con condado y peso idénticos en las 10,000 filas.
2. Elegibles: `completed_status == "Success"`, tipo declarado, `weight > 0`, mismo `in.state` y tipo, no presentes en v1.
3. **Conservación del rango (variante B):** `order_selection` ordena cada estrato por `SHA-256("22030511:<id>")`. Solo se aceptan candidatos que, al ocupar el lugar del rechazado, conservan su rango dentro del estrato (42 de 129 en WI; 8 de 19 en CT), de modo que el orden estable global queda idéntico a v1 con el ID sustituido en la misma posición. Entre ellos, orden ascendente por `SHA-256("22030511:reemplazo:<id_rechazado>:<id_candidato>")`.
4. Condado y peso salen del metadata de cada candidato (no se copian del rechazado). Todas las filas conservan `upgrade=0` y el patrón de URL del release.
5. Reemplazo en el mismo índice del CSV; el resto es idéntico byte a byte (2 líneas distintas de 10,001, 2,812,952 bytes, CRLF).

| Índice CSV (0-based) | Posición en orden estable | Rechazado | Reemplazo B |
|---|---|---|---|
| 9812 | 3366 | 294772 (WI SFD) | **432862**, G5501250, peso 253.90367272727272 |
| 1717 | 4332 | 481740 (CT MF 2-4) | **491767**, G0900030, peso 253.90367272727272 |

### Respaldos que preservan la misma posición (constancia; no se usaron)

| Reemplaza | 1.º respaldo | 2.º | 3.º |
|---|---|---|---|
| 294772 (WI) | 377244 (G5500130) | 62469 (G5500310) | 142341 (G5500490) |
| 481740 (CT) | 385601 (G0900010) | 350478 (G0900030) | 314467 (G0900030) |

(Ya no se necesitan: los titulares fueron aceptados; se conservan como constancia.) Todos con peso 253.90367272727272, HEAD 200 sobre su serie (tamaños y ETag en `respaldos-B.json`) y, simulado, orden estable idéntico al de v1 con el intercambio. Cambiar de candidato obliga a regenerar CSV y manifiesto (nuevos hashes) y a registrar el motivo del rechazo del anterior. No se usan candidatos de la variante A (373376, 291954): alteran 65 posiciones.

## Archivos y hashes (precalculados; recalcular al materializar)

Carpeta nueva `datos/releases/resstock-seleccion-final-v2/` (no toca los archivos v1): `resstock_seleccion_propuesta.csv` (2,812,952 bytes), `manifiesto-integracion.json` (copia del v1 con el artefacto de selección actualizado: bytes, filas, SHA-256, `transform` y `derived_from` con SHA-256 de v1, reemplazos, metadata y `validation_status: raw_validated_s3_pending_spark` (con bloque `raw_validation` y `downstream.spark_qc_gold_ejecutado: false`); claves `release_id` y `supersedes_manifest_sha256`), y copias regulares, idénticas a v1, de `eia_residencial_mensual.csv` y `clima_open_meteo_muestra.csv`.

| Archivo | SHA-256 |
|---|---|
| `resstock_seleccion_propuesta.csv` | `247394923fd54ad52528a4913e53bec4e330e26f0734bf0a15cea3f67482199d` |
| `manifiesto-integracion.json` | `bbbfea0863323b2deb4f77730d321725c67ea3583266d447032b331a9f860117` |

## Contrastes locales ya hechos (sin red salvo metadata y HEAD)

- 10,000 filas, 10,000 IDs únicos, 254 estratos con multiconjunto idéntico a v1, URLs válidas (`load_selection`); 294772 y 481740 ausentes, 432862 y 491767 presentes.
- Orden estable: secuencia idéntica a v1 salvo las dos posiciones sustituidas. Ventanas del procesador: de 50 lotes de 200, solo difieren `b00016` (inicio 3200) y `b00021` (inicio 4200); con lotes de 25, solo `b00134` (3350) y `b00173` (4325). La ventana 2750..2774 es idéntica a v1.
- El modo plan de `procesar_resstock_s3_lotes.py --datos <release>` y `check_base` del adaptador aceptan el release.

## Uso (raw validado; Spark pendiente)

- Procesamiento: `--datos datos/releases/resstock-seleccion-final-v2`. La prueba real de 5 perfiles se ejecutó con la selección v1, SHA-256 `caaf96067883d6a7c2b79010647614e66bd631f6d30aab38190015a4a2a8f826`, offset 0, tamaño 5 (`b00000`) y el release raw por defecto `resstock_amy2018_release_1`. Su marca existe en `gold/resstock/scale10k/resstock_amy2018_release_1/_commit/b00000.json`, `run_id=20261126T122106Z-0130e0a5`; no es un release de prueba independiente. Por seguridad, no se modifica ni elimina esa marca. El procesador actualizado mantiene ese release para leer raw, pero toma `release_id=resstock-seleccion-final-v2` del manifiesto como namespace separado de salida Silver/Gold/commit. Así, la ventana v2 `b00000` no colisiona con el commit piloto v1. La prueba publicó cuatro objetos derivados y una marca adicional; no valida perfiles v2.
- Ingesta: los reemplazos B (432862 WI y 491767 CT) ya están colocados en la clave canónica `raw/resstock/scale10k/<release>/<id>.parquet`, con checksum, `ContentLength` y relectura exactos según la adenda de Antigravity del 26-nov-2026; no requieren ingesta adicional ni CSV suplementario. Los rechazados 294772 y 481740 siguen aislados en el diario original (que se conserva íntegro) y excluidos de v2. Raws sobrantes (p. ej. de la variante A) quedan en S3 y no cuentan: la reconciliación es por roster, no por conteo de objetos.
- Estado raw v2: validado según la adenda del 26-nov-2026, con reconciliación 10,000/10,000 contra el roster v2. Alcance de la afirmación: consta por reporte de Antigravity; este documento no incluye una lista de HEAD individual por ID ni se repitió aquí la verificación (sin AWS).
- Cierre de 10,000 *procesados*: pendiente. Spark, QC de 21 reglas y Silver/Gold v2 NO se han ejecutado. Falta ejecutar Spark/QC lote por lote con `--datos datos/releases/resstock-seleccion-final-v2`, las marcas `_commit`, la consolidación global (350,400,000 filas) y el QC global.

Atribución: *Data includes information from the ResStock™ dataset developed by the National Renewable Energy Laboratory (NREL) with funding from the U.S. Department of Energy (DOE).* CC BY 4.0, «as is». Ver [decisión de publicación](decision-publicacion-datos.md).

## Evidencia de validación raw (adenda, 26-nov-2026)

| Aspecto | Resultado |
|---|---|
| Perfiles únicos aceptados en la clave canónica | 10,000 (9,998 primarios + 432862 + 491767) |
| Filas por perfil | 35,040 |
| Verificación | SHA-256/checksum, `ContentLength` y relectura exacta |
| Manifiestos de ingesta | 25 |
| Rechazados históricos aislados | 294772 (WI SFD) y 481740 (CT MF 2-4), energía negativa; excluidos de la selección v2 y del conteo |
| Spark / QC 21 reglas / Silver / Gold sobre v2 | **No ejecutados** |

Esta evidencia proviene de la adenda de Antigravity y no se repitió aquí (sin AWS). No incluye bucket, cuenta, ARN, credenciales ni URLs firmadas.

**Gate de `apply.sh`:** exige `CONFIRMO_RAW_VALIDADO_S3=10000`, es decir, solo la validación raw; aplicar los archivos no implica procesamiento.
