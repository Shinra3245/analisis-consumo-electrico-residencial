# Reporte de calidad y rendimiento Spark

Fecha: 2026-11-17T19:52:38-06:00

## Entorno

- Apache Spark: 4.1.1
- Ejecucion: local en Windows
- Periodo: Colorado, 2018
- Fuentes: ResStock y EIA

## Registros y tiempos

| Dataset | Filas | Tamaño (MiB) | Tiempo (s) |
|---|---:|---:|---:|
| ResStock Bronze | 35,040 | 19.068 | 4.473 |
| ResStock Silver | 35,040 | 0.592 | 0.487 |
| ResStock Gold | 12 | 0.003 | 0.345 |
| EIA Bronze | 12 | 0.002 | 0.297 |
| EIA Silver | 12 | 0.002 | 0.308 |
| EIA Gold | 12 | 0.003 | 0.301 |
| Comparacion | 12 | 0.003 | 0.276 |
| Rechazados ResStock | 0 | 0.001 | 0.343 |
| Rechazados EIA | 0 | 0.001 | 0.257 |

## Resultados de calidad

- Rechazados ResStock: 0
- Rechazados EIA: 0
- Conservacion de conteos Bronze/Silver: correcta
- Meses Gold: 12 por fuente

## Totales anuales

- ResStock: 16,809,653.30 MWh
- EIA: 19,286,952.00 MWh
- Relacion entre totales: 87.16%

## Alcance y limitaciones

- Los tiempos corresponden a lectura y conteo de Parquet en esta ejecucion local; no representan el tiempo total de construccion del pipeline.
- Los tamaños corresponden a las carpetas de salida.
- Los controles aplicados no sustituyen una auditoria completa de las 96 columnas originales.
- ResStock y EIA representan coberturas diferentes; la relacion porcentual no mide precision.
- Pendientes: pruebas con datos sinteticos invalidos, escala y rendimiento en AWS, y streaming con Kinesis.
