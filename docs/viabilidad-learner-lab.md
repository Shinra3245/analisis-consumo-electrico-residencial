# Viabilidad del Learner Lab de AWS Academy

**Fecha del registro:** 2026-11-26 (revalidación en consola de S3, Budgets, EMR Serverless, Kinesis y CloudFront)

**Estado actual:** Learner Lab `Ready` en `us-east-1`. El medidor mostró USD 1.20 de USD 50; no es presupuesto ni límite duro. Se confirmó que no hay Budgets configurados ni streams Kinesis; EMR Serverless devuelve `AccessDeniedException` al listar aplicaciones y CloudFront devuelve `AccessDenied` al listar distribuciones. En S3 se verificaron la release privada Gold/web de 14 objetos y la salida privada de validación Spark de un perfil (7 archivos de datos/reporte y 5 marcadores `_SUCCESS`, 12 objetos). Se verificaron Content-Type, SSE-S3 y Block Public Access; versionado deshabilitado. No se creó URL prefirmada ni se cambió configuración de acceso.

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
| S3 | Releases privadas publicadas y verificadas | Se publicaron 14 objetos Gold v2/web y 12 objetos de validación Spark de 1 perfil bajo prefijos separados. Se verificaron Content-Type, SSE-S3 y Block Public Access. No hay URL pública ni prefirmada nueva; versionado deshabilitado. El HTML v1 de 56,429 bytes y la URL temporal del 18-nov son evidencia histórica distinta. |
| Kinesis Data Streams | 0 streams | Listado verificado el 26-nov; no se creó stream. El replay permanece local, sin consumidor cloud preparado. |
| EMR Serverless | Denegado en la acción verificada | `ListApplications` devolvió `AccessDeniedException`. No se creó aplicación ni se inició cómputo; Spark 4.0.1 se ejecutó localmente. |
| CloudFront | 0 distribuciones; listado denegado | La consola mostró `AccessDenied` al consultar distribuciones. No se desplegó CloudFront/OAC ni hay URL estable. |
| AWS Budgets | 0 presupuestos | Lista verificada el 26-nov. El medidor de Learner Lab no reemplaza un Budget; no se creó uno durante esta revisión. |
| IAM | Parcial o bloqueado | La lista de roles muestra `LabRole`; `iam:GetPolicy`, `access-analyzer:ListPolicyGenerations` y `account:GetAccountInformation` devolvieron `AccessDenied`. No se crearán roles ni se intentará ampliar permisos. |

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
