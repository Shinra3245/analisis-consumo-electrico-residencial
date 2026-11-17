# Viabilidad de la selección de 10,000 perfiles ResStock

Fuente indicada por la entrega de Mares: ResStock 2025 Release 1, AMY 2018, baseline `upgrade=0`. Esta nota separa datos disponibles, cifras reportadas por el integrante y proyecciones. La lista de selección y cobertura están en [`datos/`](../datos/README.md); los archivos crudos no se incluyeron en el ZIP recibido.

## Estado y cifras del piloto

| Medida | Valor | Evidencia/estado |
|---|---:|---|
| Candidatos de metadatos nacionales | 549,971 | Reportado en el manifiesto de la entrega; índice crudo ausente en el ZIP. |
| Estados/D. C. con cobertura | 51 | Reportado en la entrega. |
| Estratos estado × tipo de vivienda con candidatos | 254 | Coincide con filas en `resstock_cobertura_estratos.csv`. |
| IDs en la selección propuesta | 10,000 | Archivo integrado; son candidatos, no perfiles descargados. |
| Perfiles en el Parquet integrado | 10 | Conteo y esquema del artefacto integrados. |
| Filas del Parquet piloto | 350,400 | 35,040 por perfil. |
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

Antes de ampliar la descarga, conviene medir un lote intermedio con más estados y tipos de vivienda, comprobar tiempos y espacio temporal, y después decidir el tamaño final con el presupuesto de nube. La generación de 10,000 candidatos no implica haber descargado los 10,000 perfiles.
