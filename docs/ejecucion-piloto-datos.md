# Piloto de datos y revisión local

**Corte del 17 de noviembre de 2026 · Brian García Mares**

El piloto contiene 10 perfiles anuales de ResStock de Colorado y Nueva York, ocho años de ventas residenciales finales de EIA y una muestra horaria de temperatura de dos lugares de Colorado. Los archivos preparados están en [`data/processed/piloto-datos/`](../data/processed/piloto-datos). El [catálogo](catalogo-datos-final.md) documenta unidades, población, atribución y límites de cada fuente.

## Leer los archivos con Spark

Desde la raíz del repositorio, con Java y PySpark configurados, ejecutar:

```powershell
pyspark --master "local[2]"
```

En la sesión de Spark o en un notebook con el mismo directorio de trabajo:

```python
base = "data/processed/piloto-datos/datos"
resstock = spark.read.parquet(f"{base}/resstock_perfiles_piloto.parquet")
eia = spark.read.csv(f"{base}/eia_residencial_mensual.csv", header=True, inferSchema=True)
clima = spark.read.csv(f"{base}/clima_open_meteo_muestra.csv", header=True, inferSchema=True)
demo = spark.read.csv(f"{base}/demo_colorado_2018_verificacion.csv", header=True, inferSchema=True)

resstock.printSchema()
resstock.groupBy("bldg_id").count().orderBy("bldg_id").show()
print("ResStock:", resstock.count(), "| EIA:", eia.count(), "| Clima:", clima.count(), "| Demo:", demo.count())
```

| Archivo | Conteo comprobado con PySpark 4.0.1 |
|---|---:|
| ResStock | 350,400 filas, 35,040 por cada uno de los 10 perfiles |
| EIA | 5,304 filas, con estados finales y preliminares identificados |
| Open-Meteo | 336 filas, 168 por punto |
| Verificación de Colorado 2018 | 12 meses |

Christian puede confirmar el esquema con este piloto. Diego puede abrir el CSV de la demo y la tabla de cobertura EIA en Excel. La razón del 87.16% corresponde al cociente entre el total modelado de viviendas unifamiliares aisladas y las ventas de todo el sector residencial de Colorado. La unión climática requiere validar ubicación y huso horario.

## Repetir la extracción

Desde la raíz del repositorio con Python 3.11 o posterior y conexión a las fuentes públicas:

```powershell
python -m pip install -r scripts/requirements-datos.txt
python scripts/preparar_datos.py
```

La salida predeterminada es `data/raw/reproduccion-piloto-datos/`. Esa ruta está excluida de Git. El script recupera los perfiles del piloto y genera la lista propuesta de candidatos. Los archivos descargados quedan en `raw/` dentro de la salida. Los archivos preparados se escriben en `datos/`.

El [manifiesto](../data/processed/piloto-datos/manifiesto.json) guarda los hashes, la procedencia y los conteos. Sus rutas `raw/` corresponden a archivos recuperables mediante el script y sus URL. Las entradas `datos/` están incluidas en el repositorio.

## Escala del piloto

La [nota de viabilidad](viabilidad-resstock-10000.md) registra 64.51 MB de archivos crudos del piloto y estima 64.51 GB para el lote de 10,000 perfiles. El CSV de candidatos registra la selección propuesta. La descarga completa requiere la decisión del equipo sobre espacio, transferencia y costo.
