# Procesamiento ResStock por lotes desde S3 privado (sin EMR)

`scripts/procesar_resstock_s3_lotes.py` toma los perfiles que `scripts/ingesta_resstock_a_s3_privado.py` dejó en `raw/resstock/scale10k/<release>/` y, en ventanas de **como máximo 200 perfiles**, ejecuta el job Spark existente (`local[*]` dentro de CloudShell, sin EMR, que Learner Lab deniega) y publica Silver/Gold por lote bajo prefijos nuevos. No modifica el adaptador, `preparar_entrada_spark.py`, el job, `generar_datos_tablero.py`, los contratos, Gold v2 ni el dashboard; solo los invoca.

**Estado (26-nov-2026):** la ingesta raw v2 de 10,000 perfiles está completa en S3 privado. Además, se ejecutó un lote real de prueba de **5 perfiles** desde S3 con Spark 4.0.1 en CloudShell: 175,200 filas Silver, 60 filas Gold mensual, 21/21 reglas QC aprobadas, 4 objetos derivados verificados por checksum y relectura, y marca de commit confirmada. Esa prueba usó la selección v1 (SHA-256 `caaf96067883d6a7c2b79010647614e66bd631f6d30aab38190015a4a2a8f826`), offset 0, lote `b00000`, release raw `resstock_amy2018_release_1`; su commit está en `gold/resstock/scale10k/resstock_amy2018_release_1/_commit/b00000.json` con `run_id=20261126T122106Z-0130e0a5`. No es una ventana v2 ni un release de prueba independiente. El procesador ahora deriva el namespace de salida del `release_id` del manifiesto (v2: `resstock-seleccion-final-v2`), por lo que las marcas v1 existentes se conservan intactas y v2 escribe bajo otro prefijo. No se ha procesado el roster v2 de 10,000 ni actualizado su manifiesto downstream; tampoco se ejecutó el QC global ni la consolidación Silver/Gold final. Un intento anterior de instalar PySpark falló por espacio temporal; posteriormente se instaló en un entorno aislado.

## Estado y bloqueo en CloudShell (evidencia nueva, 26-nov-2026)

| Aspecto | Resultado | Tipo de evidencia |
|---|---|---|
| Orquestador, gates de commit/rutas/presupuestos, Spark sobre 200 perfiles | Pruebas pasadas (ver secciones siguientes) | **Mock S3 + local**, sin AWS |
| Java en CloudShell | Java 21 LTS disponible | Observado en CloudShell |
| PySpark en CloudShell | Entorno aislado con Spark 4.0.1 instalado para la prueba de 5 perfiles | Prueba ejecutada en CloudShell, 26-nov |
| Raw de la selección final v2 | 10,000 perfiles únicos aceptados en la clave canónica; 35,040 filas por perfil | Reconciliación S3 reportada por Antigravity, 26-nov |
| Flujo real S3 → Spark → S3 | Selección v1, offset 0, lote `b00000` de 5 perfiles; 175,200 filas Silver, 60 Gold mensual, 21/21 reglas y commit verificados | Prueba CloudShell, 26-nov; commit conservado en namespace v1. El namespace v2 se separa con `release_id`; no es procesamiento a escala |
| Procesador Spark/QC global de 10,000 perfiles | **No ejecutado** | Sin consolidación Silver/Gold de 10,000 ni QC global |

El primer intento de instalación falló por espacio temporal, pero se resolvió con un entorno aislado. El lote de 5 comprobó el flujo real S3 → Spark → S3, incluidos permisos para publicar en los prefijos probados, relectura y marca de commit. Los resultados mock/local de este documento siguen siendo pruebas aparte. La disponibilidad de 10,000 raws no debe describirse como 10,000 procesados.

**Precaución con el commit histórico:** el piloto v1 ocupa `b00000` bajo el namespace de salida `resstock_amy2018_release_1`. Su marca fue escrita por el formato anterior del procesador y no incluye el campo `raw_release` que exige el gate actual. Si se planifica de nuevo esa misma ventana con la selección v1, el procesador se detendrá como marca no verificable; no la sobrescribirá ni la contará como completa. No borrar ni editar la marca. Para una ejecución exploratoria distinta de v1, elegir un `--output-release` nuevo y una ventana cuyo roster no se haya procesado; para v2, usar siempre el manifiesto de `datos/releases/resstock-seleccion-final-v2`, que selecciona su namespace aislado.

**Siguiente paso seguro (sin borrar datos ni ampliar permisos):**

1. La ingesta raw de 10,000 ya se completó en S3; no volver a descargar ni cambiar su selección v2.
2. Usar el entorno aislado probado con Spark 4.0.1 en CloudShell y revisar espacio temporal antes de cada tanda. No borrar raws ni objetos S3 para liberar espacio y no cambiar políticas IAM.
3. Antes de cada tanda, comprobar la ventana y el roster con el plan sin red; fijar `--max-bytes` y el umbral prudente de costo.
4. Escalar solo después de revisar la marca `_commit`, el roster, el QC y la relectura del lote anterior. La prueba de 5 perfiles no autoriza ni acredita lotes posteriores.

## Flujo por lote

1. **Plan determinista:** mismo orden estable (`--seed`) que el ingestor; lote `bNNNNN` = `orden[offset + k·tam : … + tam]`, `tam ≤ 200`. El release raw se usa para leer `raw/`; el namespace de salida se toma de `release_id` en el manifiesto de `--datos` (o puede fijarse con `--output-release`). Esto mantiene separadas las marcas de commit de selecciones distintas.
2. **Idempotencia con gate cerrado:** si existe `gold/resstock/scale10k/<output-release>/_commit/<lote>.json`, el lote **no se omite por la mera existencia de la llave**: se lee la marca y se exige que coincidan formato, `estado=completo`, lote, release de salida y release raw, SHA-256 de la selección, semilla, ventana, roster exacto (IDs, 35,040 intervalos, filas), QC de Spark aprobado y `run_id`; que su propio checksum/SHA-256/SSE sean válidos; que cada objeto publicado tenga una llave bajo el prefijo `<capa>/resstock/scale10k/<output-release>/<lote>/<run_id>/` y coincida por `HeadObject` (tamaño, `ChecksumSHA256`, SSE; con `--readback-commit` también relectura completa); que existan Silver, Gold mensual y reportes; y que los raw sigan con el checksum registrado. Cualquier discrepancia (marca de otra corrida, corrupta o con objetos faltantes/alterados) detiene el script con `Stop` y diario `invalido`: no se omite ni se sobrescribe, y requiere decisión manual. Un `PUT` de la marca cuya verificación posterior falla tampoco se omite en el siguiente intento sin pasar este mismo gate.
3. **Presupuesto de bytes por ejecución:** antes de descargar cada objeto se reserva su tamaño (`HeadObject`) contra `--max-bytes`; si `usados + tamaño > --max-bytes` el lote se detiene sin descargar ese objeto, de modo que el tope **nunca** se excede (ni siquiera por un archivo). Las reservas de un lote fallido siguen contadas.
3b. **Descarga en streaming** de cada perfil a un directorio temporal (`--tmp`): `HeadObject` con checksum (tamaño, SSE-S3, `ChecksumSHA256`, metadatos `bldg-id`/`license`), SHA-256 del flujo contra S3 y el contrato Parquet (35,040 filas, ID, timestamps, valores). Un solo perfil inválido detiene el lote: no se procesan lotes parciales.
4. **Entrada del job con las herramientas existentes:** se crea en el temporal una salida con el formato del ingestor local (marca, `roster.jsonl` y `consolidado/`) y se ejecutan sin cambios `adaptar_lote_resstock_spark.py` → `preparar_entrada_spark.py` → `job_spark_piloto.py`. Así el roster exacto, los hashes y las 21 reglas QC son los del contrato vigente. EIA y clima entran solo como contexto verificado contra `datos/manifiesto-integracion.json`; **no se republican por lote**, solo se registran sus hashes en la marca. Los subprocesos no heredan variables `AWS_*`.
5. **Compuerta de verificación:** rutas del manifiesto de ejecución estrictas (sin `..`, `.`, absolutas, `\`, segmentos vacíos/ocultos ni caracteres fuera de `[A-Za-z0-9_.=-]`; deben estar bajo `silver/resstock_profile_interval/` o `gold/gold_resstock_monthly/` y terminar en `.parquet`; sin duplicados), sin enlaces simbólicos en todo el árbol de salida, y el conjunto de Parquet en disco debe ser exactamente el listado; además, 0 reglas fallidas y estado `VALID`/`VALID_WITH_WARNINGS`; estado coincidente entre reporte y manifiesto; bytes y SHA-256 de cada archivo físico contra `manifiesto_ejecucion.json`; Silver con exactamente `perfiles × 35,040` filas y los `bldg_id` del roster; Gold mensual con 12 filas por perfil para un año completo.
6. **Publicación** (llaves validadas con segmentos estrictos y prefijo exacto del lote/intento; `--max-bytes-publicar` cuenta tablas **más** reportes auxiliares **y** la marca de commit; solo Silver ResStock y Gold mensual + reportes) bajo
   `silver/resstock/scale10k/<output-release>/<lote>/<run>/…` y `gold/resstock/scale10k/<output-release>/<lote>/<run>/…` con SSE-S3, `ChecksumSHA256`, `IfNoneMatch="*"` (sin ACL, no sobrescribe; 409 se reintenta una vez), `HeadObject` y relectura exacta de cada objeto. `<run>` es único por intento, de modo que un fallo parcial nunca choca con un reintento.
7. **Commit:** al final se escribe `…/_commit/<lote>.json` (roster exacto, hashes raw, objetos publicados con bytes/SHA-256, resultado QC, contexto EIA/clima, atribución, limitaciones), también con `IfNoneMatch`, HEAD y relectura. **Solo entonces el lote cuenta como completo y se borra el temporal.**

## Fallos parciales

Cualquier error deja el lote sin marca de commit, conserva el temporal (el siguiente intento se niega a reutilizarlo hasta que lo revises y borres tú) y registra en el diario el prefijo `<run>` huérfano. Este script **nunca borra objetos de S3**; los huérfanos de un intento fallido cuestan almacenamiento hasta que alguien decida limpiarlos. Se detiene al primer lote fallido, por `AccessDenied`/credenciales, por `--max-bytes` o por espacio temporal insuficiente. El diario local (`--diario`, JSONL con fsync, sin bucket/cuenta/ARN) registra cada etapa; la fuente de verdad de lo completado es la marca de commit en S3.

## ¿El job Spark actual procesa lotes sin romper Gold?

Respuesta corta: **sí para Silver y para el Gold mensual que escribe el job; no para el Gold de patrones del tablero**. Evidencia empírica de la unión: los 200 perfiles locales procesados como 2 lotes de 100 y como 1 lote de 200 dieron un `gold_resstock_monthly` de 2,400 filas **idéntico** (comparación exacta de DataFrames). La no componibilidad de percentiles es un argumento matemático (los lotes de la prueba casi no comparten estratos, así que no sirven para demostrarla empíricamente), no una medición.

| Salida | ¿Componible por lotes? | Motivo |
|---|---|---|
| `silver.resstock_profile_interval` | Sí | Una fila por perfil-intervalo; los lotes son disjuntos. |
| `gold_resstock_monthly` (Spark) | **Sí, exacta** | Clave `(bldg_id, mes, estado, tipo, peso)`: la unión de lotes iguala a un lote único. |
| `gold_eia_monthly`, Silver EIA/clima | Idénticos en cada lote | No dependen de ResStock; por eso no se republican por lote. |
| `gold_resstock_pattern_aggregate` y demás Gold del tablero (`generar_datos_tablero.py`) | **No** | Mediana, p10 y p90 por estrato no se pueden reconstruir con agregados de lotes disjuntos, y el generador carga todo el Parquet con pandas (≈350 M filas para 10,000 perfiles). |

El orquestador **no** llama a `--export-tablero` ni a `generar_datos_tablero.py`, así que el dashboard y Gold v2 no cambian. **Bloqueo para el Gold del tablero a 10,000 perfiles:** hace falta un paso posterior (fuera del perímetro de este bloque) que calcule los percentiles desde datos por perfil. Cambio mínimo propuesto: que el generador consuma `gold_resstock_pattern` por perfil (que sí es una unión por lote) o una tabla horaria por perfil publicada por lote, y calcule allí los cuantiles por estrato en un único paso acotado, o que use sketches (p. ej. t-digest) mergeables.

## Revisión adversarial y pruebas dirigidas (mock, sin red ni AWS)

Hallazgos confirmados y corregidos: (1) `--max-bytes` solo se comparaba antes de descargar y podía excederse por un archivo; (2) un lote se omitía si `HeadObject` veía la marca, sin validarla; (3) la ruta de cada archivo del manifiesto de ejecución no se validaba y la regex de llaves S3 admitía segmentos `.`/`..`; (4) `--max-bytes-publicar` excluía reportes auxiliares y la marca. Pruebas locales dirigidas: **51/51** (`/tmp` fuera del repo): presupuesto exacto y por 1 byte; marca válida aceptada y 14 variantes inválidas rechazadas (otra selección, semilla, ventana, roster, estado, QC, llave con `..`, llave de otro lote, hash o tamaño de objeto distinto, objeto ausente, reporte ausente, raw cambiado, JSON corrupto, metadato de hash distinto) sin PUT sobre la marca; 9 rutas hostiles y 6 llaves hostiles en `safe_relpath`/`safe_key`; salida Spark sintética con `..`, ruta absoluta, enlace simbólico (incluido el reporte), duplicado, Parquet no listado y archivo de otra capa; y presupuesto de publicación con auxiliares/commit. Regresión e2e con Spark real (50 perfiles): completo → re-ejecución `omitido` (con y sin `--readback-commit`) → publicación con tope bajo rechazada antes de cualquier PUT.

### Huecos que persisten (no corregibles dentro de este script)

- El gate de una marca existente confía en los checksums que S3 guardó (HEAD) salvo con `--readback-commit`; no recalcula el contenido de Silver/Gold ni vuelve a ejecutar el QC de Spark.
- Los objetos huérfanos de intentos fallidos no se limpian ni se cuentan en ningún tope (el script no borra de S3); su costo es de almacenamiento.
- Dos ejecuciones concurrentes sobre el mismo lote pueden publicar dos `<run>`; solo una gana la marca (`IfNoneMatch`) y la otra queda con huérfanos.
- Los Parquet del job dependen de la versión de Spark; la reproducibilidad byte a byte entre intentos no está garantizada (por eso cada intento usa un `<run>` propio).
- El lote real de 5 confirmó permisos de lectura/escritura, región, checksum, relectura, SSE-S3 y marca de commit para las claves que usó. Esto no valida permisos para cualquier prefijo ni el comportamiento de lotes mayores.
- El procesamiento y QC de toda la selección v2, además de la consolidación global, siguen sin ejecutarse en AWS.

## Resultados de la verificación local (mock S3, sin red ni AWS)

Entorno: venv preexistente `/tmp/bigdata-escala50-venv` (pyspark 4.0.1, pyarrow 26.0.1), Java 17, `local[2]`; S3 simulado con los 200 raw locales (`data/raw/resstock-bloque-50-250-20261126`, ventana `--offset 50`); no se instaló nada global ni se tocaron los raw.

- 2 lotes de 100: ambos `completo` (200 perfiles, 1,248,659,514 bytes raw leídos, 121.1 s en total), 12 objetos en la simulación (4 Silver, 6 Gold, 2 marcas de commit), temporales borrados tras el commit. Un segundo `--ejecutar` los reportó `omitido` sin objetos nuevos (idempotencia).
- 1 lote de 200 (release de prueba distinto): `completo`; unión de los 2 lotes de 100 = lote único (ver arriba). Duración total del script de prueba (3 corridas Spark): 3 min 37 s; pico de RSS reportado por `time -v` 453 MB (el mayor proceso individual, no la suma).
- Fallos: un raw con bytes que no coinciden con su checksum S3 detiene el lote antes de Spark (0 PUT, 0 commit, temporal conservado); un reintento con ese temporal es rechazado; un `AccessDenied` a mitad de la publicación deja 2 objetos huérfanos, sin marca de commit ni evento `completo`, y el temporal intacto.
- La salida, el diario y los objetos simulados no contienen cuenta, ARN ni nombre de bucket.
- Completado después de esos mocks: ejecución real en CloudShell/S3 para `b00000` de 5 perfiles; 56.7 s de cómputo y 4 objetos derivados más una marca de commit, con checksum y readback verificados. Pendiente: procesar las ventanas v2 a mayor escala, medirlas y realizar consolidación/QC global.

## Comandos

Plan de v2 (sin red ni AWS; el manifiesto selecciona el namespace de salida y el release raw conserva su valor predeterminado):

```bash
python scripts/procesar_resstock_s3_lotes.py --datos datos/releases/resstock-seleccion-final-v2 \
  --lote-tam 200 --max-lotes 2
```

Plantilla para una futura tanda v2 en CloudShell (PySpark 4.0.1, Java 21 y escritura/readback S3 se verificaron en la prueba de 5 perfiles; seleccionar una ventana v2 no procesada. El ejemplo no se ha ejecutado con tamaño 200):

```bash
python3 -m venv ~/venv-resstock && . ~/venv-resstock/bin/activate
pip install boto3 pyarrow pyspark==4.0.1; java -version   # verificar Java 17+ antes de seguir
python scripts/procesar_resstock_s3_lotes.py --datos datos/releases/resstock-seleccion-final-v2 \
  --ejecutar --bucket MI-BUCKET-PRIVADO \
  --lote-tam 200 --max-lotes 1 --max-bytes 1600000000 --tmp ~/tmp-resstock \
  --diario ~/procesamiento_resstock_diario.jsonl
```

Criterio para escalar: cada lote debe terminar con `resultados` = `completo`, marca `_commit` válida y sin temporales residuales; aumentar tamaño solo después de revisar el lote anterior y el tope de costo/espacio. Antes de afirmar 10,000 procesados: marcas para todas las ventanas v2, roster y filas globales (350,400,000), hashes coherentes, QC global y consolidación Gold.

## Qué no hace y riesgos

- No sube datos desde fuera de S3 ni usa EMR; no cambia bucket policy, Public Access Block, versionado ni recursos. Falla cerrado si el bucket no es demostrablemente privado o si su región difiere de la de la sesión (reutiliza las comprobaciones del script de ingesta).
- Costos: las solicitudes son despreciables; añade almacenamiento de Silver/Gold (a medir con el primer lote) y de los huérfanos de intentos fallidos. Aplica el mismo umbral operativo de USD 5 sobre el costo adicional de los primeros 30 días; mide antes de escalar.
- CloudShell: almacenamiento temporal y memoria limitados; `--lote-tam` menor reduce ambos. El job usa `local[2]` por defecto (`--spark-master`).
- No guarda bucket, cuenta, ARN, URLs firmadas ni secretos en diario, marca o reportes.

Atribución obligatoria: *Data includes information from the ResStock™ dataset developed by the National Renewable Energy Laboratory (NREL) with funding from the U.S. Department of Energy (DOE).* CC BY 4.0, «as is». Ver [decisión de publicación](decision-publicacion-datos.md).
