# Arquitectura AWS por etapas

**Estado:** diseño técnico para el demostrador académico. No se han creado recursos, no se aprobó presupuesto y no se desplegó esta arquitectura.

## 1. Qué pide el curso y qué compromete la propuesta

`Proyecto-Final.pdf` confirma equipos de cuatro, valor de 50 puntos, exposiciones el 30 de noviembre o 1 de diciembre de 2026, entrega de código, base de datos y documentación en Google Classroom, y la prohibición de plagio. El documento no contiene una matriz técnica con criterios y ponderaciones. La plantilla `Big Data Project Proposal Template.pdf` orienta el formato de la propuesta; sus ejemplos no son requisitos adicionales del profesor.

La propuesta V2 aceptada por el profesor compromete el uso de **Amazon S3**, **Amazon Kinesis Data Streams**, **Apache Spark en Amazon EMR** y un tablero interactivo. También plantea análisis de consumo, detección de anomalías, estimaciones y reproducción progresiva de históricos identificada como simulación. Por ello este diseño conserva esos componentes, pero acota su ejecución a una demostración medible. No supone que los 10,000 perfiles o los 350.4 millones de intervalos ya estén procesados.

## 2. Arquitectura objetivo

```mermaid
flowchart LR
  SRC[ResStock, EIA y Open-Meteo] --> ING[Adquisición versionada y manifiesto]
  ING --> S3RAW[S3 privado: raw]
  S3RAW --> EMRB[EMR Serverless: Spark batch]
  EMRB --> S3CUR[S3 privado: bronze / silver / gold/v1]
  S3CUR --> SITE[S3 privado: sitio y exportaciones JSON aprobadas]
  SITE --> CF[CloudFront con OAC]
  CF --> WEB[Tablero estático]
  S3CUR --> PROD[Productor acotado de replay histórico]
  PROD --> KDS[Kinesis Data Streams]
  KDS --> EMRS[EMR Serverless: Spark Structured Streaming]
  EMRS --> S3OUT[S3: resultado del replay y checkpoint]
  S3OUT --> SITE
  OBS[CloudWatch: logs y métricas] -.-> EMRB
  OBS -.-> EMRS
  COST[AWS Budgets y revisión de facturación] -.-> EMRB
  COST -.-> KDS
```

### Componentes y límites

| Componente | Diseño propuesto | Límite del demostrador |
|---|---|---|
| S3 | Un bucket dedicado al proyecto, privado, con prefijos `raw/`, `bronze/`, `silver/`, `gold/v1/`, `checkpoints/` y `site/data/v1/`. Gold guarda Parquet canónico; el sitio contiene solo exportaciones JSON aprobadas. Manifiestos registran fuente, fecha, hash, esquema y versión del código. | Subir solo una muestra seleccionada y derivados autorizados. Habilitar versionado; no sobrescribir datos de entrada ni salidas de una publicación ya emitida. |
| Spark batch en EMR Serverless | Un job de corta duración lee la muestra desde S3, valida el contrato y produce Silver/Gold Parquet en `gold/v1/`; genera además JSON versionado para el tablero en `site/data/v1/`. El mismo código se desarrolla primero en local. | Configurar máximo de trabajadores, vCPU, memoria y almacenamiento temporal. Una ejecución pequeña, medición, parada y revisión antes de ampliar. |
| Replay con Kinesis | Productor de prueba lee un segmento histórico ya validado y envía eventos con `replay_id`, `event_time` original, `ingested_at_utc`, `sequence`, fuente y `is_replay=true`. | Límite de eventos y duración configurables; comenzar con una prueba pequeña. El evento de fin del lote debe permitir detener el consumidor Spark; no dejar un stream infinito activo. |
| Spark Structured Streaming | Job EMR Serverless consume Kinesis, aplica el esquema y controles, y escribe resultados idempotentes a S3 con checkpoint específico del `replay_id`. | Una reproducción acotada; cancelar/parar tras recibir el marcador de fin y verificar el resultado antes de limpiar el checkpoint. |
| Tablero | Conservar la web estática existente y sustituir datos embebidos por `site/data/v1/manifest.json` y exportaciones JSON con nombre basado en SHA-256. CloudFront entrega la página y únicamente esos JSON. | Publicar exclusivamente `site/` revisado; Gold en `gold/v1/` queda privado y no se sirve directamente. Nunca exponer `raw/`, `bronze/`, `silver/` ni checkpoints. |
| Observabilidad | CloudWatch Logs para jobs, métricas de filas leídas/escritas, rechazadas, eventos de Kinesis y duración. Etiquetas `project`, `environment`, `owner` y `expires_at` donde el servicio las soporte. | Retención corta explícita para logs de prueba; registrar estimación y costo observado por ejecución. |

## 3. Seguridad y publicación

- Mantener **S3 Block Public Access** habilitado. Para la página, usar CloudFront con Origin Access Control (OAC), un origen S3 REST (no endpoint de website estático) y una política de bucket limitada a esa distribución y a `site/*`. No dar a CloudFront acceso a `gold/v1/`: Gold permanece privado y se publica solo mediante exportaciones explícitamente aprobadas. AWS recomienda OAC para servir una web desde S3 sin hacer público el bucket y conservar HTTPS. [Guía AWS de control de acceso S3](https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-management.html) · [Guía de OAC de CloudFront](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html)
- Cifrado S3 administrado por AWS, transporte HTTPS, bucket dedicado y roles separados: productor con permiso de escritura solo en el stream, rol Spark con lectura de entradas/escritura de capas y exportaciones, y CloudFront con lectura solo de `site/*`.
- **Publicación y caché:** escribir exportaciones JSON inmutables con SHA-256 en el nombre y `Cache-Control: public, max-age=31536000, immutable`. Publicar `site/data/v1/manifest.json` al final, con `Cache-Control: no-cache, max-age=0, must-revalidate`. Configurar CloudFront con TTL mínimo 0 y respeto de los encabezados de origen. Después de publicar el manifiesto, invalidar `/site/data/v1/manifest.json`; las exportaciones de nombre inmutable no requieren invalidación. No reemplazar objetos Gold de una publicación existente.
- Usar MFA en la cuenta raíz y no crear llaves raíz. No guardar credenciales, archivos `.env`, tokens ni claves AWS en Git, datos o capturas.
- La cuenta personal será administrada por su titular; los demás integrantes recibirán solo el acceso de proyecto necesario. Antes de cargar datos, seguir [`decision-publicacion-datos.md`](decision-publicacion-datos.md) y respetar atribuciones/licencias.
- La aplicación no necesita backend para este alcance. No añadir API Gateway, Lambda, base de datos administrada, QuickSight o WAF sin una necesidad demostrada y costo revisado.

## 4. Selección de región y compatibilidad

No fijar la región hasta comparar disponibilidad, cuota y estimación en AWS Pricing Calculator. `mx-central-1` es candidata por cercanía al equipo: la documentación vigente lista EMR Serverless en esa región y exige EMR 7.10.0 o posterior. El conector de Kinesis para Spark se incluye en EMR Serverless 7.1.0 o posterior; para consumir Kinesis se requiere configurar acceso VPC y conectividad al stream. [Regiones y releases mínimos de EMR Serverless](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/endpoints-quotas.html) · [Conector Kinesis de EMR Serverless](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/jobs-spark-streaming-connectors.html)

Comparar `mx-central-1` con `us-east-1` usando el mismo escenario. En particular, calcular endpoints VPC, solicitudes/datos S3, Kinesis, EMR, CloudWatch, CloudFront y transferencia. La entrega directa de Kinesis a S3 no está disponible en `mx-central-1` según la [tabla regional de Kinesis Data Streams](https://aws.amazon.com/kinesis/data-streams/pricing/); por eso el flujo propuesto usa Spark como consumidor y escritor S3. La documentación también señala que los jobs EMR Serverless de streaming son de larga duración y no admiten un timeout de ejecución; implementar un marcador de fin y una detención verificada para el replay finito. [Jobs de streaming de EMR Serverless](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/jobs-streaming.html) La tabla regional y disponibilidad deben revisarse de nuevo el día de la prueba.

## 5. Control de costo y puerta de autorización

No hay un monto máximo autorizado aún. Antes de crear servicios, el equipo debe acordar un presupuesto numérico y documentar una estimación con fecha, región, duración, muestra/bytes, solicitudes y eventos. Usar [AWS Pricing Calculator](https://calculator.aws/) para:

| Servicio | Variables que se deben estimar |
|---|---|
| S3 | GB-mes por prefijo/clase, PUT/GET/LIST, tamaño/particiones, salidas y transferencias; incluir versionado y retención de versiones previas. |
| EMR Serverless | vCPU-segundos, memoria GB-segundo, almacenamiento temporal y duración de cada job; incluir el minuto mínimo de cobro y el tiempo hasta detener trabajadores. |
| Kinesis Data Streams | Modo provisionado u on-demand, shards/horas o datos de entrada/salida, retención y duración del stream. Kinesis Data Streams no está actualmente en Free Tier. |
| VPC | Endpoints necesarios por zona, tráfico; comparar con cualquier alternativa de NAT antes de crearla. |
| CloudWatch | Volumen y retención de logs, métricas y alarmas. |
| CloudFront | Solicitudes y transferencia saliente estimadas para la exposición; contar invalidaciones del manifiesto y confirmar que las exportaciones inmutables aprovechan la caché de largo plazo. |

El costo de EMR Serverless depende de vCPU, memoria y almacenamiento consumidos por los workers; se factura desde que están listos, por segundo con mínimo de un minuto, además de los servicios asociados. [Precios oficiales de EMR](https://aws.amazon.com/emr/pricing/) Kinesis factura según modo/capacidad y uso; no se asumirá que una prueba pequeña es gratuita. [Precios de Kinesis Data Streams](https://aws.amazon.com/kinesis/data-streams/pricing/)

Configurar una alarma de AWS Budgets con umbrales de aviso acordados (por ejemplo, 50/80/100%). Esto **no es un tope duro**: la información de costos puede tener retraso y una notificación puede llegar después de superar el umbral. Complementarla con máximos del job EMR, duración corta, sin capacidad preinicializada, stream creado solo para la prueba, límite de eventos, y verificación manual de terminación/borrado al finalizar. [Retraso y funcionamiento de Budgets](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html) · [Acciones de Budgets](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-controls.html)

Antes del primer despliegue deben quedar anotados: titular de facturación, monto máximo aprobado, servicio/escenario calculado, notificaciones recibidas, responsable de detener recursos y evidencia final de limpieza. Si falta cualquiera de esos datos, continuar localmente.

## 6. Etapas de implementación y criterios de salida

| Etapa | Trabajo | Evidencia para pasar |
|---|---|---|
| 0. Congelar contratos localmente | Confirmar IDs/campos/unidades/huso de las muestras; correr transformaciones pequeñas localmente; separar resultados validados de la selección candidata. | Schema v1, reporte de calidad y comandos locales reproducibles. Sin recurso AWS. |
| 1. Preparar cuenta y presupuesto | Confirmar titular, MFA, acceso mínimo, región, cuotas, endpoints, estimación y umbral numérico. Crear alertas de costo. | Lista de recursos/costos aprobados y captura de presupuesto; no compartir credenciales. |
| 2. S3 privado y publicación web | Crear bucket dedicado, Block Public Access, versionado, cifrado y roles/policies; CloudFront OAC lee `site/` solamente; establecer `gold/v1/`, `site/data/v1/`, metadatos de caché y publicación de manifiesto al final. | Acceso directo al bucket denegado; web servida por HTTPS; datos Gold/raw/Silver inaccesibles públicamente; manifiesto actualizado tras publicar; exportaciones inmutables servidas desde caché. |
| 3. Lote Spark en EMR | Subir muestra acotada, ejecutar un job con límite de workers, escribir Gold particionado y métrica de ejecución. | Conteos/hash/resultados cotejados con local; runtime/costo observados; workers detenidos. |
| 4. Replay acotado | Crear stream, enviar lote pequeño identificado como replay, ejecutar Spark streaming con VPC/endpoints/checkpoint y marcador de fin. | N eventos enviados/recibidos/procesados, duplicados/rechazos, tiempo, costo y stream/job/checkpoint cerrados. |
| 5. Tablero E2E y entrega | Cambiar la web para leer manifest/Gold reales, probar estados, filtros, despliegue y copia local de respaldo; reunir código, artefactos permitidos y documentos para Classroom. | Ruta demostrable local y cloud, URL/fecha de datos, diagrama implementado y checklist de limpieza cerrado. |

## 7. Puertas de decisión pendientes

1. Titular de AWS, método de acceso del equipo y quién aprueba el gasto.
2. Monto máximo concreto para todas las pruebas y gasto máximo por ejecución.
3. Región elegida después de comparar calculadora, cuotas y endpoint Kinesis.
4. Número de perfiles/intervalos que se subirán. Los 10 perfiles actuales bastan para la primera prueba; los 10,000 IDs siguen siendo candidatos, no una descarga.
5. Duración y número máximo de eventos para el replay, además de retención de stream/checkpoint.
6. Qué artefactos Gold son redistribuibles y pueden ser públicos a través del tablero.

Este documento desarrolla el stack aprobado sin declarar despliegue ni costos inexistentes. Las decisiones de cuenta y presupuesto son requisitos previos a la implementación cloud, no pasos que se ejecutan automáticamente.
