# Guía de ejecución del pipeline Apache Spark

## 1. Objetivo

Documentar la ejecución local y reproducible del pipeline de ingeniería de datos para analizar el consumo eléctrico residencial de Colorado durante 2018.

Se utilizan las fuentes ResStock y EIA. El procesamiento se divide en las capas Raw, Bronze, Silver y Gold, seguido de una comparación mensual, exportación JSON y pruebas automatizadas.

## 2. Requisitos

- Python 3.11.
- Java 21.
- Git.
- Apache Spark mediante `pyspark==4.1.1`.
- Dependencias del archivo `requirements-spark.txt`.
- En Windows, configuración compatible de Hadoop para operaciones locales con Parquet, cuando sea necesaria.

La ejecución descrita corresponde al entorno local. No constituye una ejecución en AWS EMR.

## 3. Preparación del entorno

Desde la raíz del repositorio, en PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-spark.txt
```

Para comprobar las versiones:

```powershell
python --version
java -version
```

En Linux, la activación del entorno virtual utiliza `source .venv/bin/activate`.

## 4. Obtener los datos de entrada

Ejecutar:

```powershell
python scripts/analizar_muestra_inicial.py --descargar
```

Este programa descarga las muestras iniciales en `data/raw/`, si todavía no existen:

- `up00-co-single-family_detached.csv`: agregado de consumo eléctrico de ResStock.
- `eia_sales_revenue.xlsx`: estadísticas mensuales oficiales de EIA.
- `openmeteo_denver_2018.json`: datos meteorológicos iniciales de Denver.

El script también genera resultados de análisis exploratorio. La fuente meteorológica todavía no forma parte del pipeline Spark descrito a continuación.

## 5. Ejecutar el pipeline

Los comandos deben ejecutarse en el siguiente orden, desde la raíz del repositorio.

### 5.1. Capa Bronze

```powershell
python jobs/batch/crear_bronze_resstock.py
python jobs/batch/crear_bronze_eia.py
```

Se leen los archivos originales y se generan datasets Parquet preservando los datos de entrada y sus campos de procedencia.

### 5.2. Capa Silver

```powershell
python jobs/batch/crear_silver_resstock.py
python jobs/batch/crear_silver_eia.py
```

Se convierten los tipos de datos, se aplican reglas de validación y se separan los registros válidos de los rechazados.

### 5.3. Capa Gold

```powershell
python jobs/batch/crear_gold_resstock.py
python jobs/batch/crear_gold_eia.py
```

Se generan agregaciones mensuales expresadas en MWh.

### 5.4. Comparación de fuentes

```powershell
python jobs/batch/comparar_resstock_eia.py
```

Se relacionan los resultados mensuales de ResStock y EIA mediante año, mes y estado.

### 5.5. Exportación para visualización

```powershell
python jobs/batch/exportar_comparacion_json.py
```

Se genera el archivo:

`data/exports/comparacion_co_2018.json`

Este archivo contiene los resultados de comparación mensual destinados a su posible integración con el tablero.

## 6. Ejecutar las pruebas automatizadas

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

La ejecución local verificada completó **24 pruebas exitosas**:

| Categoría | Pruebas |
|---|---:|
| Calidad sintética EIA | 8 |
| Calidad sintética ResStock | 11 |
| Validación JSON | 5 |
| Total | 24 |

Las pruebas cubren los casos sintéticos implementados y las verificaciones de estructura y consistencia del JSON.

## 7. Generar el reporte de calidad

```powershell
python scripts/generar_reporte_spark.py
```

El reporte se genera en:

`docs/reporte_calidad_rendimiento_spark.md`

Las mediciones de tiempo corresponden a operaciones de lectura y conteo, no necesariamente a la duración total de cada transformación.

## 8. Resultados de referencia

Los resultados locales verificados son:

| Métrica | Resultado |
|---|---:|
| Intervalos ResStock procesados | 35,040 |
| Meses EIA procesados | 12 |
| Registros rechazados de la muestra | 0 |
| Consumo anual ResStock | 16,809,653.30 MWh |
| Ventas anuales EIA | 19,286,952.00 MWh |
| Relación ResStock/EIA | 87.16% |

La relación no mide precisión predictiva: ResStock representa un agregado modelado de viviendas unifamiliares aisladas, mientras EIA representa las ventas del sector residencial completo.

## 9. Consideraciones y limitaciones

- El alcance actual corresponde a Colorado en 2018.
- Los archivos procesados se almacenan principalmente en formato Parquet.
- Los datos Raw y los productos procesados están excluidos de Git.
- La muestra ResStock utiliza consumo agregado ponderado; no debe aplicarse nuevamente `units_represented` como multiplicador.
- El timestamp de ResStock corresponde al final de cada intervalo de 15 minutos. Para agrupar temporalmente se calcula el inicio restando 15 minutos.
- La normalización explícita de marcas temporales de ResStock a UTC todavía está pendiente.
- La comparación no sustituye un análisis de predicción o detección de anomalías.
- La integración con AWS EMR y Kinesis todavía está pendiente de implementar y verificar.

## 10. Estado

Pipeline batch local implementado y verificado con datos reales y pruebas automatizadas. Pendientes: contrato de datos definitivo, normalización temporal, integración con módulos analíticos y procesamiento en la nube.