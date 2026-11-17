# Catálogo de datos del proyecto (revisado)

Versión revisada de la entrega de Brian García Mares (22030511), consultada el 17 de noviembre de 2026. Estados: **Confirmado**, **Pendiente**, **No verificado**. Términos y matriz de publicación: [decision-publicacion-datos.md](decision-publicacion-datos.md). El ZIP original no se incluye; se copiaron los artefactos derivados cuyo hash fue verificado.

## Alcance real de lo descargado

| Concepto | Estado |
|---|---|
| 10,000 perfiles ResStock | **Selección propuesta** (identificadores y URL), no descargada. |
| Perfiles ResStock descargados y validados | **10** (piloto, Colorado y Nueva York, 64,509,497 bytes crudos). Los 10,000 no están descargados. |
| Volumen estimado de 10,000 perfiles | Proyección de 350,400,000 intervalos y 64.51 GB crudos, extrapolada del piloto de 10; **no verificada**. |
| Crudos enumerados en el manifiesto | **Pendiente:** el ZIP no los contiene; solo hashes y URL. |

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

Texto de atribución ResStock: «Data includes information from the ResStock™ dataset developed by the National Renewable Energy Laboratory (NREL) with funding from the U.S. Department of Energy (DOE).» Open-Meteo y C3S: ver decisión.

## Verificación pendiente

La relación de 87.16% entre ResStock y EIA de Colorado 2018 es un resultado reportado en el CSV integrado, no recalculado desde el agregado crudo ausente del ZIP. Compara poblaciones y métodos distintos; no es una validación. La cobertura EIA sí se reprodujo desde el XLSX oficial.
