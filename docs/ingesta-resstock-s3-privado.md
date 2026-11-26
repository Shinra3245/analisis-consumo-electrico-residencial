# Ingesta ResStock a S3 privado (ruta para los 10,000 perfiles sin disco local)

`scripts/ingesta_resstock_a_s3_privado.py` descargó **un perfil por vez** de OEDI a un temporal, lo validó y lo subió a S3 **privado**; el temporal se borró tras cada perfil. Es independiente de `scripts/ingesta_resstock_lotes.py` y no procesa Silver, Gold ni el dashboard.

**Estado (26-nov-2026): ingesta raw Scale-10k completada en S3.** La reconciliación reportada por Antigravity confirma 10,000 Parquet únicos aceptados: 9,998 perfiles primarios más 432862 (WI) y 491767 (CT), con 35,040 filas por perfil, checksum/SHA-256, tamaño y relectura verificados, SSE-S3 y bloqueo de acceso público. Los dos IDs originales rechazados por energía negativa (294772 y 481740) permanecen aislados en el diario y no cuentan. El procesamiento Spark, QC global, Silver/Gold de esta selección y el dashboard actualizado **siguen pendientes**. Véase la [selección final v2](decision-seleccion-resstock-final-v2.md).

## Qué hace por cada perfil

1. Toma el siguiente ID del orden estable (mismo `--seed`, estratos intercalados) que no esté `aceptado` en el diario.
2. Descarga por HTTPS solo desde el host OEDI y con la URL exacta del release (sin redirecciones a otros hosts), con tope de bytes por archivo; calcula SHA-256 en streaming.
3. Valida el Parquet: 35,040 filas, columnas `bldg_id`/`timestamp`/energía total, un único `bldg_id` igual al esperado, timestamps de 15 min desde `2018-01-01 00:15`, energía finita y no negativa. Si falla: `rechazado`, no se sube.
4. `PutObject` a `raw/resstock/scale10k/<release>/<id>.parquet` con `ServerSideEncryption=AES256` (SSE-S3), `ChecksumSHA256` (S3 rechaza el PUT si no coincide), `IfNoneMatch="*"` (no sobrescribe) y **sin ACL**.
5. `HeadObject` con `ChecksumMode=ENABLED` (tamaño, checksum SHA-256, cifrado) y relectura completa del objeto con SHA-256 (`--readback-cada N` permite espaciarla; por defecto cada perfil).
6. 412 (el objeto ya existe): solo se acepta tras verificar tamaño, SHA-256 (HEAD y relectura forzada) y SSE-S3; si coincide → `aceptado` con nota «ya existía»; si no → `conflicto` y el script se detiene. 409 (`ConditionalRequestConflict`, solicitud concurrente sobre la misma llave): se reintenta **una vez** de forma condicional; si persiste, se registra `conflicto` sin verificar ni sobrescribir y el script se detiene. Nunca sobrescribe.
7. Agrega un registro al diario local (`--diario`, JSONL con fsync, gana el último por ID) y borra el temporal.

Al terminar escribe un manifiesto de auditoría `raw/resstock/scale10k/<release>/_audit/<run_id>.json` (también `IfNoneMatch`, SSE-S3) con conteos, bytes, hash de la selección, hash de `citation.txt`, región, costo estimado y motivo de parada. El diario local no contiene el nombre del bucket, credenciales ni URLs firmadas.

## Comprobaciones que fallan cerrado (antes del primer PUT)

| Comprobación | Cómo se demuestra | Si falta |
|---|---|---|
| Credenciales temporales | Cadena por defecto de boto3; el script no tiene parámetros de llaves. Aborta si hay `AWS_SECRET_ACCESS_KEY` sin `AWS_SESSION_TOKEN` | Abortar |
| boto3 reciente | `PutObject` debe declarar `IfNoneMatch`, `ChecksumSHA256`, `ServerSideEncryption` | Abortar |
| Identidad | `sts:GetCallerIdentity`; solo se registra `identidad_validada=true`: ni cuenta, ni ARN, ni parte de ellos se imprimen o guardan | Abortar |
| Bucket accesible y misma región que la sesión | `HeadBucket` | Abortar (evita transferencia entre regiones) |
| Bucket privado | `GetPublicAccessBlock` con los cuatro bloqueos en `true`; `GetBucketPolicyStatus` no público (si se deniega, aviso) | Abortar; **no lo corrige** |
| Licencia CC BY 4.0 | Lee `citation.txt` del release y exige «CC-BY-4.0»; guarda su SHA-256; atribución en cada manifiesto | Abortar |
| Selección | 10,000 IDs sin duplicados, URL/release/`upgrade=0` exactos | Abortar |
| Prefijo seguro | Fijo bajo `raw/resstock/scale10k/`; el release solo admite `[A-Za-z0-9_.-]`; nunca `gold/`, web ni público | Abortar |
| Costo | Costo adicional de la primera ventana de 30 días del lote (solicitudes + transferencia si aplica + almacenamiento del lote), tanto el estimado como la cota superior por `--max-bytes`, ≤ `--max-costo-usd` (tope duro 5) | Aborta y exige un lote menor, indicando el `--limite` máximo |
| Límites explícitos | `--ejecutar` exige `--bucket`, `--limite` y `--max-bytes` | Rechazar argumentos |
| Espacio temporal | ≥ 4 × `--max-bytes-archivo` libres | Abortar |

**Limitación honesta:** el permiso `s3:PutObject` se comprobó con los PUT reales de la prueba de 1 perfil y del escalado raw; la prueba posterior de cinco perfiles también verificó publicación derivada en sus prefijos específicos. Estos resultados no garantizan permisos en cualquier clave. `AccessDenied`, `ExpiredToken`, `NoSuchBucket` y similares detienen la ejecución sin reintentos. El script nunca llama a `Put*Policy`, `PutPublicAccessBlock`, `PutBucketVersioning` ni crea o borra recursos; solo lee esas configuraciones.

## Paradas seguras

Se detiene (y lo registra) al alcanzar `--max-bytes` o `--limite`, tras `--max-fallos-seguidos` (5) fallos de red, tras `--max-anomalias` (5) rechazos/conflictos, **al primer conflicto**, o ante cualquier error fatal de AWS. Reanudar es repetir el mismo comando: los `aceptado` del diario se omiten; `--reintentar` reintenta fallidos/rechazados; los `conflicto` requieren decisión manual. Una última línea truncada del diario se descarta; otra corrupción detiene la ejecución.

## Costos (estimación, no garantía)

Precios de lista S3 Standard, sobrescribibles con `--precio-put-1000`, `--precio-get-1000`, `--precio-gb-mes`. El **umbral operativo de USD 5** se evalúa sobre el costo adicional de la **primera ventana de 30 días del lote**: solicitudes + transferencia entre regiones (si aplicara) + almacenamiento del lote durante ese periodo (se cuenta como un mes completo). Se evalúa el estimado con la media observada (6,168,532 bytes/perfil, 250 perfiles) y, si se pasa `--max-bytes`, también la cota superior de bytes descargables; se usa la mayor. Si supera el umbral, el script aborta y exige un lote menor (`--limite` ≤ el valor sugerido y/o `--max-bytes` menor); no omite el almacenamiento. El costo **mensual recurrente** posterior se informa aparte y no es un límite duro.

Ejemplo para 10,000 perfiles ≈ 61.7 GB:

| Concepto | Estimación |
|---|---:|
| Solicitudes PUT/GET/HEAD (10,001 PUT, ~20,000 GET/HEAD) | ≈ USD 0.06 |
| Transferencia entre regiones | 0 (bucket en la región de la sesión, obligatorio) |
| Almacenamiento primeros 30 días (≈ 61.7 GB × USD 0.023) | ≈ USD 1.42 |
| **Costo adicional primeros 30 días (compara con USD 5)** | **≈ USD 1.48** |
| Costo mensual recurrente después (informativo) | ≈ USD 1.42 / mes |

La descarga desde OEDI hacia CloudShell no genera cargo de salida para la cuenta. Excluye impuestos, descuentos, KMS (no se usa), registros de CloudTrail y otros servicios. Los crudos permanecen en S3 hasta que alguien decida borrarlos.

## Procedimiento histórico de validación de 1 perfil (ya ejecutado)

La prueba real de 1 perfil y el escalado raw a 10,000 ya se completaron el 26-nov-2026. Los comandos siguientes describen el procedimiento usado y sirven como referencia de reproducción; no son pasos pendientes para completar la ingesta actual. El ingestor por defecto lee la selección v1 (`datos/resstock_seleccion_propuesta.csv`). La selección final v2 contiene los dos reemplazos y está versionada en [`datos/releases/resstock-seleccion-final-v2/`](../datos/releases/resstock-seleccion-final-v2/); los reemplazos se validaron y cargaron por el flujo suplementario, y quedaron reconciliados bajo las claves canónicas que espera el procesador.

En la misma región que el bucket, con un bucket **privado preexistente** (con Public Access Block completo), desde un clon del repositorio:

```bash
# 1) Verifica en la sesión qué hay instalado (no se asume que CloudShell incluya boto3/pyarrow)
python3 --version; python3 -c "import boto3; print('boto3', boto3.__version__)"; python3 -c "import pyarrow; print('pyarrow', pyarrow.__version__)"
# 2) Si falta alguno, instala en un venv aislado bajo $HOME (no toca el Python del sistema)
python3 -m venv ~/venv-resstock && . ~/venv-resstock/bin/activate
pip install boto3 pyarrow   # se requiere un boto3 reciente: PutObject con IfNoneMatch y ChecksumSHA256
python scripts/ingesta_resstock_a_s3_privado.py --limite 1                      # plan, sin red
python scripts/ingesta_resstock_a_s3_privado.py --ejecutar --bucket MI-BUCKET-PRIVADO \
  --limite 1 --max-bytes 30000000 --diario ~/resstock_s3_diario.jsonl
```

Criterios de éxito: código de salida 0; `aceptado: 1`, 0 rechazados/fallidos/conflictos; `motivo_parada: null`; objeto visible en `raw/resstock/scale10k/<release>/<id>.parquet` con SSE-S3 y checksum SHA-256; el manifiesto en `_audit/`; sin archivos temporales residuales en `/tmp/resstock-*`. Repetir el mismo comando debe tomar el **siguiente** ID, no el primero.

## Procedimiento histórico de escalado por lotes (ya ejecutado)

El escalado se hizo por tandas reanudables, con límites de bytes/costo y diarios separados. Los comandos de este bloque son históricos; no deben repetirse sobre la selección v1 para regenerar el release raw ya reconciliado.

## Estado y evidencia actual de Scale-10k

**Evidencia actual:** la adenda de Antigravity reporta 10,000 `aceptado` con IDs únicos en la clave canónica, 35,040 filas por perfil (350,400,000 intervalos raw), checksum/SHA-256, tamaño y relectura exactos, y 25 manifiestos de ingesta. La selección final es [`datos/releases/resstock-seleccion-final-v2/resstock_seleccion_propuesta.csv`](../datos/releases/resstock-seleccion-final-v2/resstock_seleccion_propuesta.csv), SHA-256 `247394923fd54ad52528a4913e53bec4e330e26f0734bf0a15cea3f67482199d`; el manifiesto registra `raw_validated_s3_pending_spark`. Esa evidencia no acredita procesamiento Spark ni QC Silver/Gold de los 10,000. Un lote distinto con selección v1, offset 0 y tamaño 5 sí validó Spark real en CloudShell; no forma parte del roster v2. Gold v2 del dashboard no cambia hasta generar y validar explícitamente otra versión de tablas.

## Superficies de riesgo y qué no hace

- Publicar crudos: solo `raw/` privado; no copia a Git, website ni `gold/`; no genera URLs firmadas. El nombre del bucket se pasa por argumento y no se escribe en el repo.
- Políticas: no altera política, Public Access Block, versionado, ACL ni cifrado por defecto del bucket. Sin versionado, un PUT condicional evita sobrescrituras pero no «borra» historial; no se usa `DeleteObject`.
- Cuenta compartida (Learner Lab): si las credenciales no permiten `GetPublicAccessBlock`, el script se detiene; no se debilita la comprobación.
- Si se pierde el diario o se cambia de bucket/prefijo, hay que decidir manualmente; el diario no conserva el bucket por diseño.
- Los lotes descargados localmente (10, 50 y 250) son evidencias separadas; no se suman a la cifra de S3 ni se sustituyen por ella. S3 contiene su conjunto raw propio de 10,000 IDs de la selección v2.

Atribución obligatoria en productos derivados: *Data includes information from the ResStock™ dataset developed by the National Renewable Energy Laboratory (NREL) with funding from the U.S. Department of Energy (DOE).* CC BY 4.0, «as is». Ver [decisión de publicación](decision-publicacion-datos.md).

## Qué se guarda y qué no

Diario y manifiesto contienen: IDs de edificio, llaves bajo el prefijo `raw/`, bytes, SHA-256, filas, estados, conteos, región, `run_id`, SHA-256 de la selección y de `citation.txt`, `identidad_validada` y el costo estimado. **No** contienen ID de cuenta, ARN, correo, nombre del bucket, URLs firmadas, llaves ni tokens. Los mensajes de error AWS se reducen al código (por ejemplo `AccessDenied`). Revisa a mano el diario antes de compartirlo; la ruta que elijas para `--diario` puede incluir tu usuario.
