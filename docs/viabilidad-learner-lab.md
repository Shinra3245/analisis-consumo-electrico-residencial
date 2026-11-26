# Viabilidad del Learner Lab de AWS Academy

**Fecha del registro:** 2026-11-26 (revalidación parcial; estado de servicios distintos de S3 conserva la evidencia del 18-nov)

**Estado actual:** Learner Lab activo y listo en `us-east-1`. El 26-nov se publicaron en S3 privado los 11 JSON Gold v2 y su manifiesto, más el HTML autónomo y el manifiesto de release (14 archivos en total). Se verificaron Content-Type, SSE-S3 y el bloqueo de acceso público. Versionado sigue deshabilitado. No se generó URL prefirmada para la nueva release. EMR/Kinesis/CloudFront/Budgets/IAM no se revalidaron en esta sesión; para ellos rige la observación del 18-nov.

El Learner Lab es temporal y no productivo. Sus recursos y su medidor no se extrapolan a una cuenta AWS real. No se incluyen identificadores, correos, ARN, credenciales, tokens ni nombres de buckets.

## 1. Hechos observados

| Elemento | Observación |
|---|---|
| Región de trabajo | `us-east-1`. |
| Sesión | 4 horas. |
| Medidor del Learner Lab | USD 1.20 de USD 50 observado al iniciar la sesión el 26-nov. El medidor no es un presupuesto mensual ni un tope duro. |
| Decisión operativa | Continuar con los permisos disponibles, sin esperar confirmación externa. Si una operación se deniega, registrar el resultado y mantener una alternativa local. |

## 2. Matriz de servicios

| Servicio | Estado observado | Evidencia y próximo paso |
|---|---|---|
| S3 | Gold v2 y sitio publicados en release privada (26-nov) | Separado del bucket de prácticas. Se subieron 12 archivos bajo `gold/v2/releases/` y 2 bajo `site/releases/`. Antigravity confirmó Content-Type, SSE-S3 y Block Public Access; versionado deshabilitado. No se creó URL prefirmada para la nueva release. El HTML v1 de 56,429 bytes y la URL temporal verificada el 18-nov son evidencia histórica distinta. |
| Kinesis Data Streams | Formulario de creación accesible; no desplegado | El listado abrió con 0 streams y el formulario de creación estuvo disponible. No se creó un stream porque el consumidor EMR Serverless no tiene permisos en esta sesión; crear uno sin consumidor dejaría un recurso facturable sin completar el flujo. Mantener replay local. |
| EMR Serverless | Acceso denegado | La consola abrió la sección EMR Serverless, pero al elegir Introducción mostró: “No tiene los permisos necesarios para EMR sin servidor”. No se creó aplicación ni se inició cómputo. Continuar con Spark local. |
| CloudFront | Lectura parcial denegada; sin distribución verificada | Se observaron `AccessDenied` para `cloudfront:ListSavingsPlans` y `cloudfront:ListDistributions`; esto no demuestra que todo el servicio esté prohibido. No depender de CloudFront para avanzar. |
| AWS Budgets | Parcial | Abre la pantalla introductoria; no hay evidencia de Budget creado ni de tope duro. El medidor de Learner Lab no reemplaza Budgets. |
| IAM | Parcial o bloqueado | La lista de roles muestra `LabRole`; `iam:GetPolicy`, `access-analyzer:ListPolicyGenerations` y `account:GetAccountInformation` devolvieron `AccessDenied`. No se crearán roles ni se intentará ampliar permisos. |

## 3. Límites y control de riesgo

- Que una consola abra no prueba que se pueda crear o ejecutar el servicio.
- El error de una acción concreta no prueba que todo el servicio esté bloqueado.
- La release v2 se verificó como carga privada en la consola; no se abrió en un navegador mediante URL temporal en esta sesión. La URL prefirmada histórica del v1 caduca y no convierte el bucket en público.
- La sesión dura 4 horas y puede caducar; no se verificó la persistencia de cada recurso después del cierre.
- Los resultados aplican a la sesión y región observadas.
- Se fija una meta interna prudente de no superar **USD 5 de consumo adicional estimado u observado durante el siguiente bloque**. No es un límite duro de AWS ni una garantía del medidor. Revisar el medidor antes y después de acciones cloud; evitar EMR y streaming hasta tener estimación verificable.

## 4. Secuencia acordada

1. Empaquetar la demo con python scripts/empaquetar_demo.py --output /tmp/consumo-residencial.html.
2. Cargar el HTML autónomo y Gold v2 en los prefijos inmutables de release privados. La carga de 14 objetos se verificó el 26-nov; la nueva release aún no tiene URL de demostración.
3. Mantener la demo local como ruta permanente y respaldo; regenerar la URL temporal desde S3 cuando sea necesario.
4. Mantener Spark/replay locales mientras EMR Serverless esté denegado. No crear Kinesis sin un consumidor disponible.
5. Revisar costo y consumo después de cada bloque. No guardar URLs prefirmadas, credenciales ni datos crudos en Git.
6. Los artefactos Gold subidos son dos Parquet, el manifiesto de ejecución y el reporte de calidad; el directorio de origen fue la salida local de Spark ejecutada y verificada el 18 de noviembre de 2026.

No se detendrá el proyecto esperando confirmaciones externas. Las operaciones disponibles se ejecutarán con prudencia; las no disponibles se resolverán con una alternativa local y se declararán en la documentación.
