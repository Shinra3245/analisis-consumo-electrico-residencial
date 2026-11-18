# Plan urgente de la siguiente etapa

## Propósito y criterio de prioridad

Este plan convierte en trabajo ejecutable los cinco pendientes de integración y escalamiento. La prioridad refleja dependencias técnicas, riesgo y capacidad de desbloquear otros bloques; **no asigna fechas de entrega**. El plan sigue la propuesta V2 aprobada y las especificaciones de tablero y contratos Gold ya integradas en `main`.

### Estado de partida

- El pipeline local PySpark de Silver/Gold está integrado y ejecutado con 21/21 reglas aprobadas. Produce 10 perfiles ResStock y series EIA/clima con manifiesto de hashes.
- El prototipo web existe, pero todavía no carga como fuente de datos las salidas de ese pipeline.
- La rama de pipeline anterior del PR #4 se cerró porque su agregado Colorado/EIA no es reproducible desde los archivos versionados. La razón 87.16% no debe presentarse como precisión ni como resultado recalculado.
- La propuesta Gold define las seis vistas, pero patrones horarios locales, anomalías y pronósticos aún no tienen todas sus tablas Gold generadas.
- No hay infraestructura AWS desplegada. La región y el presupuesto máximo siguen sin decisión documentada.
- Hay 10 perfiles efectivamente procesados. La lista de 10,000 IDs es una selección candidata, no una descarga de 10,000 perfiles.

## Orden de ejecución

| Prioridad | Bloque | Dependencias principales | Estado |
|---|---|---|---|
| **P0 — Urgente, puerta de decisión** | Acordar presupuesto, región, responsable de cuenta y permisos AWS. Confirmar que la cuenta puede crear S3, EMR y Kinesis dentro del límite aprobado. | Decisión explícita del titular/equipo; estimación de costos. | Bloqueado hasta registrar los valores aprobados; no crear recursos facturables antes. |
| **P0 — Urgente, trabajo local paralelo** | Recuperar o reconstruir de forma autorizada la fuente de la comparación Colorado/EIA 2018 y hacerla reproducible. | Archivo agregado original y procedencia; o fuente autorizada equivalente. | No reproducible todavía; la salida entregada está en el repositorio, pero su agregado ResStock de origen no. |
| **P1 — Desbloquea patrones y vistas** | Normalizar timestamps ResStock a UTC y hora local IANA, preservar el timestamp fuente, y generar Gold por periodo/hora local. | Mapeo validado de perfil a estado/zona; contrato de tiempo. | Pendiente. |
| **P1 — Visible y demostrable** | Conectar el dashboard al Gold actual y completar las seis vistas incrementalmente. | Pipeline local; adaptador de datos JSON/Parquet y contrato aprobado. | Pendiente. |
| **P2 — Escalamiento** | Descargar y procesar 10,000 perfiles por lotes con procedencia y controles. | Revisión de licencia/redistribución, capacidad local/nube y estimación de almacenamiento/costo. | Pendiente; no equivale a usar los 10,000 IDs candidatos. |
| **P2 — Analítica avanzada** | Implementar y evaluar pronósticos mensuales y detección de anomalías. | Datos versionados; división temporal de evaluación; reglas y etiquetas para anomalías. | Pendiente. |
| **P2 — Despliegue objetivo** | Migrar procesamiento a EMR, replay por Kinesis, datos en S3 y publicación del tablero. | P0 aprobado; ejecución local reproducible; límites de costo y seguridad. | Pendiente; no desplegar antes de superar P0. |

P0 de la comparación, P1 de dashboard y P1 de hora local pueden trabajarse en paralelo siempre que cada salida respete el contrato y se mantengan separadas las poblaciones y zonas horarias.

## Bloque 1 — Resolver la comparación Colorado/EIA 2018

### Trabajo requerido

1. Buscar en la entrega original de Brian, el ZIP, ramas y artefactos disponibles el archivo agregado ResStock usado para los 12 valores mensuales. No sustituirlo silenciosamente por los 10 perfiles del piloto.
2. Registrar nombre, fuente, periodo, cobertura, unidad, licencia, bytes y SHA-256. Confirmar que puede conservarse y usarse para el proyecto.
3. Si el archivo no existe, obtener una entrada equivalente desde una fuente autorizada y documentar la diferencia; si no puede obtenerse, retirar la cifra 87.16% como resultado reproducido.
4. Crear un script determinista que genere la serie ResStock mensual y la serie EIA de Colorado 2018 a partir de entradas versionadas/documentadas.
5. Comprobar 12 meses, unidades, sumas y hashes; hacer que el proceso funcione desde un checkout limpio.

### Entregables

- Entrada reproducible o referencia de descarga autorizada con hash.
- Script de agregación y archivos Gold de 12 meses con manifiesto.
- Nota metodológica que describa poblaciones distintas y llame al porcentaje **razón descriptiva**, nunca precisión.

### Criterio de aceptación

Un integrante distinto de quien implementó el script puede obtener las mismas 12 filas y sumas en un checkout limpio siguiendo los comandos documentados. Si falta la fuente, se registra explícitamente como no reproducible y la cifra no se muestra como recalculada.

## Bloque 2 — Normalización horaria y patrones locales

### Trabajo requerido

1. Mantener `timestamp_end_est` como dato fuente: marca de fin de intervalo en EST fijo (UTC−05:00), sin horario de verano.
2. Derivar el inicio del intervalo (`timestamp_end_est - 15 minutos`), convertir primero de EST fijo a UTC y después a la zona IANA correspondiente al estado (`America/Denver`, `America/New_York`, etc.).
3. Derivar `period_local`, `day_type`, `hour_local` y `utc_offset_minutes` **después** de la conversión. Conservar los periodos locales parciales y marcar `is_partial_period`; no incorporarlos como meses completos.
4. Validar fechas de cambio DST, hora repetida/inexistente y límites de día, mes y año con casos conocidos.
5. Generar `gold_resstock_pattern` con una fila por perfil/periodo/tipo de día/hora/desplazamiento; guardar conteos y percentiles requeridos por la especificación.

### Entregables

- Transformación local reproducible y conjunto Gold horario.
- Pruebas de casos temporales en los dos husos incluidos (Colorado y Nueva York).
- Diccionario de campos y nota visible de zona/unidad en el tablero.

### Criterio de aceptación

Cada fila conserva el timestamp fuente y los valores UTC/local; los periodos y horas se derivan de la hora local ya convertida. Los cambios DST no duplican ni eliminan intervalos en silencio y los periodos parciales quedan identificados.

## Bloque 3 — Conectar el dashboard de seis vistas

### Trabajo requerido

1. Implementar un adaptador que lea los Parquet/JSON Gold y su manifiesto; validar versión de esquema, columnas, hashes y estado de calidad al cargar.
2. Integrar primero datos reales disponibles en **Resumen**, **Patrones** (tras Bloque 2) y **Flujo/Calidad**.
3. Integrar **Clima** como serie separada por punto mientras no exista unión geográfica/temporal aprobada.
4. Añadir **Estimaciones** solo cuando exista un backtest Gold; mostrar entrenamiento, evaluación, unidad y estado `Final`/`Preliminary`.
5. Añadir **Anomalías** solo cuando existan salidas evaluadas; marcar claramente los datos/eventos sintéticos y mostrar métricas junto a su conjunto de evaluación.
6. Conectar filtros al origen correspondiente; deshabilitar filtros que no aplican, con explicación. Validar escritorio, móvil, teclado, accesibilidad básica y consola del navegador.

### Entregables

- Dashboard local que carga datos desde el pipeline, no desde valores copiados en el HTML.
- Esquema de archivos consumidos y configuración de ruta base.
- Evidencia de cada vista, filtro y estado: carga, vacío, error y preliminar.

### Criterio de aceptación

Los valores visibles coinciden con las tablas Gold y el manifiesto; al cambiar estado, periodo o perfil cambian tanto cifras como gráficas. Ninguna vista presenta como resultado real una tabla pendiente o una métrica no calculada.

## Bloque 4 — Escalar ResStock a 10,000 perfiles

### Trabajo requerido

1. Revisar condiciones de uso, atribución y permiso de conservar/publicar perfiles y derivados. No asumir que el uso escolar elimina restricciones.
2. Definir y versionar selección por estado y tipo de vivienda, incluyendo semilla, cuotas e IDs elegidos.
3. Descargar por etapas controladas: validar primero un lote pequeño, medir bytes/tiempo/errores y decidir la siguiente escala con evidencia.
4. Registrar por archivo `bldg_id`, estado, tipo, peso, URL de origen, bytes y SHA-256; reintentar fallos sin duplicar registros.
5. Ejecutar QC de esquema, metadatos, cobertura temporal, unicidad, valores finitos/no negativos y continuidad de 15 minutos.
6. Procesar los lotes con Spark y comparar la cantidad de perfiles recibidos, aceptados, rechazados y generados en Silver/Gold.

### Entregables

- Inventario de 10,000 perfiles efectivamente descargados y manifiesto verificable.
- Reporte de QC con cuarentena de perfiles inválidos.
- Tablas Silver/Gold regenerables y costo/almacenamiento observado.

### Criterio de aceptación

El conteo de perfiles aceptados se deriva de los archivos descargados y de QC; los identificadores candidatos por sí solos no cuentan como perfiles. No presentar la muestra como representativa sin diseño muestral y pesos válidos.

## Bloque 5 — Pronósticos y anomalías

### Pronósticos

1. Usar primero ventas EIA mensuales por estado y conservar `Final`/`Preliminary`.
2. Fijar el split temporal sin fuga: entrenamiento 2018–2023, evaluación retrospectiva 2024–2025, y revisión separada de 2026 preliminar según contrato.
3. Comparar modelos candidatos con baselines estacionales; calcular MAE, RMSE y sMAPE, indicando periodos no interpretables.
4. Generar tablas Gold de predicciones, métricas y anualizados. La proyección futura debe llamarse escenario si aún no puede evaluarse.

### Anomalías

1. Definir reglas/casos: aumento, caída, faltantes y duración; decidir baseline por perfil, periodo y hora.
2. Separar señal original de casos sintéticos inyectados; guardar etiqueta y parámetros de cada caso.
3. Evaluar sin fuga entre calibración y evaluación, informar precision/recall/F1 por evento y sensibilidad a los umbrales.
4. Inspeccionar falsos positivos y casos no detectados; no llamar evento real a una inyección sintética.

### Criterio de aceptación

Resultados reproducibles con versión de código, dataset, split, parámetros y métricas. Las vistas Estimaciones/Anomalías se conectan solo después de que sus tablas Gold pasen QC y su interpretación esté documentada.

## Bloque 6 — AWS, EMR, Kinesis y S3

### Puerta de autorización obligatoria

Antes de provisionar, registrar:

- Cuenta responsable y operador autorizado.
- Presupuesto máximo del proyecto y alertas de gasto.
- Región aprobada para los recursos y confirmación de disponibilidad de EMR/Kinesis.
- Reglas de acceso, MFA, retención y eliminación de recursos de prueba.
- Decisión de publicación: qué derivados son públicos; datos crudos y capas internas permanecen privados.

Sin esos valores, se continúa el desarrollo local y **no se crean recursos facturables**.

### Implementación y entregables

1. **S3:** bucket privado, cifrado, versionado si el presupuesto lo permite, prefijos `raw/`, `silver/`, `gold/v1/` y `site/`; política de mínimo privilegio.
2. **EMR:** ejecutar el mismo job aprobado localmente sobre un lote pequeño; cotejar hashes/conteos Gold con la corrida local y registrar costo/duración.
3. **Kinesis:** crear stream de capacidad acotada para replay histórico, con `replay_id` e `ingested_at_utc`; validar idempotencia y preservar la fecha original del evento.
4. **Publicación:** exportar solo JSON aprobados para el tablero; CloudFront/OAC si se aprueba el sitio público; política de caché versionada conforme a la propuesta.
5. **Operación:** registrar logs y errores sin secretos, medir gasto y detener workers/streams al concluir pruebas; mantener evidencia de limpieza.

### Criterio de aceptación

Hay evidencia de un recorrido de lote S3 → EMR/Spark → Gold en S3, de replay Kinesis → procesamiento → Gold y de dashboard leyendo una versión publicada. Conteos/hashes coinciden con la referencia local, permisos no exponen `raw/` ni `silver/`, y el costo queda bajo el máximo aprobado.

## Dependencias y definición de cierre

```text
Decisión de presupuesto y región ──────────────┐
Fuente reproducible CO/EIA ──> comparación ────┤
Normalización UTC/local ──────> Gold patrones ──┼─> dashboard completo
Datos EIA + split validado ───> Gold forecast ─┤
Casos y evaluación ───────────> Gold anomalías ┤
Selección/descarga QC ────────> escala 10,000 ─┤
Pipeline local validado ──────> EMR/Kinesis/S3 ┘
```

No declarar una fase finalizada por tener un documento o una rama: cada bloque debe tener artefacto reproducible, comando, resultado observado, procedencia y criterio de aceptación cumplido. El estado de cierre del proyecto requiere verificar la matriz de la propuesta V2 y las instrucciones oficiales del profesor; no asumir que el plan equivale a una rúbrica adicional.
