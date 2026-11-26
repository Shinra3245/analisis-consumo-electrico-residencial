# Ingesta ResStock por lotes (reanudable e idempotente)

`scripts/ingesta_resstock_lotes.py` prepara el camino hacia la meta de 10,000 perfiles ResStock sin confundir candidatos con datos descargados. Es independiente de `scripts/preparar_datos.py`, cuyo comportamiento piloto no cambia.

**Estado de verificación (26-nov-2026):** ejecución runtime controlada de un perfil. Se descargaron 2,369,382 bytes; 1/1 perfil fue aceptado, con 35,040 intervalos, cero rechazos y cero fallos. La consolidación y validación de hash finalizaron. No representa una prueba de escalabilidad ni el cumplimiento de la meta de 10,000 perfiles.

## Conjuntos que nunca se mezclan

| Conjunto | Significado | Fuente |
|---|---|---|
| Candidatos | IDs de `datos/resstock_seleccion_propuesta.csv` (10,000 filas) | Archivo versionado; no son descargas |
| Intentados | Perfiles con registro en `roster.jsonl` | Diario de la ingesta |
| Descargados | Registros con bytes recibidos (aceptados o rechazados) | Diario |
| Aceptados | Descargados que pasaron la validación Parquet | Diario; **único conjunto que cuenta como procesado** |

El resumen informa `aceptados_sobre_meta` (por ejemplo `0/10000`) y nunca deriva un total procesado del tamaño de la selección. La selección es de cobertura de estratos, no una muestra representativa ni un estimador nacional.

## Atribución, licencia y publicación

Los datos son ResStock 2025 Release 1 (AMY 2018, `upgrade=0`), licencia CC BY 4.0. Texto de atribución: *Data includes information from the ResStock™ dataset developed by the National Renewable Energy Laboratory (NREL) with funding from the U.S. Department of Energy (DOE).* Los datos se proporcionan «as is», para investigación y sin garantía (sección Disclaimer del README del release). Ver [decisión de publicación](decision-publicacion-datos.md) y [`datos/README.md`](../datos/README.md).

La herramienta **no copia crudos a Git ni a S3**. Los Parquet descargados quedan bajo `--output`; cualquier redistribución de crudos sigue sujeta a la decisión de publicación existente. Dentro del repositorio solo se acepta `data/raw/` (ignorado por Git).

## Selección y orden reproducibles

El orden se calcula de la selección y la semilla (`--seed`, por defecto `22030511`): dentro de cada estrato estado × tipo se ordena por `SHA-256(semilla:bldg_id)` y se intercalan los estratos por posición relativa. Así, cualquier prefijo del orden cubre varios estratos. La misma selección y semilla dan siempre el mismo orden. Se valida que cada URL sea exactamente la del release esperado (`upgrade=0`, host OEDI) y que los IDs sean únicos.

## Comandos

Plan (predeterminado; no usa red ni escribe archivos):

```bash
python scripts/ingesta_resstock_lotes.py --limite 50
python scripts/ingesta_resstock_lotes.py --limite 50 --offset 50 --output data/raw/resstock-ingesta
```

Ejecución opt-in de un primer lote pequeño (requiere `pyarrow`, ver `scripts/requirements-datos.txt`):

```bash
python scripts/ingesta_resstock_lotes.py --descargar --limite 25 --concurrencia 2 \
  --output data/raw/resstock-ingesta
```

Reanudar con los siguientes 25 perfiles aún sin registro, y reintentar fallidos/rechazados (hasta `--max-intentos`):

```bash
python scripts/ingesta_resstock_lotes.py --descargar --continuar --reintentar --limite 25 \
  --output data/raw/resstock-ingesta
```

Semántica de lote: sin `--continuar`, el lote es la ventana `[--offset, --offset + --limite)` del orden estable (`--offset` por defecto 0); con `--continuar`, son los primeros `--limite` perfiles sin registro y `--offset` **se rechaza**. `--reintentar` solo se admite con `--continuar`. Se validan antes de iniciar: `--limite` ≥ 1, `--offset` dentro de la selección, `--concurrencia` 1 a 4, `--max-bytes-archivo` y `--max-bytes-lote` positivos, `--reintentos` ≥ 0, `--max-intentos` ≥ 1 y `--seed` ≥ 0.

Reejecutar un mismo lote es idempotente: los perfiles aceptados se reutilizan tras comprobar bytes y SHA-256 contra el roster (`--revalidar` relee además el Parquet), y no se descargan de nuevo.

## Salida

```text
<output>/ingesta_resstock.json   marca de propiedad: formato, semilla, SHA-256 de la selección
<output>/roster.jsonl            un registro durable (fsync) por perfil; gana el último por ID
<output>/resumen.json            resumen de conjuntos, escrito de forma atómica
<output>/raw/resstock/<ST>/<id>-0.parquet   perfiles aceptados
<output>/cuarentena/<ST>/<id>-0.intentoN.parquet   descargados e inválidos
<output>/consolidado/            solo con --consolidar
```

Campos del roster: `bldg_id`, `estado_eeuu`, `tipo_vivienda`, `url`, `estado_proceso` (`aceptado`, `rechazado`, `fallido` o `conflicto`), `bytes`, `sha256`, `filas`, `segundos`, `error`, `intentos`, `capturado_utc`, `ruta`. Un perfil sin registro está pendiente. Todos los conteos del resumen se calculan sobre la misma selección y el mismo roster validado; `pendientes_sin_intentar = candidatos − intentados` nunca es negativo y, si los conteos fueran inconsistentes, la herramienta falla en lugar de escribir el resumen.

## Validación por perfil

Se rechaza y se envía a cuarentena, con la causa en `error`, todo Parquet que no cumpla: 35,040 filas; columnas `bldg_id`, `timestamp` y `out.electricity.total.energy_consumption..kwh`; un único `bldg_id` igual al esperado; timestamps de fin de intervalo desde `2018-01-01 00:15`, en orden y con paso de 15 minutos; energía no nula, finita y no negativa. Un rechazado no cuenta como aceptado. Los errores de esquema, tipo o valor (nulos, tipos inesperados, columnas ausentes, Parquet ilegible) se convierten siempre en un rechazo por perfil con su causa y cuarentena; los errores de sistema inesperados no se ocultan. Los fallos de red (incluidos tiempos de espera y HTTP 429/5xx) se reintentan con espera exponencial y, si persisten, quedan `fallido`.

## Seguridad e idempotencia

- La salida debe ser nueva o una salida propia reconocida (marca `ingesta_resstock.json` con la misma selección y semilla). Se rechazan enlaces simbólicos, carpetas no vacías sin marca, rutas raíz o del usuario, y solapamientos con la carpeta de la selección, `datos/`, `tablero/`, `docs/` o `scripts/`.
- Un archivo existente sin registro aceptado, o aceptado cuyo tamaño o SHA-256 ya no coincide, queda `conflicto`: no se sobrescribe ni se reutiliza en silencio y requiere decisión manual.
- Cada descarga va a un `.part` y se mueve solo tras validarse.
- El diario se agrega y sincroniza por perfil; una caída pierde como máximo el perfil en curso.
- **Cola sin salto de línea del diario:** solo el último fragmento sin LF recibe trato especial. Si es un registro JSON completo, se valida contra la selección (ID, estado, URL, tipos, ruta) y **se incluye en el roster** antes de elegir el lote y de resumir o consolidar, de modo que ese perfil no se reprocesa; al descargar solo se le añade el LF. Si es un JSON completo pero inválido, la ejecución se detiene con un error y hay que corregir `roster.jsonl` a mano. Si no es JSON (escritura truncada por una caída), no cuenta como registro: antes de agregar se aparta en `roster.jsonl.truncado-<fecha>` y el diario se recorta a la última línea íntegra. Los modos plan y `--consolidar` solo leen: ven el roster recuperado sin modificar el archivo. Cualquier otra línea corrupta, con tipos/campos inválidos, con un `bldg_id` ajeno a la selección o con `ruta` insegura detiene la ejecución; la herramienta no la repara.
- **Rutas internas:** el marcador, el diario, el resumen, los `.part`, los archivos finales, la cuarentena y `consolidado/` se resuelven con una comprobación que rechaza enlaces simbólicos en cualquier componente y rutas que escapen de `--output`. Un `.part` o `.tmp` previo se descarta antes de escribir y los archivos nuevos se abren en modo exclusivo, de modo que un enlace preexistente no hace escribir fuera de la salida. Un perfil cuya ruta resulta insegura queda `conflicto`.

## Límites y riesgos

- Concurrencia predeterminada 2, máximo 4. `--max-bytes-archivo` (25 MB por defecto; los diez perfiles piloto midieron 5.4 a 7.0 MB) y `--max-bytes-lote` (2 GB). El tope de lote se comprueba antes de iniciar cada descarga, por lo que puede excederse hasta `concurrencia × max-bytes-archivo`.
- Proyección, no medición: 10,000 perfiles a la media piloto (6,450,949.7 bytes) serían unos 64.5 GB decimales ([viabilidad](viabilidad-resstock-10000.md)). Medir un lote intermedio antes de ampliar y comprobar espacio en disco.
- La descarga usa el bucket público de OEDI; respeta cuotas y la política de uso. Comprobar la región y el costo de salida antes de mover datos a otro servicio.
- Aceptar un perfil significa que cumple el contrato por perfil; no valida representatividad ni cobertura de estratos.

## Camino hacia Spark

`--consolidar` (sin red) une solo los aceptados en `consolidado/resstock_perfiles_lote.parquet` con las columnas `bldg_id`, `timestamp_fin_local` y `electricidad_kwh` del contrato actual. Escribe también `resstock_seleccion_aceptada.csv` y `consolidado.json` con el `profile_roster`. Los nombres, el orden ascendente de IDs y la estructura de `profile_roster` no cambian, por lo que el [adaptador](adaptador-lote-resstock-spark.md) los sigue leyendo igual.

Antes de leer cada perfil aceptado, `--consolidar` lo revalida: la ruta debe estar dentro de `--output`, y los bytes y el SHA-256 deben coincidir con el registro aceptado y el archivo debe volver a pasar la validación por perfil (ID, 35,040 intervalos, valores). Si un raw se alteró después de aceptarse, la consolidación se detiene con un error que nombra el perfil y no se publica ninguna salida.

La construcción ocurre en un staging hermano (`.consolidado.stage-*` dentro de `--output`): se escriben allí el Parquet, el CSV y el JSON, se comprueban filas, IDs y SHA-256, y solo entonces se renombra de forma atómica a `consolidado/`. Si algo falla, el staging se elimina y se puede reintentar. Un `consolidado/` preexistente (incluso vacío) se rechaza sin borrarlo; muévelo antes de volver a consolidar. **Ejecución observada:** el 26-nov-2026 se consolidó 1 perfil, 35,040 filas; el hash del Parquet coincidió con `consolidado.json`. La salida usada fue `data/raw/resstock-ingesta-validation-20261126/`, ignorada por Git.

`scripts/preparar_entrada_spark.py` todavía **no** acepta esta salida directamente: exige una carpeta con `manifiesto.json` de `preparar_datos.py` y los nombres fijos `resstock_perfiles_piloto.parquet` y `resstock_seleccion_piloto.csv`, más los CSV de EIA y clima. Falta un adaptador que:

1. renombre o enlace el Parquet y el CSV de selección aceptada a esos nombres, o que `preparar_entrada_spark.py` admita nombres configurables;
2. genere `manifiesto.json` con `archivo`, `bytes`, `filas`, `sha256` y `profile_roster` por artefacto;
3. incorpore los CSV de EIA y clima.

El adaptador ya está implementado en [`adaptar_lote_resstock_spark.py`](../scripts/adaptar_lote_resstock_spark.py) y su ejecución de un perfil se documenta en [`adaptador-lote-resstock-spark.md`](adaptador-lote-resstock-spark.md). La prueba confirmó 35,040 filas y el roster de un ID. Esto no prueba que `job_spark_piloto.py` escale a 10,000 perfiles.
