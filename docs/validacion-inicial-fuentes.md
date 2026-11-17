# Validación inicial de fuentes

Revisión inicial para la exposición del 17 de noviembre, actualizada con la inspección de una muestra. **Fecha de actualización: 16 de noviembre de 2026.** Es una validación acotada, no exhaustiva. Se descargaron tres objetos pequeños para análisis local; no se registró cuenta ni clave de API y los originales quedan excluidos de Git.

Leyenda: **Confirmado** = visto en la fuente oficial citada. **No confirmado** = no se encontró o no se comprobó. **Pendiente** = por hacer.

## Matriz

| Aspecto | ResStock 2025.1 | EIA | Open-Meteo |
|---|---|---|---|
| Fuente oficial / documentación | [Data ResStock](https://natlabrockies.github.io/ResStock.github.io/docs/data.html); [FAQ de ResStock](https://natlabrockies.github.io/ResStock.github.io/docs/FAQ.html); [guía técnica 2025.1](https://oedi-data-lake.s3.amazonaws.com/nrel-pds-building-stock/end-use-load-profiles-for-us-building-stock/2025/resstock_amy2018_release_1/ResStockTechnicalReferenceGuide_2025_1.pdf) | [Datos EIA-861M](https://www.eia.gov/electricity/data/eia861m/); [detalle de datos EIA](https://www.eia.gov/electricity/data/detail-data.php) | [Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api); [términos de uso](https://open-meteo.com/en/terms) |
| Propósito en el proyecto | Perfiles residenciales modelados, características de vivienda y resúmenes por estado | Series mensuales/anuales por estado y demanda horaria del sistema | Temperatura y otras variables meteorológicas |
| Acceso comprobado | **Confirmado:** se listó el prefijo de agregados por estado para `upgrade=0`, Colorado: cinco archivos por tipo de vivienda (27.0–31.0 MB). Se descargó localmente solo `up00-co-single-family_detached.csv` (31,004,915 bytes) para la prueba. | **Confirmado:** se descargó el libro oficial mensual `sales_revenue.xlsx` (2,280,162 bytes), hoja `Monthly-States`; se extrajeron 12 registros finales de Colorado para 2018. No se usó la API ni se solicitó clave. | **Confirmado:** consulta histórica de una ubicación de Denver para 2018, `temperature_2m`, respondió 8,760 filas horarias en GMT sin faltantes. Se conserva localmente fuera de Git. La consulta usó el modelo predeterminado `Best Match`, que combina productos meteorológicos. |
| Cobertura | **Confirmado (documentación del release):** los 50 estados y D.C.; el año meteorológico AMY es 2018. La muestra es solo Colorado y vivienda unifamiliar separada. La guía describe 550,000 muestras del conjunto, sin recuento propio del inventario. | **Confirmado en muestra:** Colorado, sector residencial, 2018-01 a 2018-12, todos `Final`. No se validaron todos los estados/rutas ni la demanda de red. | **Confirmado en consulta:** una ubicación (Denver), año 2018. No se validó cobertura del estado completo. |
| Granularidad | **Confirmado en muestra:** 35,040 marcas únicas consecutivas a 15 minutos; timestamps de cierre de intervalo en EST. La guía técnica estima unos 500 GB de salida para 550,000 muestras sin mejoras. | **Confirmado en muestra:** 12 observaciones mensuales; EIA-861M reporta ventas en MWh por estado y sector. | **Confirmado en consulta histórica:** horaria, temperatura a 2 m en °C y zona solicitada GMT; es reanálisis, no observación directa de estación. |
| Formato | **Confirmado en la muestra:** CSV; 96 columnas, archivo de 31,004,915 bytes. No se inspeccionaron otros formatos. | **Confirmado en la muestra:** libro XLSX de 2,280,162 bytes, hoja `Monthly-States`; la API REST requeriría clave y no se usó. | **Confirmado:** JSON; respuesta de 208,313 bytes. |
| Licencia / atribución | **Confirmado parcialmente:** el registro general del bucket OEDI indica CC BY 3.0 US; la página de ResStock pide cita y atribución a ResStock/NLR y DOE. Revisar siempre si hay aviso específico más restrictivo en el release. Los originales no se suben al repositorio. | **Pendiente:** revisar términos de reutilización y atribución de EIA. | **Confirmado (términos):** uso gratuito no comercial, datos bajo CC BY 4.0 y límites de llamadas. La prueba asume uso académico no comercial; comprobar con el equipo antes de publicación externa. |
| Avisos de la fuente | **Confirmado (README):** 82 columnas de resultados se omitieron de este release y no se añadirán (cargas por componente y carga de respaldo de bomba de calor). Los agregados de las mejoras 29–32 no están en `timeseries_aggregates/`. | — | — |

## Pendientes

1. **ResStock:** revisar el aviso de columnas del release/`KNOWN_ISSUES.md`, confirmar en el equipo la atribución y reproducir la descarga con el script. La muestra valida solo el agregado de Colorado para vivienda unifamiliar separada.
2. **EIA:** revisar términos/atribución y decidir si el libro mensual es la serie oficial que se conservará para comparar estados y meses. La API queda innecesaria para el primer MVP.
3. **Open-Meteo:** confirmar que el uso académico no comercial encaja en los términos. Elegir una cobertura espacial representativa y resolver el cambio horario antes de cualquier unión con ResStock.
4. **Comunes:** ampliar controles de calidad y registrar linaje con el procedimiento de [fuentes-de-datos.md](fuentes-de-datos.md); resultados actuales en [muestra inicial](resultados-muestra-inicial.md).

## Limitaciones de esta revisión

- Las páginas de ResStock se leyeron desde documentación oficial de NLR y OEDI. Se inspeccionó un agregado por estado; no se descargó el conjunto completo ni se inspeccionaron series individuales por vivienda.
- No se revisó aún la atribución y reutilización específica exigida por EIA ni el aviso de columnas del release ResStock.
- La granularidad de 15 minutos se verificó también en el archivo de muestra. La escala de 550,000 muestras/~500 GB solo se verificó en la guía técnica, no en una descarga. La cifra de 350.4 millones de filas para 10,000 perfiles es una proyección aritmética de la propuesta, no una cantidad observada.
- Los términos de uso pueden cambiar; la fecha de consulta es la referencia.
