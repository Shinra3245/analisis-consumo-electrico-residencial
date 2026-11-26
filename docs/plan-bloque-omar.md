# Plan definitivo de implementación — Bloque Omar

**Responsable:** Omar Gadiel Bolaños García.
**Base:** plan general [`plan-definitivo-general.md`](plan-definitivo-general.md), propuesta V2, `origin/main` `5572c1f` (PR #15 integrado), checkout `ui/dashboard-simplified-ui` en `5225aa2`, y evidencia AWS revalidada parcialmente el 26 de noviembre de 2026.
**Alcance:** cierre del Bloque 0, integración de la entrega ya completada de Brian, integración final del dashboard y datos, organización/publicación S3 y cierre documentado de la factibilidad cloud.
**No incluye:** reescribir, reasignar ni modificar las tareas de Christian o Diego, ni rehacer los archivos fuente del bloque de Brian.

## 1. Estado y límites que rigen este bloque

| Área | Evidencia vigente | Decisión de Omar |
|---|---|---|
| Bloque 0 | Planes v2 integrados; el 26-nov se verificó Learner Lab, región us-east-1 y S3 privado. EMR/Kinesis/CloudFront no se revalidaron. | Documentar la evidencia S3 actual; conservar para los otros servicios la última observación del 18-nov hasta revalidarlos. |
| Brian | PR #13 y #14 están mergeados. Gold v2 incluye sus 306 filas (51 jurisdicciones × seis años) dentro de 11 tablas y 20,858 filas; manifiesto: 27/27 controles aprobados con advertencias. | Su bloque está `COMPLETADO`; no se le reasigna trabajo. |
| Christian | Su alcance de clima estatal NOAA/NCEI se conserva tal como aparece en `division-bloques-equipo-v2.md`, §4. | Omar espera y revisa la interfaz de entrega; no modifica sus tareas ni su archivo. |
| Diego | Su alcance de ML estatal y anomalías ResStock se conserva tal como aparece en `division-bloques-equipo-v2.md`, §5. | Omar consume sus artefactos por contrato; no modifica sus tareas ni su archivo. |
| Datos ResStock | Gold v2 contiene 10 perfiles/350,400 intervalos; lote local de 50 reportado por separado; nueva validación runtime de ingesta/adaptador/Spark con 1 perfil y 35,040 intervalos. 10,000 IDs son candidatos. | Mantener separados los conjuntos. La prueba del job valida el flujo de una unidad, no la escala ni la meta final. |
| S3 | El 26-nov se publicaron 12 archivos Gold v2 y 2 de sitio en prefijos inmutables privados; SSE-S3 y bloqueo público verificados. Versionado deshabilitado. | Mantener la release privada y no subir crudos; no hay URL pública ni CloudFront. |
| Servicios AWS | Learner Lab activo el 26-nov. EMR Serverless, Kinesis y CloudFront no se revalidaron; su última evidencia es del 18-nov. | Revalidar permisos antes de intentar otros despliegues; no crear un stream sin consumidor ni prometer URL estable sin CloudFront/OAC. |

## 2. Cierre del Bloque 0 — estado, contratos y documentación

### 2.1 Congelar una base reproducible

1. Crear una rama nueva desde el `origin/main` más reciente; verificar que el commit incluya PR #13 y #14.
2. Mantener intactos los archivos locales sin seguimiento y cualquier material ajeno al proyecto. No usar el checkout antiguo `avance/docs-demo-s3` como si fuera el `main` actual.
3. Antes de cada integración, verificar rama, commit, `git status`, origen del PR, scope de rutas y hashes de entradas.
4. No iniciar cambios de UI/manifest desde la copia local antigua: primero portar/actualizar el trabajo sobre la base actual de `main`.

### 2.2 Publicar una sola descripción del estado real

Actualizar bajo este bloque los documentos operativos AWS y de seguimiento para que separen **observado**, **objetivo**, **denegado** y **no verificado**. La actualización futura de los documentos se limitará a sus hechos y nombres; no cambiará el alcance de Christian o Diego.

- Región observada: `us-east-1`. Reemplazar `mx-central-1` donde se describa el entorno efectivamente utilizado; si aparece como alternativa o diseño previo, etiquetarlo como tal.
- S3 observado: bucket privado, prefijos `gold/` y `site/`, ACL deshabilitadas, Block Public Access, cifrado SSE-S3. Versionado se observó **deshabilitado**; no describirlo como activado.
- Objetos S3: inventariar claves exactas, fecha, bytes, content type, hash si se dispone y si la URL temporal abrió. La guía cita un HTML de 8.5 MB y la nota del Learner Lab cita otro de 56,429 bytes; no tratarlos como el mismo artefacto sin verificar sus claves.
- URL: las URL prefirmadas son temporales. No incluirlas en Git, documentación pública, screenshots ni este repositorio.
- EMR Serverless: último resultado registrado es denegación de acceso; no se creó aplicación ni ejecutó job.
- Kinesis: formulario accesible, cero streams creados; mantenerlo sin recursos hasta que consumidor/flujo y limpieza estén listos.
- CloudFront: `ListDistributions`/acciones de lectura tuvieron `AccessDenied`; marcar como permiso parcialmente no verificado, no como despliegue ni como prohibición total.
- Budgets: consola parcial; no hay evidencia de Budget creado y no debe llamarse límite duro al medidor de Learner Lab.
- Recurso del medidor: se observó USD 0.50 de USD 50, sesión de 4 horas; el medidor puede no reflejar todos los cargos ni cortar recursos.
- Comparación Colorado/EIA 87.16%: el agregado fuente no está en `main`, por lo que se mantiene como `NO REPRODUCIDO`, no como precisión.

### 2.3 Alinear contratos y vocabulario

- Usar el nombre real de Brian: `population_density_per_sq_mi`. El texto antiguo `estimated_population_per_sq_mile` no es el campo integrado. No modificar la tabla ya mergeada.
- Mantener separadas `gold/v2/` (tablas canónicas) y `site/data/v2/` (exportaciones aprobadas para el frontend). `tablero/data/v2/` es la carpeta fuente/exportación local, no un prefijo S3 alternativo.
- Mantener `gold/v1/pilot/` intacto. No reemplazar manifest o artefactos v1.
- Corregir contradicciones sobre ResStock: 10 perfiles/350,400 intervalos en paquete Git/S3; lote 50/1,752,000 intervalos solo reportado localmente; 10,000 IDs candidatos aún no descargados/procesados.
- Corregir contradicciones de evaluación: backtest previo de 2024–2025 fue consultado. No volver a llamarlo prueba ciega o no vista. 2026 contiene meses preliminares y se debe etiquetar como tales.
- Alinear la nomenclatura del manifiesto y la especificación UI; campos y cifras deben provenir del CSV/Gold y no de valores escritos a mano.

### Criterio de cierre del Bloque 0

- [~] Evidencia del 26-nov cubre región y S3; EMR/Kinesis/CloudFront y presupuesto requieren revalidación independiente.
- [ ] Los documentos no describen como activa una arquitectura objetivo.
- [x] Los conjuntos de 10 perfiles en Gold, lote local de 50, prueba local de 1 y meta de 10,000 candidatos están separados.
- [ ] Los contratos de Brian/Christian/Diego y sus campos actuales están identificados sin duplicar tareas.
- [ ] La cifra 87.16% permanece no reproducida hasta contar con su agregado fuente verificable.

## 3. Finiquitar a Brian e integrar su entrega (Bloque 1)

### 3.1 Estado del responsable

Brian entregó el bloque por PR #13 y la corrección de reproducibilidad del PR #14; ambos se integraron a `main`. El bloque de Brian queda **COMPLETADO**: no se le reasigna nueva descarga, preparación o documentación de Census/EIA.

Artefactos aceptados:

- `datos/demografia_estatal/energy_demography_state_year_v1.csv`
- `datos/demografia_estatal/manifest.json`
- `scripts/preparar_demografia_estado.py`
- `docs/demografia-estatal.md`

### 3.2 Integración a Gold v2

1. Cargar CSV y manifiesto mediante el adaptador de integración; validar SHA-256, filas, encoding, FIPS como texto y claves únicas `(state_fips, year)`.
2. Confirmar 306 filas, 51 jurisdicciones × seis años (2020–2025), 12 meses EIA `RES` `Final` por grupo y 0 pares excluidos según el manifiesto.
3. Preservar exactamente el origen y nombres del contrato, especialmente `population_density_per_sq_mi`.
4. Generar tabla Gold v2 para la aplicación sin alterar el CSV v1. Si la tabla Gold agrega o cambia nombres, declarar el mapeo en esquema v2 y conservar claves/unidades.
5. Registrar en manifiesto: fuente/versiones, filas, bytes, hashes, fecha, commit del código generador y estado QC.
6. Mantener la superficie con precisión y la densidad derivada; el valor se calcula con el área fuente sin redondear y el CSV de entrada muestra seis decimales. El dashboard no debe presentar el pequeño residuo de recálculo como anomalía.
7. No derivar ciudades desde los datos estatales ni cruzar DC como si fuera uno de los 50 estados.

### 3.3 Integración al dashboard

- Vista **Resumen**: año seleccionado, estado más poblado, ventas residenciales totales y dato de contexto por habitante; mostrar fuente/año en cada tarjeta.
- Vista **Patrones** o subsección “Comparación estatal”: dispersión densidad (`hab./mi²`) vs ventas EIA (`kWh/persona/año`), punto = jurisdicción, tamaño = población. Tooltip: código/nombre, año, habitantes, densidad, ventas MWh y kWh/habitante.
- Rankings independientes: población total, densidad y ventas totales. DC debe aparecer con etiqueta separada; informar si el ranking se compara solo entre estados o incluye DC.
- Filtros de año 2020–2025, jurisdicción y estado de dato; la selección debe actualizar todas las cifras relacionadas.
- Incluir una explicación visible: `kWh por habitante = ventas residenciales estatales × 1,000 / población estimada`. Aclarar que es un cociente agregado, no lectura de hogares.
- Asegurar que la vista comunica que densidad y consumo per cápita son asociados/descriptivos y no demuestran causalidad.

### Criterio de cierre de integración Brian

- [x] El dashboard consume Gold v2 generado desde la tabla de Brian, no cifras manuales.
- [x] Gold v2 y su manifiesto incluyen 306 filas demográficas (51 jurisdicciones × 2020–2025); Gold v1 se conserva.
- [x] Las vistas estatales muestran población, densidad, ventas totales y ventas por habitante, con DC separado y aclaraciones de alcance.
- [~] Falta repetir una revisión independiente de filtros e interacciones después de integrar las entregas pendientes del equipo.

## 4. Integrar los trabajos existentes de Christian y Diego sin modificar su asignación

1. Recibir cada PR hacia `main`; revisar rutas, contrato, fuentes, unidades, periodo, hashes, cobertura y criterios ya establecidos en `division-bloques-equipo-v2.md`.
2. No editar sus rutas ni reescribir sus tareas para acelerar el dashboard. Si el contrato entregado difiere, detener la integración de esa interfaz y registrar el mapeo requerido antes de tocar frontend.
3. Tras el merge del clima de Christian, cargar solo filas NOAA/NCEI estatales por `(state_fips, period)`; mantener la muestra Open-Meteo de dos puntos en Colorado como tabla separada.
4. Tras el merge de Diego, revisar que sus resultados distingan baseline, ML, holdout, preliminares y anomalías sintéticas/candidatas; adaptar solo el loader/manifest del dashboard.
5. No integrar como resultado de producción un modelo que no tenga comparación de baselines y partición temporal explicada.
6. La evaluación final usa los datos realmente entregados; si el clima llega después del entrenamiento o no comparte cobertura, el dashboard lo presenta como contexto separado en vez de imputar o forzar un join.

## 5. Resolver el objetivo de escala ResStock

La meta de la propuesta V2 es 10,000 perfiles; 10,000 IDs en el índice no cuentan como perfiles. El objetivo de Omar es coordinar la ingestión y verificar escala; las tareas analíticas específicas del detector siguen dentro del bloque de Diego.

### Pasos de implementación

1. Reusar el índice/manifiesto de candidatos y el método de selección ya existente; confirmar cobertura por estado, estrato y tipo de vivienda antes de descargar. Documentar semilla, cuotas, pesos y limitaciones de representatividad.
2. Medir una descarga controlada con conteo de archivos, bytes, tiempo y tasa de error. Extrapolar recursos/costo a 10,000 solo a partir de esos datos medidos.
3. Confirmar que los archivos y derivados que se usarán cumplen la decisión de atribución/licencia registrada en `docs/decision-publicacion-datos.md`; no subir automáticamente el crudo a S3.
4. Descargar por lotes idempotentes; crear roster inmutable con ID, estado, estrato, vivienda, fuente, bytes, hash y estado del archivo. Un reintento no debe duplicar perfiles.
5. Validar esquema, intervalos esperados, unidades, continuidad, rangos, nulos, IDs del roster y huellas; enviar perfiles inválidos a cuarentena con causa.
6. Ejecutar Spark local por particiones; comparar contadores leídos/aceptados/rechazados y Gold agregada por estrato. No cargar 350.4 millones de filas en memoria del navegador.
7. Revisar perfiles y métrica de cobertura con una etiqueta `muestra seleccionada`; no afirmar representatividad poblacional sin pesos/diseño de muestra sustentado.
8. Publicar solamente derivados autorizados y resumidos; mantener el perfil individual y datos crudos privados/no versionados si la autorización o la utilidad del dashboard no justifican publicarlos.

### Criterios de cierre de escala

- [ ] Hay 10,000 archivos/perfiles únicos realmente descargados y aceptados, o un reporte exacto de qué número se aceptó y por qué faltó el resto. Los IDs candidatos no cuentan.
- [ ] El roster y manifiesto reproducen conteos, bytes y SHA-256; el lote puede procesarse por Spark sin cargarlo como payload web.
- [ ] El reporte separa los 10 perfiles incluidos en Git, el lote local reportado de 50 y la nueva selección final.
- [ ] El alcance y representatividad se describen sin sobreprometer.
- [ ] Un resultado incompleto se etiqueta como tal; no se afirma que la meta V2 se alcanzó por tener 1,752,000 intervalos.

## 6. Dashboard final y paquete de datos Gold v2

### Trabajo del frontend e integración

1. Crear `tablero/data/v2/` como contrato de publicación, manteniendo `tablero/data/v1/` intacto.
2. Definir un `manifest.json` v2 que registra cada tabla, esquema, versión, grano, clave primaria, unidad, rango temporal, filas, bytes, SHA-256, generación, entrada/commit y QC.
3. Exportar tablas pequeñas como JSON determinista para el navegador. El Parquet canónico puede mantenerse en Gold privado; no cargar perfiles crudos completos en el cliente.
4. Mantener las seis vistas existentes, pero no habilitar una visualización vacía como si fuera completa:
   - **Resumen:** alcance, datos disponibles y cifras demográficas/energéticas por estado-año.
   - **Patrones:** perfiles ResStock, tiempo local y agregados válidos; no espacios/habitaciones que no existan en el dataset.
   - **Clima:** NOAA estatal mensual y la muestra Open-Meteo puntual, claramente separadas.
   - **Anomalías:** candidatos observados y evaluación sintética en secciones distintas.
   - **Estimaciones:** backtest y proyección con fechas/origen/unidades claros.
   - **Flujo/Calidad:** fuentes, conteos, hashes, vigencia, QC y procedencia.
5. Para cada filtro indicar fuente, campo afectado, unidad y rango; filtros no aplicables se deshabilitan con explicación.
6. Probar en navegador local escritorio/móvil, tabla ausente, hash inválido, estado sin datos, preliminar, error de carga y teclado; el sitio debe indicar versión/fecha y no simular carga en vivo.
7. Generar visual final de vivienda isométrica conceptual solo para la vista de perfiles; identificarla como ilustración, nunca como planta o dato medido por habitación.

### Criterios de cierre dashboard/Gold

- [ ] Las seis vistas usan datos de manifiesto v2 y explican qué muestran, fuente, geografía, periodo y unidad.
- [ ] Las tablas del manifest pasan validación de esquema/filas/hash antes de renderizarse.
- [ ] Los filtros cambian números y gráficas desde los datos, con casos vacíos/preliminares explicados.
- [ ] La visualización no mezcla 10,000 IDs candidatos con perfiles procesados ni ventas EIA con perfiles ResStock.
- [ ] No existe cifra de pronóstico/anomalía sin la tabla Gold y la métrica que la respalda.

## 7. S3 organizado y despliegue AWS

### 7.1 Organización del bucket

Conservar el bucket privado y el prefijo ya existente `gold/v1/pilot/`. Organizar nuevas salidas usando una relación exacta entre artefactos locales y S3:

```text
raw/<fuente>/<corte>/                     # solo cuando conservación/redistribución estén permitidas
silver/eia/<schema-version>/
silver/resstock/<schema-version>/
silver/clima/<schema-version>/
gold/v1/pilot/                             # existente; no sobrescribir
gold/v2/demografia/<release-id>/
gold/v2/clima/<release-id>/
gold/v2/analitica/<release-id>/
site/releases/<release-id>/index.html
site/data/v2/<tabla>-<sha256>.json
site/data/v2/manifest.json
checkpoints/<replay-id>/                   # solo ejecución streaming de duración limitada
```

No crear prefijos de archivos crudos por decoración: solo poblar carpetas que correspondan a objetos reales y autorizados. Cada carga revisa su contenido, MIME, cifrado, acceso y hash. El `manifest.json` se publica al final, no antes de que existan los objetos de la release.

### 7.2 Prueba final de la web S3

1. Verificar localmente el dashboard y el empaquetador contra manifest v2.
2. Generar un `release-id` nuevo; no sobrescribir archivos históricos.
3. Decidir el paquete según host disponible:
   - Con CloudFront/OAC operativo, publicar HTML y JSON versionados en `site/`, mantener el bucket privado y entregar HTTPS estable.
   - Sin CloudFront, empaquetar solo los datos autorizados en HTML autónomo y abrir una URL prefirmada desde S3 para la demostración. Esa URL expira y no es despliegue permanente.
4. Abrir exactamente el objeto recién cargado desde un navegador sin sesión AWS; verificar vistas, tablas, filtros y consola. Documentar resultado, hora, release y hash sin guardar la URL temporal.
5. Mantener una ruta local reproducible. Nunca habilitar acceso público a todo el bucket para resolver un error de carga.

### 7.3 EMR, Kinesis y procesamiento

- Reintentar EMR Serverless solo después de confirmar estado/permisos actuales y tener el job local cerrado y medido; si repite `AccessDenied`, registrar acción/servicio/fecha y mantener Spark local como procesamiento efectivo. No afirmar que el pipeline está en EMR.
- Verificar si existe otra opción de Spark administrado permitida por el lab; no asumir que Glue/EC2 están habilitados ni crear recursos de costo sin evaluación acotada.
- Crear Kinesis solamente cuando exista un consumer preparado, contrato de evento, retención, límite de mensajes/duración y método para cerrar stream, job y checkpoint. El productor debe marcar el lote como replay y preservar `event_time`/`ingested_at_utc`.
- Validar que el lote recibido y escrito a S3 coincida con el manifest local; contar duplicados, rechazados y tardanza.
- Si EMR o Kinesis quedan denegados, publicar lo que sí se ejecutó (Spark local + outputs derivados autorizados en S3) y señalar expresamente qué parte del flujo cloud no se ejecutó.

### 7.4 Costo, sesión y seguridad

- La nota del lab informa sesión de 4 horas, medidor `USD 0.50 / USD 50` observado y ausencia de un límite duro. El valor no equivale a un Budget ni garantiza que AWS detenga recursos antes de cargos.
- Antes de cada acción, revisar consumo; estimar bytes/requests/duración; usar el umbral interno prudente anotado en la viabilidad (USD 5 adicionales estimados/observados para el siguiente bloque), consciente de que no es protección automática.
- No dejar workers, streams, endpoints, buckets de prueba o checkpoints innecesarios. Tras ejecutar, comprobar cleanup y medir de nuevo.
- S3 debe seguir privado, con SSE-S3, ACL deshabilitadas y Block Public Access. Si versioning sigue denegado/deshabilitado, usar claves inmutables versionadas y registrar esa limitación; no presentarlo como habilitado.
- Nunca incorporar account ID, ARN, credentials, archivos de sesión, pre-signed URLs, emails privados o capturas con información sensible.

### Criterios de cierre cloud

- [ ] Los prefijos y su contenido corresponden a capas y releases documentadas; el nombre del bucket se protege en el repo público.
- [ ] El sitio final fue probado desde la URL/endpoint realmente disponible y el resultado visual fue verificado.
- [ ] Se documenta como hecho solo lo que se creó/ejecutó; denegaciones se acompañan con evidencia no sensible.
- [ ] Cualquier URL temporal se describe como tal y se conserva una ejecución local reproducible.
- [ ] Se puede explicar claramente la ruta implementada: insumos → Spark efectivo → Gold → JSON/web; el flujo Kinesis/EMR aparece con su estado real.

## 8. Secuencia de trabajo de Omar

1. Obtener checkout limpio desde el `main` integrado y preservar los archivos locales sin seguimiento.
2. Cerrar inventario del Bloque 0 y alinear los documentos de estado sin modificar tareas de Christian/Diego.
3. Verificar hashes/manifiesto de Brian (bloque concluido) y producir integración demográfica Gold v2.
4. Implementar visualización estatal-demográfica y contrastarla con la tabla source antes de agregar otra fuente.
5. Recibir los PRs de Christian y Diego cuando estén listos; revisarlos por sus contratos actuales y no editar sus responsabilidades.
6. Integrar clima y salidas de modelo/anomalía al paquete v2; resolver de forma escrita el split ya observado y condiciones de inferencia.
7. Coordinar selección y procesamiento de 10,000 perfiles como alcance de escala V2; medir, usar roster y Spark, mantener crudos privados si corresponde.
8. Validar las seis vistas completas, manifiesto, filtros, accesibilidad, escritorio/móvil y ausencia de datos estáticos copiados.
9. Publicar Gold/JSON/web con prefijos versionados; verificar endpoint real y registrar S3/EMR/Kinesis/CloudFront estado por estado.
10. Crear PR de Omar hacia `main` con diagrama implementado, manifest, screenshots sin secretos, comandos y checklist de aceptación; integrar solo tras pasar revisión.

Los pasos de escala, build y publicación son actividades internas del producto final; no habilitan presentar un MVP como cierre.

## 9. Checklist de cierre del Bloque Omar

**Leyenda:** `[x]` completado con evidencia; `[~]` parcial o pendiente de revalidación; `[ ]` pendiente.

### Bloque 0

- [~] El checkout parte del `origin/main` vigente y conserva archivos locales ajenos; los cambios del bloque siguen en la rama local, pendientes de push/PR.
- [~] Región y S3 tienen evidencia fechada del 26-nov; EMR/Kinesis/CloudFront y presupuesto aún reflejan la observación del 18-nov.
- [~] Los planes distinguen 10 perfiles Gold, lote de 50 reportado y meta de 10,000; falta alinear todos los documentos de estado/analítica.
- [x] El 87.16% se mantiene como no reproducido, no como precisión ni métrica validada.

### Brian / demografía

- [x] Su bloque está registrado como completo con referencia a PR #13/#14.
- [x] Gold v2 incluye las 306 filas del CSV real; la vista estatal presenta año, unidades y categorías.
- [x] DC y rankings se presentan por separado, con límites de interpretación explícitos.

### Producto, escala y AWS

- [ ] Christian y Diego se integran al dashboard sin reescribir sus tareas ni código fuera del bloque Omar.
- [ ] ResStock llega a meta V2 de 10,000 perfiles aceptados con QC, o se reporta con claridad la meta no lograda y la evidencia del bloqueo.
- [ ] Forecast ML y anomaly outputs están probados/reproducidos y las limitaciones/splits visibles.
- [x] El dashboard local tiene seis vistas que consumen Gold v2; pruebas sintéticas se identifican como tales y los candidatos no se presentan como eventos confirmados.
- [x] S3 contiene el paquete Gold v2 con manifiesto y el HTML autónomo, publicados bajo prefijos privados de release.
- [ ] La URL estable existe solo si CloudFront/OAC quedó realmente desplegado; de otro modo se declara S3 prefirmado temporal y se conserva ruta local.
- [ ] EMR/Kinesis se marcan con resultado verificado; no se representa como cloud la ejecución Spark local.
- [ ] Diagrama, fuente/cortes, hashes, comandos, atribución y guía para profesor son reproducibles.

## 10. Entrega del trabajo de Omar

Rama única desde el `main` actualizado, PR acotado a la integración y nube, commits descriptivos y verificación independiente. El cuerpo del PR debe incluir:

- Cierre del Bloque 0 y cambios de reconciliación documental.
- Referencia a Brian #13/#14 y prueba de la integración de su tabla.
- Referencias a PRs de Christian/Diego sin apropiarse de sus archivos.
- Tablas/manifest v2, cobertura, bytes, hashes y controles.
- Evidencia del dashboard local y endpoint cloud en versión final.
- Servicios AWS ejecutados, denegados y no verificados, con costos observados cuando existan.
- Limitaciones pendientes explícitas; no afirmar el cierre integral de un requerimiento cuyo criterio no se cumplió.
