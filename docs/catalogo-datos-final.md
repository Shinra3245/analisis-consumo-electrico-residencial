# Catálogo de datos del proyecto (revisado)

Versión revisada de la entrega de Brian García Mares (22030511), consultada el 17 de noviembre de 2026. Estados: **Confirmado**, **Pendiente**, **No verificado**. Términos y matriz de publicación: [decision-publicacion-datos.md](decision-publicacion-datos.md). El ZIP original no se incluye; se copiaron los artefactos derivados cuyo hash fue verificado.

## Corte inicial de la entrega revisada (17-nov-2026)

| Concepto | Estado |
|---|---|
| Selección de 10,000 perfiles ResStock | **Candidatos**, no descargados en ese corte. |
| Perfiles ResStock descargados y validados | **10** del piloto, Colorado y Nueva York (64,509,497 bytes crudos). |
| Volumen de 10,000 perfiles | Proyección inicial de 350,400,000 intervalos y 64.51 GB crudos, extrapolada del piloto; no era una medición. |
| Archivos crudos enumerados en el manifiesto del ZIP | No incluidos en el ZIP; solo se registraban sus hashes y URL. |

**Estado actualizado (26-nov-2026):** la selección final v2 fue descargada y validada en S3 privado: 10,000 perfiles únicos, 35,040 filas cada uno. Este corte inicial no describe el estado actual. Para la selección final y su evidencia consulte [`decision-seleccion-resstock-final-v2.md`](decision-seleccion-resstock-final-v2.md). El procesamiento Spark/QC Silver/Gold de los 10,000 sigue pendiente. La proyección de 64.51 GB es histórica y no debe presentarse como tamaño medido del conjunto final.

## Inventario

| Fuente | Periodo | Contenido | Estado |
|---|---|---|---|
| ResStock 2025 Release 1, AMY 2018, `upgrade=0` | 2018 | Metadatos de 549,971 modelos reportados; Parquet piloto de 10 perfiles, 35,040 filas por ID; agregado de Colorado unifamiliar aislado reportado | Parquet piloto leído y controles de esquema/frecuencia/valores completados. Índice nacional y agregado no se reprodujeron desde crudos, que no venían en el ZIP. |
| EIA-861M `Monthly-States` | 2018–2025 finales, ene–ago 2026 preliminares | Ventas mensuales por estado, sector RES (MWh); 5,304 registros | Reproducido desde el XLSX oficial del corte; 4,896 registros finales y 408 preliminares. |
| Open-Meteo Historical Weather API (ERA5-Land) | 1–7 enero 2018 UTC | 336 horas-punto, 168 por punto, Denver y Grand Junction, temperatura a 2 m en °C | Filas, cobertura y hash cotejados; JSON crudos no estaban en el ZIP, por lo que no se reobtuvieron valores desde la respuesta fuente. |
| EIA-930 | Por definir | Contexto de red | Previsto; sin extracción |

## Uso, publicación y atribución

Cada fila cita fuentes oficiales en el documento de decisión; aquí solo el resumen.

| Fuente | Confirmado | Pendiente / no verificado | Decisión provisional |
|---|---|---|---|
| ResStock | `citation.txt` del release indica CC BY 4.0. El README pide citar dataset/guía y usar la atribución NREL/DOE. «For research purposes only» aparece en un apartado `Disclaimer` junto a las condiciones “as is” y ausencia de garantía. | Conservar el disclaimer al compartir y mantener el uso en el proyecto académico autorizado. | Muestra, selección y derivados integrados con atribución, licencia y cambios; enlace a la fuente para recuperar crudos completos. |
| EIA | https://www.eia.gov/about/copyrights_reuse.php: publicaciones en dominio público, se pueden usar y distribuir; pide acuse con fecha de publicación. | No hay página específica del XLSX con términos propios. Material de terceros en el sitio tiene copyright. | Derivados y muestra publicables con atribución. |
| Open-Meteo / ERA5-Land | Los datos API son CC BY 4.0; ERA5-Land en CDS también muestra CC-BY. | El endpoint gratuito es no comercial, con límites de llamadas; la muestra procede de dos puntos y no se integró con energía. | CSV publicable e integrado con Open-Meteo/C3S, enlaces de licencia y cambios declarados. |
| EIA-930 | Misma política EIA. | Sin extracción ni verificación. | N/A |
| Uso en el proyecto | — | El profesor autorizó utilizar la información necesaria para el proyecto. | Uso académico; mantener atribución, licencia y disclaimer de cada fuente. |

Las tablas EIA, la muestra climática y cuatro artefactos derivados ResStock están integrados con procedencia y hashes en [`datos/`](../datos/README.md). EIA se reobtuvo desde el XLSX oficial y se reprodujo byte a byte con [`scripts/preparar_eia.py`](../scripts/preparar_eia.py); el XLSX no se conserva en el repo. Para el contrato técnico por fuente, ver [`contrato-datos-v1.md`](contrato-datos-v1.md).

## Campos de interés y análisis posterior

| Fuente/archivo | Campos | Significado y uso |
|---|---|---|
| ResStock individual (`resstock_perfiles_piloto.parquet`) | `bldg_id`, `timestamp_fin_local`, `electricidad_kwh` | ID del modelo, fin del intervalo de 15 minutos y energía modelada en kWh. El timestamp almacenado no incluye offset; la documentación de la fuente indica EST fijo. Mantener esa semántica y no convertirlo a UTC sin una regla explícita. |
| ResStock selección (`resstock_seleccion_propuesta.csv`) | `bldg_id`, `estado`, `tipo_vivienda`, `condado_codigo`, `peso_viviendas`, `upgrade`, `url` | Candidatos y metadatos para seleccionar perfiles. `condado_codigo` se conserva como texto de origen; algunos valores son nombres descriptivos, no un identificador GIS uniforme. |
| EIA (`eia_residencial_mensual.csv`) | `periodo`, `estado`, `sector`, `estado_dato`, `ventas_mwh` | Mes, estado, sector residencial, condición `Final`/`Preliminary` y ventas agregadas en MWh. Conservar el estado del dato. |
| Open-Meteo (`clima_open_meteo_muestra.csv`) | `punto_id`, coordenadas, `timestamp_utc`, `temperatura_c`, `modelo` | Temperatura horaria en dos puntos; no representa todo Colorado ni está unida a ResStock. |

Como propuesta de evaluación temporal para EIA, se puede reservar 2018–2023 para ajuste, 2024 para validación y 2025 para prueba final, manteniendo enero–agosto de 2026 como preliminar. Es una división recomendada, no un entrenamiento o evaluación ya ejecutados. Para detalles de lectura con Spark, consultar la [guía del piloto](ejecucion-piloto-datos.md). La [nota de viabilidad de 10,000 perfiles](viabilidad-resstock-10000.md) distingue las cifras reportadas del piloto de la proyección de escala.

La cifra de 87.16% es descriptiva y se recibió como resultado del artefacto de Colorado del ZIP de Mares; no se recalculó aquí desde el agregado ResStock crudo, que no venía en el ZIP. Compara dos coberturas distintas y no debe presentarse como precisión o validación del modelo.

Texto de atribución ResStock: «Data includes information from the ResStock™ dataset developed by the National Renewable Energy Laboratory (NREL) with funding from the U.S. Department of Energy (DOE).» Open-Meteo y C3S: ver decisión.

## Verificación pendiente

La relación de 87.16% entre ResStock y EIA de Colorado 2018 es un resultado reportado en el CSV integrado, no recalculado desde el agregado crudo ausente del ZIP. Compara poblaciones y métodos distintos; no es una validación. La cobertura EIA sí se reprodujo desde el XLSX oficial.
