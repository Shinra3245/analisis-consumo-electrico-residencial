# Fuentes de datos y validación

Las fuentes siguientes son las previstas en la propuesta aprobada. Su presencia en este documento no significa que ya se hayan descargado, que sus términos permitan redistribución ni que su cobertura se haya validado para todos los análisis.

| Fuente | Aplicación prevista | Validaciones pendientes |
|---|---|---|
| ResStock 2025.1 | MVP: agregados geográficos y metadatos/anuales; perfiles individuales sujetos a prueba de tamaño | Revisar inventario, licencia/uso, esquema, cobertura, granularidad, variables y tamaños de los archivos candidatos. |
| EIA | MVP: serie residencial oficial por estado y periodo; demanda horaria EIA-930 opcional como contexto de red | Elegir archivo/API, confirmar sectores, estados, unidades, fechas, retrasos, clave de API si aplica y atribución. |
| Open-Meteo | MVP: muestra histórica pequeña de temperatura y variables complementarias justificadas | Confirmar términos para uso académico, variables, resolución, disponibilidad histórica y alineación de zona horaria. |

El orden y los límites del primer MVP están registrados en [`decision-alcance-mvp.md`](decision-alcance-mvp.md). La priorización no cambia las metas generales de la propuesta aprobada.

Se procesó una primera muestra local reproducible de Colorado (ResStock, ventas EIA y temperatura histórica de Denver). El detalle de inventario, comprobaciones, cifras y límites de comparación está en [`resultados-muestra-inicial.md`](resultados-muestra-inicial.md). Los archivos originales se mantienen bajo `data/raw/`, ignorados por Git.

## Procedimiento de incorporación

Para cada extracción se registrarán fuente, URL o identificador, fecha de consulta, versión, periodo, cobertura, unidades, formato, licencia/atribución, cantidad de registros y hash del archivo original. Se conservarán los datos crudos sin alteraciones y las transformaciones se ejecutarán en copias reproducibles.

Antes de combinar fuentes se comprobarán claves de ubicación y tiempo, zonas horarias, unidades, valores faltantes, duplicados y cambios de esquema. Las mediciones oficiales y los perfiles modelados permanecerán diferenciados en almacenamiento, transformaciones y visualizaciones.

## Volumen de referencia

La propuesta estima al menos 10,000 perfiles con registros de 15 minutos para un año, aproximadamente 350.4 millones de filas. Se mantiene como meta de escala a validar, no como requisito para el primer incremento. El MVP comienza con un subconjunto cuyo volumen se medirá. No publicar datos fuente hasta confirmar que su licencia permite redistribución; preferir scripts, metadatos y muestras autorizadas.
