# Viabilidad de 10,000 perfiles de ResStock

**Brian García Mares**

**Fuente:** ResStock 2025.1, AMY 2018, escenario base `upgrade=0`

## Trabajo comprobado

| Medida | Resultado |
|---|---:|
| Candidatos de metadatos nacionales | 549,971 |
| Cobertura de candidatos | 50 estados y Washington D. C. |
| Estratos con candidatos, por estado y tipo RECS | 254 |
| Perfiles preseleccionados | 10,000 |
| Archivos solicitados en el piloto | 10 |
| Perfiles descargados y validados | 10 |
| Descargas o validaciones fallidas | 0 |
| Intervalos por perfil | 35,040 |
| Filas en los 10 perfiles | 350,400 |
| Bytes crudos descargados del piloto | 64,509,497 |
| Bytes medios por perfil | 6,450,949.7 |
| Tamaño mínimo y máximo | 5,378,721 a 7,042,415 bytes |

Colorado y Nueva York aportaron un perfil de cada una de sus cinco clases de vivienda. En cada archivo se comprobó el identificador, la secuencia de 15 minutos y la existencia de valores numéricos finitos de energía. Los tiempos medidos por archivo y por lote se registran en [el manifiesto](../data/processed/piloto-datos/manifiesto.json) y [el resumen de ejecución](../data/processed/piloto-datos/resumen-ejecucion.json). El tiempo depende de la red y la máquina utilizadas.

## Selección propuesta

1. Filtrar el baseline a simulaciones satisfactorias con tipo declarado y peso positivo.
2. Formar un estrato por estado y tipo de vivienda RECS. Asignar un lugar inicial a los estratos con datos y distribuir los lugares restantes en proporción a su capacidad de candidatos, usando restos mayores.
3. Seleccionar sin reemplazo dentro de cada estrato con la semilla fija `22030511`. Los 10,000 identificadores y URL están en [la selección propuesta](../data/processed/piloto-datos/datos/resstock_seleccion_propuesta.csv). El número de candidatos y la cuota por estrato se pueden auditar en [la tabla de cobertura](../data/processed/piloto-datos/datos/resstock_cobertura_estratos.csv).
4. Al escalar, validar que cada URL entregue un perfil completo y registrar reintentos, fallas y, si procede, sustituciones dentro del estrato. La disponibilidad de los 10 archivos del piloto quedó comprobada.

La preselección sirve para explorar perfiles con cobertura de tipos y estados. Las cuotas pequeñas pueden servir para revisar esquema o presencia. Para resultados nacionales, usar los agregados oficiales de ResStock. Una estimación poblacional a partir de la submuestra requiere revisar ponderación de origen, probabilidad de selección y tamaño efectivo.

## Estimación y decisión propuesta

**10,000 × 35,040 = 350,400,000 intervalos esperados**, si todos los archivos son válidos y completos.

**10,000 × 6,450,949.7 bytes = 64.51 GB crudos estimados** (60.08 GiB). El rango de tamaños individuales observado fue de 5.38 a 7.04 MB por archivo. La proyección usa un piloto de 10 perfiles de dos estados. Separar del volumen crudo el espacio que requerirán el procesamiento y sus salidas.

Propongo revisar el esquema con Christian y medir un segundo lote de mayor diversidad antes de decidir el volumen que se transportará a S3. El script permite aumentar el piloto con `--pilot-states` y `--pilot-per-stratum`, y limita la extracción a la cuota seleccionada de cada estrato. Para validar la consulta del país se pueden utilizar los agregados estatales del release desde el inicio. Omar y Christian deben confirmar el presupuesto de almacenamiento y procesamiento, y el equipo debe acordar cualquier cambio al alcance de la propuesta.
