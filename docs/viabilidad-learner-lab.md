# Viabilidad del Learner Lab de AWS Academy

**Fecha del registro:** 2026-11-26 (revalidación en consola de S3, Budgets, EMR Serverless, Kinesis y CloudFront)

**Estado actual:** Learner Lab `Ready` en `us-east-1`. El medidor se observó en USD 1.20 de USD 50 durante la revalidación del 26-nov; no es un presupuesto ni un tope duro. No hay Budgets configurados ni streams Kinesis. EMR Serverless devuelve `AccessDeniedException` en lectura y creación; CloudFront devuelve `AccessDenied` en lectura y creación. En S3 se verificaron la release Gold v2/web, la validación Spark de un perfil, un lote real S3 → Spark → S3 de 5 perfiles, y la ingesta raw Scale-10k (10,000 Parquet únicos; véase [`decision-seleccion-resstock-final-v2.md`](decision-seleccion-resstock-final-v2.md)). El lote de 5 generó 175,200 filas Silver y 60 Gold mensual, con 21/21 reglas QC aprobadas, cuatro objetos derivados verificados y marca de commit. Ese piloto no es procesamiento de la selección v2 de 10,000: Spark/QC global y Silver/Gold de escala siguen pendientes. SSE-S3 y Block Public Access continúan verificados; versionado deshabilitado. No se generó una URL pública estable.

El Learner Lab es temporal y no productivo. Sus recursos y su medidor no se extrapolan a una cuenta AWS real. No se incluyen identificadores, correos, ARN, credenciales, tokens ni nombres de buckets.

## 1. Hechos observados

| Elemento | Observación |
|---|---|
| Región de trabajo | `us-east-1`. |
| Sesión | 4 horas. |
| Medidor del Learner Lab | USD 1.20 de USD 50 observado al iniciar la sesión el 26-nov. El medidor no es un presupuesto mensual ni un tope duro. |
| AWS Budgets | 0 presupuestos listados en la consola el 26-nov. No hay alerta ni tope configurado por Budget. |
| Decisión operativa | Continuar con los permisos disponibles, sin esperar confirmación externa. Si una operación se deniega, registrar el resultado y mantener una alternativa local. |

## 2. Matriz de servicios

| Servicio | Estado observado | Evidencia y próximo paso |
|---|---|---|
| S3 | Releases y raw privados publicados y verificados | Se publicaron Gold v2/web, 12 objetos de validación Spark de 1 perfil, un lote Spark real de 5 perfiles (4 objetos derivados más marca de commit) y 10,000 raws ResStock v2 bajo prefijos separados. El lote de 5 tuvo readback y 21/21 QC; no equivale a procesar los raws v2. Se verificaron Content-Type, SSE-S3 y Block Public Access. No hay URL pública estable; versionado deshabilitado. |
| Kinesis Data Streams | 0 streams (lectura permitida) | `ListStreams` devolvió 0 streams; `DescribeLimits` reportó límite de 20,000 shards. No se creó stream para evitar costos estériles, dado que EMR Serverless está denegado y no existe consumidor cloud en el entorno. |
| EMR Serverless | Denegado en lectura y creación | `ListApplications` y `CreateApplication` devolvieron `AccessDeniedException` (`no identity-based policy allows...`). No es posible ejecutar cómputo cloud en Learner Lab; el pipeline Spark 4.0.1 se mantiene localmente reproducible. |
| CloudFront | 0 distribuciones; API denegada en lectura y creación | `ListDistributions` y `CreateDistribution` devolvieron `AccessDenied` (`no identity-based policy allows...`). La consola web visual mostró 0 distribuciones sin error modal, pero la API deniega la creación. No es viable configurar CDN/HTTPS pública en este entorno. |
| AWS Budgets | 0 presupuestos (lectura permitida) | `DescribeBudgets` devolvió 0 presupuestos. El medidor de Learner Lab no reemplaza un Budget; consumo monitoreado directamente en Vocareum. |
| IAM | Parcial o bloqueado | La sesión asume `voclabs/LabRole`; llamadas administrativas y de ampliación devuelven `AccessDenied`. No se intentan eludir políticas. |

## 3. Límites y control de riesgo

- Que una consola abra no prueba que se pueda crear o ejecutar el servicio.
- El error de una acción concreta no prueba que todo el servicio esté bloqueado.
- Las cargas Gold v2/web y la salida Spark de validación se verificaron en S3 privado. No se abrió en navegador mediante URL temporal en esta sesión. La URL prefirmada histórica del v1 caduca y no convierte el bucket en público.
- La sesión dura 4 horas y puede caducar; no se verificó la persistencia de cada recurso después del cierre.
- Los resultados aplican a la sesión y región observadas.
- Se fija una meta interna prudente de no superar **USD 5 de consumo adicional estimado u observado durante el siguiente bloque**. No es un límite duro de AWS ni una garantía del medidor. Revisar el medidor antes y después de acciones cloud; evitar EMR y streaming hasta tener estimación verificable.

## 4. Secuencia acordada

1. Empaquetar la demo con python scripts/empaquetar_demo.py --output /tmp/consumo-residencial.html.
2. Cargar el HTML autónomo y Gold v2 en prefijos privados inmutables. Los 14 objetos de release y los 12 objetos de salida Spark de validación se verificaron el 26-nov; la carga no crea una dirección web pública.
3. Mantener la demo local como ruta permanente y respaldo; regenerar la URL temporal desde S3 cuando sea necesario.
4. Mantener Spark/replay locales mientras EMR Serverless esté denegado. No crear Kinesis sin un consumidor disponible.
5. Revisar costo y consumo después de cada bloque. No guardar URLs prefirmadas, credenciales ni datos crudos en Git.
6. La salida de validación de 1 perfil contiene cinco Parquet (tres Silver y dos Gold), manifiesto y reporte; también conserva cinco marcadores `_SUCCESS` de Spark. Se mantuvo privada y separada de la release Gold v2. La salida del job de 50 perfiles permanece local; no se publicó en S3.

No se detendrá el proyecto esperando confirmaciones externas. Las operaciones disponibles se ejecutarán con prudencia; las no disponibles se resolverán con una alternativa local y se declararán en la documentación.
