# Seguimiento del proyecto

Este archivo establece cómo registrar avances y decisiones. El plan de desarrollo y el reparto inicial están en [`plan-de-desarrollo.md`](plan-de-desarrollo.md); el equipo debe confirmar y ajustar la asignación.

## Registro de hitos

| Fecha | Hito o decisión | Responsable(s) | Evidencia/enlace | Estado |
|---|---|---|---|---|
| 2026-10-19 | Propuesta V2 preparada para revisión docente | Equipo | Documento de propuesta local | Completado |
| Fecha no registrada | Aprobación de la propuesta V2 | Equipo | Confirmación del profesor | Completado, sin observaciones |
| 2026-11-16 | Repositorio público y documentación inicial | Omar | README y documentos base | Completado |
| 2026-11-16 | Plan inicial de desarrollo, fechas y responsables | Equipo | [Plan de desarrollo](plan-de-desarrollo.md) | Propuesto para coordinación del equipo |
| 2026-11-16 | Plan de preparación para revisión del 17 de noviembre | Equipo | [Plan de avance](plan-avance-17-noviembre.md) | Propuesto para ejecutar hoy |
| 2026-11-16 | Investigación inicial de fuentes | Claude | [Validación inicial](validacion-inicial-fuentes.md) | Completado; pendiente revisión del equipo |
| 2026-11-16 | Esquema y controles conceptuales iniciales | Antigravity (AGY) | [Esquema inicial](esquema-inicial-calidad-datos.md) | Completado; pendiente revisión del equipo |
| 2026-11-16 | Recomendación inicial de alcance del MVP | Equipo | [Decisión de alcance](decision-alcance-mvp.md) | Propuesta técnica para revisar después de la exposición; basada en revisión documental, sin descarga de datos |
| 2026-11-16 | Primera muestra empírica y validación reproducible | Equipo | [Resultados](resultados-muestra-inicial.md), [script](../scripts/analizar_muestra_inicial.py) | Completado localmente; agregado ResStock, EIA mensual y Open-Meteo; fuentes originales excluidas de Git |
| 2026-11-16 | Contenido resumido de presentación por diapositiva | Equipo | [JSON editable](contenido-presentacion-avance.json), [versión legible](presentacion-avance-17-noviembre.md) | Contenido actualizado; falta aplicar el estilo visual que entregará el usuario. El PowerPoint/PDF anterior quedan como borradores |
| 2026-11-17 | Consolidación de artefactos, gobernanza y guía técnica del piloto | Equipo; insumos de Brian García Mares | [Catálogo](catalogo-datos-final.md), [contrato](contrato-datos-v1.md), [decisión de publicación](decision-publicacion-datos.md), [guía Spark](ejecucion-piloto-datos.md), [viabilidad](viabilidad-resstock-10000.md) | Integrado a `main` mediante PR #2 (merge `fc02f2f3`); una sola copia de datos, hashes cotejados, reproducción EIA y límites de evidencia documentados |
| 2026-11-18 | Primer despliegue del demostrador en Learner Lab | Equipo | [Demo S3](despliegue-s3-demo.md), [viabilidad](viabilidad-learner-lab.md) | Bucket privado, web estática y artefactos Gold cargados; URL prefirmada temporal verificada; región observada us-east-1; EMR Serverless denegado, Kinesis sin stream creado, CloudFront con lectura parcial denegada y sin distribución verificada; sin evidencia de AWS Budget. Evidencia del 18-nov, no revalidada |
| 2026-11-26 | Release privada Gold v2 y dashboard autónomo en S3 | Omar; Antigravity | [Guía de publicación S3](publicacion-s3-dashboard-v2.md), [gobernanza](decision-publicacion-datos.md) | 14 archivos derivados en `gold/v2/releases/` y `site/releases/`; Content-Type y SSE-S3 verificados, Block Public Access conservado. No se generó URL prefirmada ni se desplegó CloudFront |
| 2026-11-26 | Prueba de ingesta, adaptador y Spark con 50 perfiles | Omar; Claude | [Ingesta por lotes](ingesta-resstock-lotes.md), [adaptador Spark](adaptador-lote-resstock-spark.md), [job Spark local](ejecucion-job-spark-local.md) | 50/50 aceptados, 1,752,000 intervalos ResStock; 21/21 QC y hashes cotejados. Resultado local bajo `/tmp`; al cierre de esa corrida quedaban 9,950 IDs sin intentar. Después, la ingesta raw v2 completó 10,000 en S3; Spark a escala 10,000 sigue pendiente |
| 2026-11-26 | Auditoría AWS y publicación de salida Spark de 1 perfil | Omar; Antigravity | [Viabilidad Learner Lab](viabilidad-learner-lab.md), [guía de publicación S3](publicacion-s3-dashboard-v2.md) | 7 archivos derivados bajo un prefijo privado, con 5 marcadores `_SUCCESS` de Spark (12 objetos S3 en total); Content-Type, SSE-S3 y bloqueo público verificados. 0 Budgets, 0 streams Kinesis; EMR y CloudFront denegados en las acciones revisadas; no se alteró configuración |
| 2026-11-26 | Cierre verificable de auditoría y límites en AWS Learner Lab | Omar; Antigravity | [Viabilidad Learner Lab](viabilidad-learner-lab.md), [Demo S3](despliegue-s3-demo.md) | Confirmación formal de permisos lectura/creación: EMR Serverless denegado (`AccessDeniedException`), CloudFront denegado (`AccessDenied`), Kinesis 0 streams (lectura permitida; creación omitida por ausencia de consumidor cloud), S3 privado íntegro y protegido. Medidor constante en USD 1.20 / USD 50 (USD 0.00 adicional; 0% del umbral de USD 5). Arquitectura cerrada en S3 privado + cómputo local reproducible |
| 2026-11-26 | Ingesta raw final ResStock Scale-10k en S3 privado | Omar; Antigravity | [Decisión selección final v2](decision-seleccion-resstock-final-v2.md), [Ingesta S3](ingesta-resstock-s3-privado.md) | 10,000 Parquet únicos aceptados (9,998 primarios + 432862 y 491767), 35,040 filas por perfil, checksum/SHA-256, tamaño y relectura verificados; dos perfiles originales con energía negativa aislados. Raw completado; Spark/QC/Silver/Gold de la selección v2 aún no ejecutados |
| 2026-11-26 | Prueba real S3 → Spark → S3 con 5 perfiles | Omar; Antigravity | [Procesamiento por lotes](procesamiento-resstock-s3-lotes.md) | CloudShell con Spark 4.0.1: 175,200 filas Silver y 60 Gold mensual; 21/21 QC aprobadas; 4 objetos derivados verificados con checksum/readback y marca de commit. Solo lote piloto, no demuestra 10,000 procesados ni actualiza el dashboard Gold |

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
