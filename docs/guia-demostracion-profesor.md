# Guía breve para mostrar el avance al profesor

Esta guía resume qué datos se usaron, qué se implementó, qué está configurado en AWS y cómo abrir la web. Distingue el trabajo local del que ya está desplegado.

## 1. Explicación corta del proyecto

El proyecto analiza patrones de consumo eléctrico residencial combinando tres tipos de información: perfiles de viviendas simulados, ventas eléctricas oficiales y una muestra climática histórica. El objetivo final es explorar patrones y, después de validar los métodos, agregar detección de anomalías y estimaciones.

Los perfiles ResStock son modelos, no lecturas de medidores de hogares. EIA informa ventas agregadas del sector residencial por estado. El clima procede de reanálisis histórico y se mantiene separado mientras no se resuelvan las correspondencias geográficas y horarias.

## 2. Fuentes de datos

| Fuente y enlace | Qué se tomó | Cómo explicarlo |
|---|---|---|
| [ResStock 2025 Release 1 en OEDI](https://data.openei.org/submissions/4520), [README del release](https://oedi-data-lake.s3.amazonaws.com/nrel-pds-building-stock/end-use-load-profiles-for-us-building-stock/2025/resstock_amy2018_release_1/README.md), [cita y licencia](https://oedi-data-lake.s3.amazonaws.com/nrel-pds-building-stock/end-use-load-profiles-for-us-building-stock/2025/resstock_amy2018_release_1/citation.txt) | Perfiles AMY 2018 cada 15 minutos. El Parquet piloto procesado contiene 10 perfiles y 350,400 filas; el índice de 10,000 IDs son candidatos, no 10,000 perfiles descargados. | Muestra consumo residencial modelado para distintos edificios. |
| [EIA-861M: ventas y datos mensuales](https://www.eia.gov/electricity/data/eia861m/), [archivo XLSX usado](https://www.eia.gov/electricity/data/eia861m/xls/sales_revenue.xlsx) | Ventas mensuales por estado y sector, filtradas al sector residencial. La tabla integrada tiene 5,304 filas y conserva si el dato es `Final` o `Preliminary`. | Es una referencia oficial agregada de ventas; no corresponde a las mismas viviendas del modelo ResStock. |
| [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api), [licencia de datos](https://open-meteo.com/en/license), [términos de uso](https://open-meteo.com/en/terms), [ficha ERA5-Land de Copernicus](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land?tab=overview) | Muestra de temperatura horaria ERA5-Land para Denver y Grand Junction, del 1 al 7 de enero de 2018: 336 filas. | Es clima estimado por reanálisis en dos puntos, no una estación física ni el clima de todo Colorado. Aún no se ha unido al consumo. |

Los términos de Open-Meteo describen la API gratuita como no comercial y permiten contenido educativo; se mantiene la atribución a Open-Meteo y ERA5-Land/Copernicus. Para ResStock, conservar la cita del release y la atribución NREL/DOE indicadas en su README.

## 3. Qué se implementó

- **Preparación y procesamiento local:** un job PySpark lee las muestras, comprueba hashes y esquemas, ejecuta 21 reglas de calidad y escribe capas Silver y Gold. La ejecución documentada aprobó las 21 reglas.
- **Tablas producidas:** 350,400 filas Silver ResStock, 5,304 EIA y 336 de clima; Gold mensual de 120 filas ResStock y 5,304 filas EIA.
- **Sitio web:** página estática interactiva con gráficas mensuales de líneas, barras y relación, filtros por temporada, selección de mes y tabla de valores. Se puede abrir sin instalar bibliotecas.
- **Alcance de la cifra 87.16%:** corresponde a una comparación exploratoria de un agregado ResStock de 5,869 modelos ponderados con las ventas de todo el sector residencial EIA en Colorado en 2018. No es una medida de precisión del modelo.

**Distinción importante para la exposición:** el sitio web actual todavía muestra esa comparación histórica de 5,869 modelos; no consume las tablas Gold del pipeline Spark, que corresponden a otro piloto de 10 perfiles. No presentar ambos conjuntos como si fueran el mismo cálculo. La conexión web–Gold queda como próximo bloque.

## 4. AWS: servicios, región y configuración observada

El entorno usado es AWS Academy Learner Lab temporal, en `us-east-1`. No se inició una instancia EC2 ni un clúster de cómputo.

| Servicio | Estado real | Configuración / uso |
|---|---|---|
| [Amazon S3](https://us-east-1.console.aws.amazon.com/s3/home?region=us-east-1) | Implementado | Bucket nuevo dedicado al proyecto. Bloqueo de acceso público activado, ACL deshabilitadas y cifrado SSE-S3. Se cargaron el HTML autónomo y dos Parquet Gold con manifiesto y reporte de calidad. El contenido permanece privado. |
| [Amazon EMR Serverless](https://us-east-1.console.aws.amazon.com/emr/home?region=us-east-1#/serverless) | No implementado en AWS | La sesión mostró falta de permisos al abrir EMR Serverless. El job Spark se ejecutó localmente en vez de dejar cómputo cloud sin completar. |
| [Amazon Kinesis Data Streams](https://us-east-1.console.aws.amazon.com/kinesis/home?region=us-east-1#/streams) | No implementado | El formulario era visible, pero no se creó un stream porque no había un consumidor EMR cloud disponible. El replay histórico sigue siendo trabajo pendiente/local. |
| CloudFront | No desplegado | No hay URL permanente del sitio. La lectura de S3 se verificó con una URL prefirmada temporal; esta caduca y no hace público el bucket. |

Los enlaces de consola requieren entrar al Learner Lab correspondiente y respetan los permisos de esa sesión. No se incluyen credenciales, nombre del bucket ni URL prefirmada en esta guía. El medidor del laboratorio no es un límite de gasto garantizado.

## 5. Cómo abrir el proyecto web

### En la computadora donde está el repositorio

Desde la carpeta raíz del proyecto, ejecutar:

```bash
python -m http.server 8000 --directory demo
```

Abrir <http://localhost:8000> en el navegador. Para detener el servidor, volver a la terminal y presionar `Ctrl+C`.

También se puede abrir directamente `demo/index.html`. La demo no depende de internet ni de servicios externos. El enlace local `127.0.0.1` funciona solo en esta computadora; no es un enlace público para abrir desde otra casa o dispositivo.

### Para mostrar la gráfica

1. Explicar que el eje horizontal contiene los meses y el vertical el consumo en MWh.
2. Identificar cada serie usando la leyenda: perfil ResStock modelado y ventas residenciales EIA.
3. Cambiar entre líneas, barras agrupadas y relación mensual; probar el filtro de temporada.
4. Seleccionar un mes y leer sus valores en la tabla inferior.
5. Aclarar que las dos fuentes cubren poblaciones distintas y que el porcentaje mostrado no es precisión.

## 6. Pendientes prioritarios

1. **Conectar la web con las tablas Gold reales** y resolver la diferencia entre los 5,869 modelos de la gráfica actual y los 10 perfiles del pipeline Spark.
2. **Completar el tablero de seis vistas** previsto en la propuesta; la demo actual es una página preliminar con una vista de comparación y secciones explicativas.
3. **Ampliar y medir la muestra ResStock** antes de afirmar que se procesaron los 10,000 perfiles candidatos.
4. **Desarrollar y evaluar** las vistas de patrones, anomalías y estimaciones con métricas y periodos de evaluación reproducibles.
5. **Resolver las zonas horarias y el cruce con clima** antes de afirmar patrones horarios combinados.
6. **Completar el flujo cloud:** EMR Serverless, replay por Kinesis y publicación web persistente con CloudFront/OAC; los permisos actuales impiden completar esas etapas en Learner Lab.
7. **Revisar permisos de redistribución y conservar atribuciones** antes de incluir archivos crudos o muestras en una entrega pública.

## 7. Frase sugerida para explicar el estado

> “Ya contamos con una muestra reproducible, un procesamiento local en Spark con controles de calidad y una web interactiva para explorar una comparación inicial. También guardamos en S3 privado resultados derivados y la página. El siguiente trabajo es conectar esa web con las tablas Gold del piloto, completar análisis y vistas, y terminar el flujo cloud cuando el entorno permita ejecutar EMR y Kinesis.”

## Documentación técnica del repositorio

- [Demo web y forma de abrirla](../demo/README.md)
- [Ejecución local de Spark](ejecucion-job-spark-local.md)
- [Despliegue y objetos cargados en S3](despliegue-s3-demo.md)
- [Viabilidad observada del Learner Lab](viabilidad-learner-lab.md)
- [Contrato y alcance de las fuentes](contrato-datos-v1.md)
- [Decisión sobre publicación y licencias](decision-publicacion-datos.md)
