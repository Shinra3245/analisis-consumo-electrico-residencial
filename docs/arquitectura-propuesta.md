# Arquitectura propuesta

## Flujo lógico

```text
ResStock ─┐
EIA ──────┼─> ingesta y validación ─> almacenamiento crudo ─> transformación/análisis ─> agregados ─> tablero
Open-Meteo┘                                      │
                                                 └─> métricas, calidad y trazabilidad

Históricos reproducidos progresivamente ─> entrada de eventos ─> actualización de indicadores
```

La propuesta considera Amazon S3 para archivos y resultados, Amazon Kinesis Data Streams para la entrada de registros y Apache Spark en Amazon EMR para procesamiento. El flujo de históricos reproducidos se identificará como simulación. Las estadísticas de EIA y los perfiles residenciales conservarán etiquetas de fuente y significado distintos.

## Decisiones aún por validar

- Organización por zonas de almacenamiento, formatos y particiones.
- Estrategia de ingesta y frecuencia de actualización por fuente.
- Esquema común para tiempo, ubicación, unidad y tipo de dato.
- Algoritmos y criterios de evaluación para anomalías y estimaciones.
- Tecnología del tablero y mecanismo para consultar agregados.
- Configuración de AWS, controles de acceso y presupuesto de pruebas.

La ejecución del Learner Lab y la estrategia de costo/seguridad están registradas en [Arquitectura AWS por etapas](arquitectura-aws-por-etapas.md), [viabilidad del Learner Lab](viabilidad-learner-lab.md) y [despliegue S3 de la demo](despliegue-s3-demo.md). Ya existe un bucket privado con la demo y salidas Gold; EMR Serverless está denegado y Kinesis/CloudFront no están desplegados.

## Principios operativos

- Mantener datos originales inmutables y versionar transformaciones.
- Evitar secretos en el repositorio; utilizar variables de entorno o servicios de secretos.
- Aplicar permisos mínimos y detener recursos de prueba cuando no se utilicen.
- Registrar uso, tiempos y costos observados antes de ampliar recursos.
- Documentar decisiones con fecha, contexto, alternativas y evidencia.
