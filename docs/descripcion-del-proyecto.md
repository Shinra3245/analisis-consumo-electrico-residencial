# Descripción del proyecto

## Contexto

El proyecto estudiará el consumo eléctrico residencial en Estados Unidos mediante la integración de perfiles residenciales modelados, estadísticas oficiales de electricidad y datos meteorológicos. El análisis buscará describir diferencias por región y grupo de viviendas, reconocer patrones temporales y explorar cambios inusuales.

## Objetivo general

Construir una plataforma de análisis de Big Data que integre fuentes residenciales, eléctricas y meteorológicas para visualizar patrones de consumo, detectar anomalías y generar estimaciones interpretables por periodo y grupo, documentando la procedencia y las limitaciones de los datos.

## Objetivos específicos

1. Identificar y validar conjuntos de datos compatibles en cobertura, granularidad, periodo, formato y condiciones de uso.
2. Preparar un flujo reproducible de ingesta, validación, transformación y almacenamiento.
3. Calcular indicadores temporales y comparaciones regionales para los perfiles residenciales y las estadísticas oficiales, manteniendo clara su distinción.
4. Implementar y evaluar métodos de detección de anomalías sobre perfiles o grupos de viviendas.
5. Comparar métodos de estimación de consumo con periodos reservados para evaluación cuando la cobertura histórica lo permita.
6. Presentar indicadores, estimaciones, anomalías y cobertura mediante un tablero.
7. Medir volumen procesado, tiempos de ejecución y costos de las pruebas de infraestructura.

## Alcance funcional

- Filtros por estado, región, grupo de viviendas y periodo.
- Resumen de cobertura y consumo agregado.
- Patrones por hora, día, mes, año y temporada; comparación entre días laborales y fines de semana.
- Exploración de la relación entre consumo y clima.
- Detección explicable de aumentos, disminuciones y periodos faltantes.
- Estimaciones diarias, mensuales y anuales con supuestos y métricas de evaluación visibles.
- Seguimiento de registros recibidos y actualización de indicadores.
- Reproducción progresiva de históricos como demostración de flujo; no se presentará como telemetría real de medidores domésticos.

## Límites y supuestos

- Los perfiles de ResStock son simulados/modelados y se identificarán como tales.
- Los datos de demanda horaria de EIA describen el sistema eléctrico, incluyen varios sectores y no sustituyen el consumo residencial por hogar.
- Una disminución de consumo no demuestra por sí misma una falla eléctrica.
- Las proyecciones basadas en un solo año de perfiles se etiquetarán como escenarios, no como predicciones longitudinales validadas.
- La conexión directa con medidores residenciales queda fuera del alcance inicial.
- Las cifras de volumen son estimaciones de planeación hasta que se midan sobre datos descargados y procesados.

## Entregables previstos

- Repositorio con documentación, código y decisiones técnicas.
- Inventario de datos y proceso reproducible de preparación.
- Flujo de procesamiento por lotes y demostración de reproducción continua.
- Análisis y evaluación de anomalías y estimaciones.
- Tablero de resultados.
- Evidencia de desempeño, cobertura, limitaciones y costos de pruebas.
