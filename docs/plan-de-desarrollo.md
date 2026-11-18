# Plan de desarrollo del proyecto

## Base académica y requisitos

El documento del curso `Proyecto-Final.pdf` establece un equipo de cuatro, un proyecto final con valor de 50 puntos, y subir a Google Classroom el código, la base de datos y la documentación. También prohíbe el plagio. El profesor aprobó la segunda versión sin observaciones pendientes, según la confirmación comunicada por el equipo.

La plantilla `Big Data Project Proposal Template.pdf` contiene secciones para objetivos, justificación, alcance, requisitos, arquitectura, fuentes/metodología, equipo, riesgos y métricas. Incluye ejemplos de fases y metas técnicas ilustrativas; no son requisitos adicionales del curso. La guía disponible no presenta una rúbrica detallada con ponderaciones por apartado. Si el profesor comparte otros criterios, se agregan a la matriz de aceptación. El trabajo se ordena por requisitos, dependencias y evidencias, no por fechas de entrega.

## Secuencia de implementación por requisitos

| Fase | Trabajo | Evidencia para avanzar |
|---|---|---|
| Requisitos y alcance | Trazar la propuesta V2 con requisitos del curso; marcar qué está implementado, pendiente o condicionado. | Matriz de trazabilidad, criterios de aceptación y decisiones explícitas. |
| Fuentes y contratos | Verificar procedencia, licencias, cobertura, unidades, esquemas y zonas horarias. | Catálogo, manifiestos, contratos y muestra medida. |
| Preparación local | Implementar extracción reproducible, controles y transformaciones sobre una muestra. | Conteos/hash cotejados, reporte de calidad y salidas repetibles. |
| Cloud foundation | Acordar cuenta, acceso, región y presupuesto; preparar S3/IAM/observabilidad privada. | Estimación aprobada, permisos mínimos y evidencia de configuración segura. |
| Procesamiento distribuido | Llevar los mismos jobs a Spark/EMR para batch y al replay acotado con Kinesis. | Salidas cotejadas con local, métricas de carga, costo y cierre de recursos. |
| Analítica y tablero | Evaluar anomalías y estimaciones; conectar los resultados Gold a las vistas. | Métricas reproducibles, filtros conectados a datos y explicación de cobertura/unidades. |
| Aceptación y entrega | Ejecutar recorridos E2E, revisar accesos/costos y preparar código, datos permitidos y documentación. | Runbook, diagrama implementado, evidencias y paquete Classroom completo. |

Cada fase comienza cuando sus dependencias están comprobadas. Si alguna fuente o componente no es viable, se registra la limitación y se propone un ajuste de alcance antes de presentar resultados como completos.

La implementación seguirá la [decisión inicial de alcance del MVP](decision-alcance-mvp.md): empezar por muestras verificables y ampliar solo con inventario, licencia, tamaño y pruebas medidos. Esto organiza el orden de trabajo sin reemplazar los objetivos de la propuesta aprobada.

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

### Requisitos esenciales para completar el proyecto

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

## Coordinación e integración

- Revisar avances por fase: progreso, evidencia, bloqueo y siguiente dependencia.
- Actualizar [`seguimiento.md`](seguimiento.md) al cerrar cada bloque y registrar decisiones/evidencias.
- Trabajar mediante ramas y pull requests pequeños. Definición de terminado: integrado en `main`, documentación actualizada y comprobación reproducible anotada.
