# Plan de tareas para la revisión de avance

**Preparación:** lunes 16 de noviembre de 2026  
**Exposición:** martes 17 de noviembre de 2026  
**Meta de hoy:** llegar a la exposición con evidencia pequeña, reproducible y honesta del trabajo iniciado. Este es un plan de preparación para la revisión académica, no una afirmación de que el sistema esté terminado.

## Acuerdo de alcance para mañana

Mostrar: problema y propuesta V2 aprobada; fuentes seleccionadas y estado real de validación; un ejemplo procesado de ResStock/EIA; controles aplicados; visualización exploratoria; riesgos, límites y próximos pasos. El [guion actualizado](presentacion-avance-17-noviembre.md) contiene los datos observados.

No afirmar como realizado: integración de las tres fuentes, 350.4 millones de filas procesadas, flujo en vivo, modelos evaluados, tablero conectado a datos, despliegue en AWS ni costos medidos, salvo que el equipo complete y guarde evidencia hoy.

## Tareas documentales para el avance parcial

| Agente | Tarea concreta | Evidencia | Alcance para la exposición |
|---|---|---|---|
| Claude | Hacer una verificación documental inicial de ResStock, EIA y Open-Meteo con enlaces oficiales y registrar qué se confirmó y qué falta comprobar. | [`validacion-inicial-fuentes.md`](validacion-inicial-fuentes.md) | Investigación preliminar: sin descarga de datasets ni confirmación de tamaños o cobertura que no se haya observado. |
| Antigravity (AGY) | Proponer un esquema conceptual pequeño y controles de calidad candidatos, marcando como pendientes los campos, unidades y frecuencias que requieren inspeccionar datos reales. | [`esquema-inicial-calidad-datos.md`](esquema-inicial-calidad-datos.md) | Diseño preliminar: no es pipeline ni resultado medido; queda sujeto a corrección al obtener muestras. |

Las tareas de esta iteración se asignaron a agentes para producir evidencia inicial; no asignan responsabilidades permanentes entre los cuatro integrantes. El equipo revisará ambos documentos antes de presentarlos.

## Secuencia y coordinación

1. **Hoy:** revisar los dos documentos, sus enlaces y las etiquetas de confirmado/pendiente.
2. **Antes de la exposición:** acordar qué hallazgos mostrar y quién presenta cada sección, sin convertir esa distribución en una asignación permanente de desarrollo.
3. **Mañana:** explicar la propuesta aprobada, el estado de las fuentes, el esquema conceptual inicial y las limitaciones; registrar preguntas y próximos pasos.

El plan original cubría el avance documental de los dos agentes. Después se añadió una muestra empírica y un análisis local; el desarrollo técnico seguirá después de recibir comentarios del profesor.

## Guion sugerido para la exposición

1. Problema, objetivo y aprobación de la propuesta V2 (45 s).
2. Qué se pudo verificar sobre las fuentes y qué sigue pendiente (1 min).
3. Esquema conceptual y controles de calidad propuestos (1–2 min).
4. Limitaciones actuales: todavía no hay muestra integrada ni procesamiento implementado (45 s).
5. Siguientes etapas hasta fin de mes y preguntas del profesor (1 min).

Registrar preguntas del profesor y acuerdos en [`seguimiento.md`](seguimiento.md) al terminar.

## Criterio de éxito de la preparación

- Cada integrante presenta un artefacto o una limitación respaldada por evidencia.
- La exposición responde qué se aprobó, qué se construyó, qué falta y qué sigue.
- Los datos modelados, estadísticas oficiales, reproducción histórica y datos en vivo no se confunden.
- No se muestran resultados numéricos sin archivo, cálculo y método reproducibles.
