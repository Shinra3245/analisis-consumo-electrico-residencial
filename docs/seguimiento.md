# Seguimiento del proyecto

Este archivo establece cómo registrar avances y decisiones. El plan de desarrollo y el reparto inicial están en [`plan-de-desarrollo.md`](plan-de-desarrollo.md); el equipo debe confirmar y ajustar la asignación.

## Registro de hitos

| Fecha | Hito o decisión | Responsable(s) | Evidencia/enlace | Estado |
|---|---|---|---|---|
| 2026-10-19 | Propuesta V2 preparada para revisión docente | Equipo | Documento de propuesta local | Completado |
| Pendiente | Aprobación docente | Equipo | Confirmación del profesor | Completado, sin observaciones |
| 2026-11-16 | Repositorio público y documentación inicial | Omar | README y documentos base | Completado |
| 2026-11-16 | Plan inicial de desarrollo, fechas y responsables | Equipo | [Plan de desarrollo](plan-de-desarrollo.md) | Propuesto para coordinación del equipo |
| 2026-11-16 | Plan de preparación para revisión del 17 de noviembre | Equipo | [Plan de avance](plan-avance-17-noviembre.md) | Propuesto para ejecutar hoy |
| 2026-11-16 | Investigación inicial de fuentes | Claude | [Validación inicial](validacion-inicial-fuentes.md) | Completado; pendiente revisión del equipo |
| 2026-11-16 | Esquema y controles conceptuales iniciales | Antigravity (AGY) | [Esquema inicial](esquema-inicial-calidad-datos.md) | Completado; pendiente revisión del equipo |
| 2026-11-16 | Recomendación inicial de alcance del MVP | Equipo | [Decisión de alcance](decision-alcance-mvp.md) | Propuesta técnica para revisar después de la exposición; basada en revisión documental, sin descarga de datos |
| 2026-11-16 | Primera muestra empírica y validación reproducible | Equipo | [Resultados](resultados-muestra-inicial.md), [script](../scripts/analizar_muestra_inicial.py) | Completado localmente; agregado ResStock, EIA mensual y Open-Meteo; fuentes originales excluidas de Git |
| 2026-11-16 | Contenido resumido de presentación por diapositiva | Equipo | [JSON editable](contenido-presentacion-avance.json), [versión legible](presentacion-avance-17-noviembre.md) | Contenido actualizado; falta aplicar el estilo visual que entregará el usuario. El PowerPoint/PDF anterior quedan como borradores |
| 2026-11-17 | Piloto individual de ResStock, cobertura multianual EIA, muestra climática y catálogo | Brian García Mares | [Ejecución y conteos](ejecucion-piloto-datos.md) | Piloto verificado localmente; revisión del equipo e integración pendientes |

## Actualización de avances

Cada actualización debe indicar:

- qué se completó y quién participó;
- evidencia verificable (PR, commit, archivo, captura o resultado reproducible);
- cambios en alcance, supuestos, datos o decisiones;
- bloqueos y siguiente paso concreto.

Los estados sugeridos son `Pendiente`, `En curso`, `En revisión`, `Completado` y `Bloqueado`. Usar `Completado` solo cuando exista evidencia revisable.

## Registro de decisiones

Para decisiones importantes, anotar fecha, pregunta, alternativas consideradas, decisión, razón, impacto y responsables. Cambios a la propuesta aprobada deben quedar explicados y, si afectan el compromiso académico, consultarse con el profesor.

## Organización colaborativa

- Crear ramas breves para cambios y abrir pull requests hacia `main`.
- Describir el propósito y las comprobaciones de cada pull request.
- Mantener la documentación sincronizada con el comportamiento real.
- No incluir credenciales, datos personales innecesarios ni datos fuente sin permiso de redistribución.
