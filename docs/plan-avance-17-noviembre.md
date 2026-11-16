# Plan de tareas para la revisión de avance

**Preparación:** lunes 16 de noviembre de 2026  
**Exposición:** martes 17 de noviembre de 2026  
**Meta de hoy:** llegar a la exposición con evidencia pequeña, reproducible y honesta del trabajo iniciado. Este es un plan de preparación para la revisión académica, no una afirmación de que el sistema esté terminado.

## Acuerdo de alcance para mañana

Mostrar: problema y propuesta V2 aprobada; fuentes seleccionadas y estado real de validación; un ejemplo de datos o metadatos si se obtiene hoy; flujo de procesamiento propuesto; prototipo simple de salida; división de responsabilidades, riesgos y próximos pasos.

No afirmar como realizado: integración de las tres fuentes, 350.4 millones de filas procesadas, flujo en vivo, modelos evaluados, tablero conectado a datos, despliegue en AWS ni costos medidos, salvo que el equipo complete y guarde evidencia hoy.

## Tareas de hoy por integrante

| Integrante | Tarea concreta hoy | Evidencia que debe dejar | Condición de cierre |
|---|---|---|---|
| Brian Garcia Mares (22030511) | Revisar ResStock, EIA y Open-Meteo. Para cada fuente confirmar la página/documentación oficial, acceso actual, periodo/cobertura, granularidad, formato, licencia/condiciones y forma de descarga. Intentar obtener una muestra pequeña de al menos una fuente sin subir archivos grandes al repo. | Completar `docs/estado-fuentes-17-nov.md` con enlaces, fecha de consulta, campos observados y pendientes; guardar solo muestra autorizada o metadatos, con tamaño/hash si procede. | Cada fuente queda marcada `verificada`, `parcial` o `no verificada`, con evidencia y bloqueo específico; no inferir atributos que no se vieron. |
| Omar Gadiel Bolaños García (22030591) | Coordinar tiempos y contratos entre responsables. Preparar un diagrama sencillo de arquitectura/flujo, una agenda de exposición de 5–7 minutos y actualizar el README/enlaces del repo. Reunir el estado de cada tarea y dejar un respaldo ejecutable o navegable. | Diagrama Markdown/Mermaid en `docs/arquitectura-propuesta.md` o archivo enlazado; agenda y checklist en `docs/seguimiento.md`; commit con los entregables integrados. | Cada integrante confirma su evidencia; la demo abre desde instrucciones del repositorio y distingue claramente propuesta de implementación. |
| Christian Raul Páramo Bautista (22031149) | Definir contrato mínimo del dato y controles de calidad para el primer flujo: ubicación, fecha/hora y zona horaria, variable, valor, unidad, tipo de fuente y perfil/grupo. Si Brian obtiene muestra, inspeccionarla y producir un resumen básico; si no, entregar especificación sin inventar resultados. | `docs/esquema-y-calidad.md` con campos, tipos/unidades por confirmar, reglas de faltantes/duplicados/rangos, y tabla de inspección de muestra solo si existe. | El equipo puede explicar cómo se detectarían inconsistencias y qué metadatos faltan antes de unir fuentes. |
| Diego Emilio Ortiz Vilchez (22030642) | Diseñar un prototipo de tablero o boceto de baja fidelidad con secciones previstas y un ejemplo claramente marcado como ilustrativo; definir una línea base para anomalías (p. ej., desviación respecto al patrón horario del grupo) y qué necesitaría evaluarse. No entrenar ni reportar métricas sin datos. | Boceto/captura o prototipo local en `docs/prototipo-tablero.md`/`docs/`; ficha de método con entrada, salida, criterio inicial y plan de evaluación. | La visualización identifica fuente, unidad y periodo como campos aún por completar; el método se presenta como diseño, no como resultado evaluado. |

La asignación usa nombres y matrículas tal como aparecen en la propuesta V2.

## Secuencia y coordinación

1. **Ahora (15 minutos):** confirmar responsables, compartir el plan y acordar un canal rápido de coordinación.
2. **Primer bloque de trabajo:** Brian revisa fuentes; Christian prepara el esquema; Diego prepara el boceto; Omar define el formato común y la estructura de la presentación.
3. **Punto de integración (aprox. 2 horas después):** cada integrante comparte evidencia y bloqueos. Christian y Diego adaptan sus entregables a los campos realmente observados por Brian.
4. **Cierre de hoy:** integrar Markdown, revisar enlaces, ensayar la demo y anotar qué quedó parcial o pendiente. Hacer respaldo del material de exposición.
5. **Mañana antes de exponer:** abrir la presentación, repo y demo desde el equipo que se utilizará; revisar que no haya secretos ni datos cuya publicación esté restringida.

Los horarios son relativos porque no conocemos la disponibilidad de cada integrante. El equipo debe compartirlos y ajustar los intervalos sin mover la fecha objetivo.

## Guion sugerido para la exposición

1. Problema, objetivo y aprobación de la propuesta V2 (45 s).
2. Fuentes y cobertura que ya se verificó; pendientes de acceso/licencia (1 min).
3. Flujo/arquitectura y contrato de datos (1 min).
4. Evidencia de muestra, metadatos o prototipo disponible (1–2 min).
5. Método previsto de análisis, anomalías y estimaciones, separando diseño de resultados (1 min).
6. Reparto de trabajo, riesgos y siguiente hito (1 min).

Registrar preguntas del profesor y acuerdos en [`seguimiento.md`](seguimiento.md) al terminar.

## Criterio de éxito de la preparación

- Cada integrante presenta un artefacto o una limitación respaldada por evidencia.
- La exposición responde qué se aprobó, qué se construyó, qué falta y qué sigue.
- Los datos modelados, estadísticas oficiales, reproducción histórica y datos en vivo no se confunden.
- No se muestran resultados numéricos sin archivo, cálculo y método reproducibles.
