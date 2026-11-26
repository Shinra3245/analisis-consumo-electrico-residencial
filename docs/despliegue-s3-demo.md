# Demo estática en S3 privado

**Fecha:** 2026-11-18  
**Estado:** HTML autónomo cargado a S3 y abierto correctamente mediante una URL prefirmada temporal.

## Qué quedó desplegado

- Bucket dedicado del proyecto en us-east-1, separado del bucket de prácticas.
- Acceso público bloqueado, ACL deshabilitadas, cifrado SSE-S3 y versionado deshabilitado (observado el 2026-11-18).
- Objeto site/consumo-residencial.html, tipo text/html, 56,429 bytes.
- SHA-256: e653ccf800b36d8ea84a5a14b7a522df0b8fe84ae13df66003acbae0218eb822.
- Se abrió desde un navegador con una URL prefirmada de dos horas. La URL concede lectura temporal de ese objeto y no modifica la política privada del bucket. Una petición anónima sin firma devolvió AccessDenied, confirmando que el objeto no quedó público. No guardar ni versionar la URL: cuando caduque, generarla de nuevo en la consola S3.

## Tablas Gold del piloto en S3

Se cargaron desde la salida verificada del job Spark local y S3 reportó los cuatro archivos como correctos (55.2 KB en total):

| Objeto | Bytes | SHA-256 |
|---|---:|---|
| gold/v1/pilot/gold_resstock_monthly.parquet | 3,724 | 7ef1b445586e213728a56fe7021c5816ee2443d2ce1071471669062539b50e01 |
| gold/v1/pilot/gold_eia_monthly.parquet | 35,573 | 375a21a01abdba25f6ff5c244023e5baacb23ece1310d5eb9c34add48e2e0095 |
| gold/v1/pilot/run_manifest.json | 4,253 | 514a7cbfd7cf05505d2adeef44e4b1fc8e187ffd7c52ac547f471be255a1257b |
| gold/v1/pilot/quality_report.json | 12,945 | 8583afae33d28032f8afb5a74144b9c8c4b14900eb3ec92c7369c88e05771bd4 |

Los Parquet de esta publicación son derivados (Gold): 120 filas ResStock mensual del piloto y 5,304 filas EIA mensual multestado; este release no incluía archivos crudos ni Silver. Después se cargaron 10,000 Parquet raw ResStock en prefijos privados separados (véase [`decision-seleccion-resstock-final-v2.md`](decision-seleccion-resstock-final-v2.md)). El acceso del bucket se mantiene privado.

El Learner Lab es temporal. La URL deja de servir cuando vence o cuando expiran las credenciales de la sesión, lo que ocurra primero. Esto no es todavía alojamiento permanente del sitio.

## Regenerar el archivo

Desde la raíz del repositorio:

```bash
python scripts/empaquetar_demo.py --output /tmp/consumo-residencial.html
```

El empaquetador incorpora demo/styles.css y demo/app.js dentro de demo/index.html. Comprueba que no queden referencias a recursos externos. El archivo local no contiene claves AWS ni consulta servicios externos.

## Cargar una versión actualizada

1. En la consola S3, abrir el bucket dedicado del proyecto y entrar a site/.
2. Cargar /tmp/consumo-residencial.html con tipo text/html; confirmar que S3 marque la carga como correcta.
3. Seleccionar el objeto y usar Acciones → Compartir con una URL prefirmada. Elegir un tiempo corto, por ejemplo dos horas.
4. Abrir la URL en una ventana o navegador sin la sesión de AWS para confirmar el acceso.
5. Compartir la URL solo durante la demostración. El bucket debe seguir bloqueando el acceso público.

## Estado de otros servicios (Revalidado el 26-nov-2026)

- **EMR Serverless:** La API devolvió `AccessDeniedException` tanto en `ListApplications` como en `CreateApplication` (`no identity-based policy allows...`). No se puede usar cómputo administrado EMR en este entorno. Spark 4.0.1 se ejecutó en modo local dentro de CloudShell para el lote de prueba de cinco perfiles; el procesamiento global de 10,000 no se ha ejecutado.
- **Amazon Kinesis:** La API permitió `ListStreams` (0 streams) y `DescribeLimits` (20,000 shards), pero no se creó un stream debido a que no existe consumidor cloud habilitado (al estar bloqueado EMR Serverless). El replay se mantiene local.
- **CloudFront:** La API devolvió `AccessDenied` en `ListDistributions` y en `CreateDistribution` (`no identity-based policy allows...`). La consola web muestra 0 distribuciones. No es posible crear una CDN con HTTPS pública mediante CloudFront en Learner Lab; el acceso demostrativo a S3 se efectúa exclusivamente mediante URLs prefirmadas temporales directas sobre objetos privados.
- **S3:** Bucket verificado con Block Public Access total activado y SSE-S3. La arquitectura completa con EMR y Kinesis en la nube queda como diseño objetivo, habiendo alcanzado el nivel factible en Learner Lab (alojamiento seguro de datos Gold y tablero web autocontenido en S3 privado).
