# Adaptador de un lote ResStock aceptado a la entrada Spark

`scripts/adaptar_lote_resstock_spark.py` convierte la salida de [`ingesta_resstock_lotes.py`](ingesta-resstock-lotes.md) en la carpeta que consume `scripts/preparar_entrada_spark.py` (y, después, `scripts/job_spark_piloto.py`). Es opt-in: no cambia el flujo piloto vigente ni modifica esos scripts.

**Estado de verificación:** escrito y revisado estáticamente. No se ha ejecutado el adaptador, el empaquetador ni el job Spark, y la compatibilidad de extremo a extremo no está probada.

## Uso

```bash
# 1. Lote aceptado y consolidado (ver la guía de ingesta)
python scripts/ingesta_resstock_lotes.py --consolidar --output data/raw/resstock-ingesta

# 2. Adaptador: --output debe ser una carpeta NUEVA
python scripts/adaptar_lote_resstock_spark.py \
  --ingesta data/raw/resstock-ingesta \
  --output /tmp/entrada-preparada-lote \
  --base-manifest datos/manifiesto-integracion.json \
  --eia datos/eia_residencial_mensual.csv \
  --clima datos/clima_open_meteo_muestra.csv \
  --seleccion-candidatos datos/resstock_seleccion_propuesta.csv

# 3. Empaquetado existente y, por separado, el job (ver ejecucion-job-spark-local.md)
python scripts/preparar_entrada_spark.py --prepared /tmp/entrada-preparada-lote --output /tmp/entrada-spark-lote
python scripts/job_spark_piloto.py --input /tmp/entrada-spark-lote --output /tmp/salidas-spark-lote --master 'local[2]'
```

Los comandos 2 y 3 se documentan sin haberse ejecutado. Ejecuta el módulo desde cualquier directorio: importa funciones de validación de `ingesta_resstock_lotes.py`, que debe estar en la misma carpeta `scripts/`. Requiere `pyarrow`.

## Entradas y validaciones

- `--ingesta`: salida reconocida del ingestor (marca `ingesta_resstock.json` con formato válido). Se lee `roster.jsonl` con las mismas reglas del ingestor; si termina sin salto de línea se rechaza y hay que reanudar el ingestor para repararlo. Solo cuentan los perfiles `aceptado`; debe haber al menos uno.
- `consolidado/` ya generado con `--consolidar`: `consolidado.json` debe declarar exactamente los IDs aceptados actuales, el SHA-256 del Parquet debe coincidir, el esquema debe ser `bldg_id`, `timestamp_fin_local`, `electricidad_kwh` y cada ID aceptado debe tener 35,040 filas y ningún otro ID. Si el lote cambió después de consolidar, el adaptador falla; hay que mover `consolidado/` y consolidar de nuevo.
- `--base-manifest`, `--eia`, `--clima`, `--seleccion-candidatos`: rutas explícitas, archivos regulares (no enlaces), con el nombre del contrato y fuera de la carpeta del ingestor. Bytes, SHA-256 y filas deben coincidir con el manifiesto base, que sigue siendo la fuente de licencia y procedencia; el adaptador no inventa ni duplica esos metadatos. La selección de candidatos debe tener el mismo SHA-256 que la usada por el ingestor.

El adaptador no relee los Parquet individuales de `raw/`: su integridad la comprueba el ingestor (`--revalidar`).

## Salida

```text
<output>/manifiesto.json   lista de registros {archivo, bytes, filas, sha256, ...}; el Parquet añade profile_roster
<output>/datos/resstock_perfiles_piloto.parquet   perfiles ACEPTADOS (nombre fijo del contrato)
<output>/datos/resstock_seleccion_piloto.csv      subconjunto de candidatos con los aceptados (mismas columnas, p. ej. condado_codigo y peso_viviendas)
<output>/datos/resstock_seleccion_propuesta.csv, eia_residencial_mensual.csv, clima_open_meteo_muestra.csv   copias verificadas
```

`profile_roster.bldg_ids` son exactamente los IDs aceptados; `filas = aceptados × 35,040`; el registro del Parquet incluye `perfiles_aceptados` y `candidatos_en_seleccion` para no confundir conjuntos. Los nombres «piloto» son heredados del contrato: en un lote ampliado no significan 10 perfiles.

Se publica en un staging temporal junto al destino y se renombra de forma atómica. Se rechazan destinos existentes, padres o destinos simbólicos y solapamientos con el ingestor, las entradas, `datos/`, `docs/`, `scripts/` y `tablero/`. No se copian raw individuales ni se escriben URL firmadas o secretos.

## Limitaciones

- El adaptador no ejecuta Spark. Que `job_spark_piloto.py` escale a decenas o miles de perfiles sigue sin probarse y requiere una ejecución separada con medición de memoria y tiempo.
- El manifiesto de integración que escribe `preparar_entrada_spark.py` conserva su nota y descripción de transformación genéricas; la cantidad real está en `manifiesto.json` y en el roster.
- Los CSV de EIA y clima son los del manifiesto base; no se actualizan ni se amplían aquí.
- La atribución y licencia ResStock/NREL/DOE (CC BY 4.0, datos «as is», uso de investigación) siguen la [decisión de publicación](decision-publicacion-datos.md); no se publican crudos.
