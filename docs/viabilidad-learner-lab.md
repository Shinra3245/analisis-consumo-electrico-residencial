# Viabilidad del Learner Lab de AWS Academy

**Fecha del registro:** 2026-11-18  
**Estado:** sesión temporal de Learner Lab. Se creó un bucket privado dedicado, se subió la demo autónoma a site/ y cuatro artefactos derivados a gold/v1/pilot/. EMR Serverless negó acceso; Kinesis permite abrir el formulario, pero no se creó un stream.

El Learner Lab es temporal y no productivo. Sus recursos y su medidor no se extrapolan a una cuenta AWS real. No se incluyen identificadores, correos, ARN, credenciales, tokens ni nombres de buckets.

## 1. Hechos observados

| Elemento | Observación |
|---|---|
| Región de trabajo | `us-east-1`. |
| Sesión | 4 horas. |
| Medidor visto antes de crear el bucket | USD 0.50 de USD 50. El medidor no es un presupuesto mensual ni un tope duro. |
| Decisión operativa | Continuar con los permisos disponibles, sin esperar confirmación externa. Si una operación se deniega, registrar el resultado y mantener una alternativa local. |

## 2. Matriz de servicios

| Servicio | Estado observado | Evidencia y próximo paso |
|---|---|---|
| S3 | Carga verificada en bucket nuevo del proyecto | Separado del bucket de prácticas. ACL deshabilitadas, bloqueo de acceso público, cifrado SSE-S3 y versionado deshabilitado. Se cargó site/consumo-residencial.html (56,429 bytes, tipo text/html) y S3 reportó la carga correcta. Una URL prefirmada de 2 horas abrió el tablero desde un navegador sin usar la consola. |
| Kinesis Data Streams | Formulario de creación accesible; no desplegado | El listado abrió con 0 streams y el formulario de creación estuvo disponible. No se creó un stream porque el consumidor EMR Serverless no tiene permisos en esta sesión; crear uno sin consumidor dejaría un recurso facturable sin completar el flujo. Mantener replay local. |
| EMR Serverless | Acceso denegado | La consola abrió la sección EMR Serverless, pero al elegir Introducción mostró: “No tiene los permisos necesarios para EMR sin servidor”. No se creó aplicación ni se inició cómputo. Continuar con Spark local. |
| CloudFront | Lectura parcial denegada | Se observaron `AccessDenied` para `cloudfront:ListSavingsPlans` y `cloudfront:ListDistributions`; esto no demuestra que todo el servicio esté prohibido. No depender de CloudFront para avanzar. |
| AWS Budgets | Parcial | Abre la pantalla introductoria; no se verificó creación de presupuestos. El medidor de Learner Lab no reemplaza Budgets. |
| IAM | Parcial o bloqueado | La lista de roles muestra `LabRole`; `iam:GetPolicy`, `access-analyzer:ListPolicyGenerations` y `account:GetAccountInformation` devolvieron `AccessDenied`. No se crearán roles ni se intentará ampliar permisos. |

## 3. Límites y control de riesgo

- Que una consola abra no prueba que se pueda crear o ejecutar el servicio.
- El error de una acción concreta no prueba que todo el servicio esté bloqueado.
- La consola confirmó la carga correcta del HTML y el navegador abrió su URL prefirmada; la URL caduca y no convierte el bucket en público.
- La sesión dura 4 horas y puede caducar; no se verificó la persistencia de cada recurso después del cierre.
- Los resultados aplican a la sesión y región observadas.
- Se fija una meta interna prudente de no superar **USD 5 de consumo adicional estimado u observado durante el siguiente bloque**. No es un límite duro de AWS ni una garantía del medidor. Revisar el medidor antes y después de acciones cloud; evitar EMR y streaming hasta tener estimación verificable.

## 4. Secuencia acordada

1. Empaquetar la demo con python scripts/empaquetar_demo.py --output /tmp/consumo-residencial.html.
2. Cargar el HTML en site/ del bucket privado. La carga del archivo único se verificó y la URL prefirmada de 2 horas abrió el dashboard.
3. Mantener la demo local como ruta permanente y respaldo; regenerar la URL temporal desde S3 cuando sea necesario.
4. Mantener Spark/replay locales mientras EMR Serverless esté denegado. No crear Kinesis sin un consumidor disponible.
5. Revisar costo y consumo después de cada bloque. No guardar URLs prefirmadas, credenciales ni datos crudos en Git.
6. Los artefactos Gold subidos son dos Parquet, el manifiesto de ejecución y el reporte de calidad; el directorio de origen fue la salida local de Spark ejecutada y verificada el 18 de noviembre de 2026.

No se detendrá el proyecto esperando confirmaciones externas. Las operaciones disponibles se ejecutarán con prudencia; las no disponibles se resolverán con una alternativa local y se declararán en la documentación.
