# Publicación temporal del tablero en S3

## Resultado

El 18 de noviembre de 2026 se cargó desde la consola de AWS un HTML autónomo de 8.5 MB al bucket S3 privado del proyecto, región `us-east-1`:

```text
s3://<bucket-privado-del-equipo>/site/consumo-residencial-autonomo-20261118-v1.html
```

El nombre del bucket se consulta en la consola AWS de la sesión del equipo y se omite del repositorio público.

El objeto tiene tipo `text/html` e incluye estilos, JavaScript y las 10 tablas Gold del paquete versionado del tablero, con sus hashes. La carga terminó con 1 archivo correcto y 0 errores. No se subieron los 50 perfiles ampliados ni datos crudos.

## Acceso temporal

La consola de S3 generó una URL prefirmada para el objeto. Se seleccionaron cuatro horas; la sesión temporal de Learner Lab puede hacer que venza antes. AWS copió el enlace al portapapeles de la sesión al generarlo. El enlace es una credencial temporal de acceso: no se incluye en este repositorio, chat, capturas ni commits. Quien lo tenga puede leer el objeto mientras sea válido.

Para abrirlo en el navegador de esta sesión, pega el enlace copiado en una pestaña nueva. Para compartirlo con el profesor, envíalo directamente y aclara que expira; si ya venció, vuelve a generarlo desde **S3 → bucket del proyecto → site/ → objeto → Acciones de objetos → Compartir con una URL prefirmada**. El bucket y el objeto siguen privados; una URL prefirmada no vuelve público el bucket.

## Arquitectura y límites actuales

- S3 almacena el HTML de presentación bajo `site/` y conserva el prefijo `gold/v1/pilot/` con resultados derivados separados.
- El HTML autónomo funciona como archivo único y no necesita descargar scripts, CSS o JSON externos.
- No hay endpoint permanente ni dominio web. CloudFront no está desplegado.
- EMR Serverless no inició por permisos insuficientes del Learner Lab; no se ejecutó procesamiento Spark en AWS.
- No se creó stream de Kinesis. El HTML no representa una ingestión continua ni un flujo en vivo.
- El tablero y sus métricas usan el conjunto versionado de 10 perfiles. El lote de 50 está disponible solo en salidas locales temporales y requiere una decisión de publicación antes de subirlo.

## Reproducir el paquete

Desde la raíz del repositorio:

```bash
python3 scripts/empaquetar_tablero_autonomo.py \
  --web tablero \
  --datos tablero/data/v1 \
  --salida /tmp/consumo-residencial-autonomo.html
```

El proceso valida el manifiesto, los bytes, las filas y el SHA-256 de cada tabla antes de generar el HTML. La carga a S3 y la creación de URL prefirmada son pasos manuales desde la consola.
