# Guía de Publicación y Release Web Privado en S3 (Dashboard v2)

**Estado:** Propuesta operativa de release y empaquetado seguro. No se ejecutaron acciones AWS, no se realizaron cargas a S3 ni se generaron URLs prefirmadas durante la tarea.
**Script de release y empaquetado:** [`scripts/publicar_tablero_s3.py`](../scripts/publicar_tablero_s3.py)
**Insumo de datos:** Paquete Gold v2 en [`tablero/data/v2/`](../tablero/data/v2/) (11 tablas contractuales validadas)
**Esquema de datos:** `1.0` (Publicación `2.0` con soporte demográfico)

---

## 1. Arquitectura y Modelo de Seguridad en S3 Privado

1. **Alojamiento en S3 Privado:**
   - El artefacto web del tablero se compila en un archivo HTML completamente autocontenido (`index.html`) que integra los estilos CSS, el código modular JavaScript y los datos Gold v2 inyectados en memoria (`window.__GOLD_DATA_BUNDLE__`).
   - La clave propuesta en el bucket S3 sigue un esquema inmutable y versionado:
     ```text
     site/releases/<release-id>/index.html
     ```
   - El prefijo S3 está estrictamente acotado y validado dentro del espacio de nombres `site/releases`.
   - El identificador `--release-id` se valida con una expresión regular estricta (`^[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}$`), rechazando slashes, backslashes, espacios, caracteres de control o segmentos vacíos.
   - El bucket dedicado del equipo mantiene **Block Public Access (BPA)** activado, sin ACLs públicas ni políticas abiertas.
   - Todo objeto cargado utiliza cifrado en reposo estándar **SSE-S3** (`AES256`).

2. **Acceso Web y Ausencia de URL Pública:**
   - Un bucket privado de S3 **no proporciona una URL permanente ni pública**.
   - **CloudFront:** No se encuentra desplegado ni verificado con Origin Access Control (OAC). Por ende, no existe un dominio web público ni CDN activo.
   - **Mecanismo de Evaluación:** El acceso visual requiere que un operador autenticado genere manualmente una **URL prefirmada temporal** desde la consola AWS de su sesión (por ejemplo, con expiración de 1 a 2 horas).
   - **Regla Estricta de Gobernanza:** Ninguna URL prefirmada debe ser registrada, versionada o guardada en repositorios, archivos markdown, logs ni chats, ya que actúa como credencial temporal de lectura directa al objeto privado.

3. **Estado de Servicios de Cómputo y Streaming:**
   - **EMR Serverless:** Se documenta en estado no disponible (permisos insuficientes en el entorno Learner Lab del equipo). Todo el procesamiento Spark y analítico se mantiene reproducible en entornos locales.
   - **Amazon Kinesis:** Sin streams activos ni consumidores cloud configurados. El tablero opera en base a los datos Gold generados por el pipeline, sin simulación de streaming en vivo.

---

## 2. Preparación y Validación Local del Release

El flujo predeterminado del script opera de forma estrictamente local y aislada, sin invocar credenciales ni servicios de red:

### Paso 1: Generar la carpeta de release local

Desde la raíz del repositorio:

```bash
python3 scripts/publicar_tablero_s3.py \
  --web tablero \
  --datos tablero/data/v2 \
  --salida-dir dist/release-v2-20261125
```

**Mecanismos de seguridad estricta y atomicidad local:**
- **Rechazo de sobreescritura:** Para garantizar la inmutabilidad y trazabilidad de releases históricos, el script exige que el directorio de salida sea nuevo y no exista previamente.
- **Resolución estricta anti-symlinks y no-escape:** Antes de leer cualquier insumo, la función `verify_safe_file_within_root` inspecciona `manifest.json`, cada una de las 11 tablas, `index.html`, `styles.css` y cada módulo JavaScript, comprobando que ni el archivo ni ningún componente de su ruta sean symlinks y que sus destinos resueltos residan estrictamente dentro de sus directorios raíz (`web/` o `data/`).
- **Staging atómico y verificación pre-rename:** El script genera el release en un directorio temporal hermano oculto (`.staging_...`). Antes de proceder con el renombrado final, vuelve a leer desde el disco `index.html` y `release_manifest.json` y verifica que:
  1. El tamaño y hash SHA-256 del HTML leído correspondan exactamente al empaquetado y a lo declarado en el manifiesto.
  2. El manifiesto parsee correctamente y declare el mismo `release_id` y `proposed_object_key`.
  Si se detecta cualquier discrepancia, el directorio temporal de staging se elimina de inmediato y el proceso se aborta sin publicar. Solo si todas las comprobaciones son exitosas, se ejecuta el renombrado atómico (`rename`) hacia la ruta de destino.

### Paso 2: Validación estricta del contrato de datos v2

Antes de compilar el artefacto, el script valida rigurosamente:
1. **Inventario contractual de 11 tablas:** Comprueba la presencia exacta de `gold_eia_monthly`, `gold_resstock_monthly`, `gold_resstock_pattern`, `gold_resstock_pattern_aggregate`, `gold_resstock_profile_summary`, `gold_climate`, `gold_demography_state_year`, `gold_anomaly_candidates`, `gold_anomaly_synthetic_eval`, `gold_forecast_metrics` y `gold_forecast_series`. No se permiten tablas faltantes ni sobrantes.
2. **Campos obligatorios por tabla:** Exige `file`, `bytes`, `sha256` y `rows` en cada entrada del manifiesto, sin admitir omisiones.
3. **Integridad de datos:** Compara el tamaño exacto en bytes, el SHA-256 de cada archivo, parsea los contenidos como JSON y comprueba que la cantidad de registros sea exacta.
4. **Estado QC del manifiesto:** Exige que `failed_rules == 0` y que el estatus de calidad sea `VALID` o `VALID_WITH_WARNINGS`.

### Paso 3: Contenido del release generado

Al finalizar el empaquetado local, la carpeta de release contiene:

1. **`index.html`:**
   - Archivo HTML autocontenido (~9.1 MB).
   - Integra las 11 tablas Gold (20,858 registros en total).
   - Funciona de manera autónoma en cualquier navegador sin realizar llamadas HTTP externas.
2. **`release_manifest.json`:**
   - Manifiesto reproducible con metadatos del release:
     - `release_id`: Identificador único validado (ej. `v2-20261125-<hash8>`).
     - `built_at_utc`: Marca temporal ISO 8601 de compilación.
     - `schema_version`: `"1.0"`.
     - `package_version`: `"2.0"`.
     - `artifact`: Nombre de archivo, tamaño exacto en bytes, SHA-256 y tipo de contenido (`text/html; charset=utf-8`).
     - `s3_target`: Clave inmutable propuesta (`site/releases/<release-id>/index.html`), especificación de cifrado SSE-S3 (`AES256`) y declaración exacta de control de acceso: `"private (no ACL sent; bucket policy and Block Public Access remain unchanged)"`.
     - `source_data`: Conteo de tablas (11), filas totales (20,858) y SHA-256 del manifiesto de origen.

### Paso 4: Inspeccionar el release localmente

Para verificar visualmente el release local antes de cualquier interacción con la nube:

```bash
# Probar el archivo compilado en el navegador local
python3 -m http.server 8080 -d dist/release-v2-20261125
# Abrir http://localhost:8080/index.html
```

---

## 3. Procedimiento Consciente de Carga a S3 (Operador Autorizado)

> [!IMPORTANT]
> La carga a S3 solo debe ser ejecutada por un miembro del equipo que cuente con sesión activa en el entorno de AWS del proyecto y consentimiento del equipo. No se ejecutan llamadas de carga automáticas.

### Opción A: Carga mediante el script de publicación (`--upload`)

El script incluye un mecanismo seguro y cerrado que garantiza la inmutabilidad y verifica la integridad post-carga:

```bash
# Requiere credenciales activas en la sesión local (AWS CLI / Learner Lab)
python3 scripts/publicar_tablero_s3.py \
  --web tablero \
  --datos tablero/data/v2 \
  --salida-dir dist/release-v2-20261125-s3 \
  --upload \
  --bucket <nombre-bucket-privado> \
  --region us-east-1
```

**Garantías del mecanismo `--upload`:**
- **Rechazo de sobreescritura previa:** Ejecuta primero un `head_object` para verificar si la clave ya existe en el bucket. Si el objeto ya existe, falla cerrado de inmediato (`RuntimeError`) para no sobrescribir versiones previas.
- **Escritura condicional:** En la petición `put_object`, envía `IfNoneMatch='*'` como condición atómica de la API de S3 para impedir colisiones o reemplazos concurrentes.
- **Sin ACL pública:** No se envía cabecera de ACL; el objeto hereda la política privada del bucket y las reglas de Block Public Access.
- **Cifrado y Content-Type:** Especifica `ServerSideEncryption='AES256'` y `ContentType='text/html; charset=utf-8'`, asociando el hash SHA-256 local en `Metadata={'sha256': ...}`.
- **Verificación estricta con HeadObject:** Tras la carga, consulta remotamente el objeto y comprueba:
  1. `ContentLength` idéntico a los bytes locales.
  2. `ServerSideEncryption == 'AES256'`.
  3. `ContentType` contenga `text/html`.
  4. `Metadata.sha256` coincida exactamente con el SHA-256 local.
  *(Nota técnica: El ETag no se interpreta como SHA-256 dado que corresponde a un hash MD5 en S3).*
- Falla cerrado ante cualquier discrepancia. Nunca borra objetos existentes ni altera configuraciones de CDN.

### Opción B: Carga manual desde la Consola de AWS

1. Acceder a la Consola de AWS en `us-east-1` e ingresar a **Amazon S3**.
2. Navegar al bucket privado del equipo y abrir la carpeta `site/releases/`.
3. Crear una subcarpeta con el `<release-id>` indicado en `release_manifest.json`.
4. Cargar el archivo `index.html` asegurando:
   - **Tipo de contenido:** `text/html; charset=utf-8`.
   - **Cifrado del servidor:** Clave administrada por Amazon S3 (SSE-S3).
   - **Permisos:** Mantener desactivado todo acceso público.

---

## 4. Verificación en la Consola de AWS y Demostración Temporal

Una vez cargado el objeto por el operador:

1. **Verificar Propiedades:**
   - En la consola S3, seleccionar el objeto cargado (`site/releases/<release-id>/index.html`).
   - Confirmar en la pestaña **Propiedades** que el tamaño en bytes coincide con el valor registrado en `release_manifest.json`.
   - Confirmar que el cifrado en reposo muestre `Amazon S3 key (SSE-S3)` y el tipo de contenido sea `text/html; charset=utf-8`.
2. **Confirmar Acceso Privado:**
   - Copiar la URL estándar de S3 (`https://<bucket>.s3.amazonaws.com/site/releases/<release-id>/index.html`).
   - Abrirla en una ventana de incógnito o sin autenticar: debe devolver código `403 Forbidden` (`AccessDenied`), evidenciando que el objeto no es accesible anónimamente.
3. **Generar URL Prefirmada para Demostración:**
   - Desde la consola S3, seleccionar el objeto y pulsar **Acciones de objetos → Compartir con una URL prefirmada**.
   - Definir un tiempo de validez reducido (ej. 60 o 120 minutos).
   - Abrir el enlace en el navegador para comprobar la navegación completa entre las 6 vistas y la correcta interacción demográfica con Gold v2.
   - **Recordatorio:** No guardar ni pegar la URL generada en archivos del proyecto ni en el historial de git.
