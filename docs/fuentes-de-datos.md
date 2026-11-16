# Fuentes de datos y validación

Las fuentes siguientes son las previstas en la propuesta aprobada. Su presencia en este documento no significa que ya se hayan descargado, que sus términos permitan redistribución ni que su cobertura se haya validado para todos los análisis.

| Fuente | Aplicación prevista | Validaciones pendientes |
|---|---|---|
| ResStock 2025.1 | Perfiles residenciales modelados, características de vivienda y resúmenes estatales | Acceso a archivos, licencia/uso, esquema, cobertura estatal, periodo meteorológico 2018, granularidad de 15 minutos, variables disponibles y tamaño real. |
| EIA | Series mensuales/anuales de consumo residencial por estado y demanda horaria del sistema | Endpoints/archivos disponibles, sectores, estados cubiertos, unidades, fechas, retrasos de publicación, límites de consulta y atribución requerida. |
| Open-Meteo | Temperatura y otras variables meteorológicas | Términos de uso, variables, resolución espacial/temporal, disponibilidad histórica/previsión y alineación de zona horaria. |

## Procedimiento de incorporación

Para cada extracción se registrarán fuente, URL o identificador, fecha de consulta, versión, periodo, cobertura, unidades, formato, licencia/atribución, cantidad de registros y hash del archivo original. Se conservarán los datos crudos sin alteraciones y las transformaciones se ejecutarán en copias reproducibles.

Antes de combinar fuentes se comprobarán claves de ubicación y tiempo, zonas horarias, unidades, valores faltantes, duplicados y cambios de esquema. Las mediciones oficiales y los perfiles modelados permanecerán diferenciados en almacenamiento, transformaciones y visualizaciones.

## Volumen de referencia

La propuesta estima al menos 10,000 perfiles con registros de 15 minutos para un año, aproximadamente 350.4 millones de filas. Se validará la fórmula y el volumen real según perfiles disponibles, faltantes, periodo cubierto y formato descargado. No publicar datos fuente en el repositorio hasta confirmar que su licencia permite redistribución; preferir scripts, metadatos y muestras autorizadas.
