# Viabilidad de la selección de 10,000 perfiles ResStock

Fuente indicada por la entrega de Mares: ResStock 2025 Release 1, AMY 2018, baseline `upgrade=0`. Esta nota separa datos disponibles, cifras reportadas por el integrante y proyecciones. La lista de selección y cobertura están en [`datos/`](../datos/README.md); los archivos crudos no se incluyeron en el ZIP recibido.

**Actualización 26-nov-2026:** la selección final v2 completó la ingesta raw en S3 privado con 10,000 perfiles únicos aceptados (9,998 primarios y dos reemplazos), 35,040 filas por perfil y 350,400,000 intervalos en total. Este conteo se apoya en la validación por perfil y la reconciliación S3 de Antigravity. El job Spark, QC global y las tablas Silver/Gold a escala 10,000 aún no se ejecutaron; el dashboard sigue consumiendo Gold del piloto de 10 perfiles. Detalle y hashes de la selección en [`decisión v2`](decision-seleccion-resstock-final-v2.md).

## Estado y cifras del piloto

| Medida | Valor | Evidencia/estado |
|---|---:|---|
| Candidatos de metadatos nacionales | 549,971 | Reportado en el manifiesto de la entrega; índice crudo ausente en el ZIP. |
| Estados/D. C. con cobertura | 51 | Reportado en la entrega. |
| Estratos estado × tipo de vivienda con candidatos | 254 | Coincide con filas en `resstock_cobertura_estratos.csv`. |
| IDs en la selección v1 inicial | 10,000 | En el corte original eran candidatos; la selección final v2 y su estado de descarga se documentan arriba. |
| Perfiles en el Parquet integrado | 10 | Conteo y esquema del artefacto integrados. |
| Filas del Parquet piloto | 350,400 | 35,040 por perfil. |
| Perfiles raw aceptados en S3 (selección v2) | 10,000 | 9,998 primarios + reemplazos 432862 y 491767; SHA/checksum, tamaño y relectura reportados verificados. |
| Intervalos raw asociados a la selección v2 | 350,400,000 | Conteo aritmético sobre 10,000 Parquet validados, 35,040 filas cada uno; no implica salida Spark. |
| Bytes crudos de los diez perfiles | 64,509,497 | Suma reportada en el manifiesto de Mares; los diez crudos no están en el ZIP para repetir el cotejo local. |
| Media de bytes por perfil | 6,450,949.7 | Derivada del total reportado dividido entre 10. |

La selección propuesta se generó filtrando simulaciones exitosas con tipo declarado y peso positivo, asignando cuotas por estado y tipo RECS, y seleccionando IDs sin reemplazo con semilla `22030511`. La selección ofrece cobertura de estratos para exploración; no se presenta como una muestra probabilística representativa ni como estimador nacional.

## Proyección de almacenamiento

Si los 10,000 perfiles tuvieran el promedio observado en el piloto:

```text
10,000 × 35,040 = 350,400,000 intervalos
10,000 × 6,450,949.7 bytes ≈ 64.51 GB decimales (60.08 GiB)
```

Es una proyección lineal basada en diez perfiles de Colorado y Nueva York, no una medición del lote completo. El intervalo observado reportado por Mares fue de 5,378,721 a 7,042,415 bytes por archivo. A la capacidad de almacenamiento hay que añadir espacio temporal, archivos transformados y salidas de Spark.

La proyección inicial ya fue superada para almacenamiento raw mediante descarga directa a S3. El tamaño total exacto de los 10,000 objetos no se consigna aquí porque la adenda recibida no dio el total agregado de bytes; debe leerse del manifiesto/journal de ingesta si se requiere para una estimación de costo. Se validó después un lote piloto de 5 perfiles S3 → Spark → S3 con 21/21 QC, pero no corresponde al roster v2 de 10,000. El siguiente hito es procesar esa selección por lotes y medir bytes de entrada/salida, tiempo, memoria y QC global. No confundir la ingesta raw con procesamiento analítico.
