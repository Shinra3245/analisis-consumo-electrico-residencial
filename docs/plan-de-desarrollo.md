# Plan de desarrollo del proyecto

## Base académica y calendario

El documento del curso `Proyecto-Final.pdf` indica periodo agosto-diciembre de 2026, proyecto final con valor de 50 puntos, equipos de cuatro, revisión de avance el martes 17 de noviembre y presentación final el 30 de noviembre o el 1 de diciembre. Solicita subir a Google Classroom código, base de datos y documentación. La propuesta tiene fecha de entrega del 15 de octubre. El profesor aprobó la segunda versión sin observaciones pendientes, según la confirmación comunicada por el equipo.

La plantilla `Big Data Project Proposal Template.pdf` contiene 12 secciones: resumen ejecutivo, objetivos SMART, justificación, alcance, requisitos, arquitectura, fuentes/metodología, cronograma, equipo, riesgos, métricas y conclusión. Incluye ejemplos de fases de 24 semanas y metas técnicas ilustrativas; no son fechas ni umbrales obligatorios del curso. La guía de proyecto disponible no presenta una rúbrica detallada con ponderaciones por apartado. Si el profesor comparte una rúbrica o instrucciones adicionales, este plan debe actualizarse.

## Calendario de entrega

| Fecha | Hito | Resultado verificable |
|---|---|---|
| 16 nov 2026 | Preparar revisión de avance | Demo ejecutable con datos disponibles, arquitectura, estado real, riesgos y siguientes pasos. No atribuir a la revisión requisitos que no aparecen en la guía. |
| 17 nov 2026 | Exposición de avance en clase | Presentar el progreso real y respaldarlo con código, datos y documentación; registrar comentarios y acciones. |
| 18–20 nov 2026 | Consolidar fuentes y flujo inicial | Inventario validado, descarga reproducible, esquema y controles de calidad iniciales. |
| 21–24 nov 2026 | Procesamiento y análisis | Transformaciones reproducibles, indicadores descriptivos y primer método de anomalías con evaluación. |
| 25–27 nov 2026 | Estimaciones y tablero | Comparación con línea base, métricas, visualizaciones integradas y pruebas de extremo a extremo. |
| 28–29 nov 2026 | Congelar y preparar entrega | Correcciones, documentación final, instrucciones de ejecución, respaldo y ensayo de exposición. |
| 30 nov o 1 dic 2026 | Presentación final | Demostración, resultados, límites, arquitectura, contribución de integrantes y preguntas. Confirmar con el profesor qué fecha corresponde al equipo. |
| Según indicación del curso | Carga en Google Classroom | Código, base de datos o artefactos de datos permitidos, y documentación. Confirmar formato, ubicación y hora límite. |

Este calendario es una propuesta intensiva construida con las fechas disponibles, no un calendario oficial del profesor. El equipo debe reducir alcance antes que presentar funciones sin validar. Primero se comprobará acceso, licencia, tamaño y esquema de ResStock, EIA y Open-Meteo; si una fuente no está disponible a tiempo, se documentará y se ajustará el análisis conservando la distinción entre datos modelados y oficiales.

## División inicial por integrante

La asignación organiza responsabilidades principales; los cuatro integrantes deben revisar interfaces, decisiones y entrega final. Cada bloque debe producir un resultado integrado y revisable.

| Integrante | Responsabilidad principal | Entregables y evidencia |
|---|---|---|
| Brian Garcia Mares (22030511) | Datos y fuentes | Verificar acceso, términos, cobertura, formatos y esquema de las fuentes; preparar inventario y extracción reproducible; guardar metadatos y cifras reales de descarga. |
| Omar Gadiel Bolaños García (22030591) | Coordinación técnica e integración | Mantener repositorio, issues/PR, estructura, entorno reproducible e integración; consolidar arquitectura y documentación; coordinar demo y registro de decisiones. |
| Christian Raul Páramo Bautista (22031149) | Procesamiento y calidad | Diseñar esquema normalizado, limpieza, controles de calidad y agregaciones; documentar reglas, pruebas de datos y resultados de volumen/tiempo. |
| Diego Emilio Ortiz Vilchez (22030642) | Analítica y visualización | Implementar análisis descriptivo, método de anomalías y línea base de estimación; definir evaluación; construir tablero y visualizaciones de resultados. |

### Trabajo compartido y revisiones cruzadas

- Brian y Christian acuerdan formato de entrada, unidades, zonas horarias y contratos de datos antes de integrar.
- Christian entrega tablas agregadas con diccionario de campos; Diego valida que las visualizaciones representen correctamente sus unidades y cobertura.
- Diego documenta método, particiones de evaluación, métricas y límites; Brian revisa procedencia y significado de los datos usados.
- Omar integra y publica incrementos; cada responsable revisa al menos un PR de otro integrante y contribuye a la presentación.
- Todos confirman alcance, resultados y limitaciones antes de marcar una función como terminada.

## Priorización

### Imprescindible para una entrega académica defendible

1. Confirmar que se pueden obtener y usar las fuentes seleccionadas; dejar un plan alternativo si falla alguna.
2. Crear extracción o preparación reproducible y documentar linaje, unidades, fechas y cobertura.
3. Presentar análisis descriptivo correcto y claramente separar perfiles modelados de estadísticas oficiales.
4. Implementar al menos un método sencillo de anomalías y una línea base de estimación, con evaluación y limitaciones explícitas.
5. Integrar tablero o visualización demostrable, repositorio reproducible e instrucciones de ejecución.
6. Medir volumen real, tiempos y costos observados. No prometer disponibilidad, latencia o precisión antes de medirlas.

### Ampliaciones sujetas a tiempo y costo

- Procesamiento continuo real con Kinesis; para la exposición puede bastar la reproducción histórica prevista, correctamente etiquetada.
- Ejecución en EMR/S3; usar primero un entorno local o datos pequeños mientras se definen presupuesto y controles. No activar recursos con costo sin aprobación explícita del equipo.
- Más de un método de anomalías, modelos complejos o cobertura detallada de los 50 estados.
- Actualización automatizada y despliegue público del tablero.

## Criterios de aceptación del proyecto

- Cada fuente utilizada tiene procedencia, fecha/periodo, licencia o condiciones de uso, unidades, cobertura y volumen efectivo documentados.
- La preparación se puede repetir con instrucciones del repositorio, o sus limitaciones están registradas con precisión.
- Los datos crudos no se alteran; cambios sintéticos para probar anomalías se hacen en copias y quedan identificados.
- Cada indicador muestra periodo, grupo, unidad y tipo de dato apropiados.
- Las anomalías y estimaciones se comparan con una referencia o partición de evaluación; se reportan métricas acordes a la tarea.
- La demostración de históricos se identifica como reproducción y no como lectura en vivo de medidores.
- La documentación de Classroom incluye código, datos autorizados o esquema/instrucciones para obtenerlos, y resultados reproducibles.
- La presentación explica alcance, arquitectura, contribuciones, evidencia, riesgos y trabajo pendiente sin inventar resultados.

## Ritmo de coordinación

- Reunión breve diaria durante la semana de cierre: progreso, evidencia, bloqueo y siguiente entrega.
- Actualizar [`seguimiento.md`](seguimiento.md) al cerrar cada bloque; registrar decisiones y comentarios de la revisión del 17 de noviembre.
- Trabajar mediante ramas y pull requests pequeños. Definición de terminado: integrado en `main`, documentación actualizada y comprobación reproducible anotada.
- Revisar fecha, hora, modalidad y formato de presentación/carga directamente con el profesor, ya que la guía solo ofrece el 30 de noviembre y el 1 de diciembre sin asignar equipo.
