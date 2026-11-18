# Análisis, predicción y detección de anomalías del consumo eléctrico residencial

Proyecto final de la asignatura **Big Data** del Instituto Tecnológico de Celaya. La propuesta versión 2 fue revisada y aprobada por el profesor para continuar con su desarrollo.

## Propósito

Desarrollar una plataforma de análisis para explorar el consumo eléctrico residencial en Estados Unidos, comparar patrones entre estados y grupos de viviendas, detectar comportamientos inusuales y estimar la evolución del consumo con sus supuestos claramente documentados.

## Alcance inicial

- Integrar perfiles residenciales modelados con estadísticas eléctricas oficiales y variables meteorológicas.
- Analizar patrones por hora, día, mes, año, temporada, región y características de vivienda.
- Detectar anomalías en los perfiles o grupos y distinguir cambios de consumo de periodos sin datos.
- Explorar estimaciones diarias, mensuales y anuales; reportar límites cuando los datos históricos no permitan validar una predicción.
- Demostrar procesamiento continuo mediante reproducción progresiva de datos históricos, conservando su fecha original e identificándolo como simulación.
- Presentar resultados en un tablero con secciones para resumen, patrones, clima, estimaciones, anomalías y seguimiento de registros.

## Fuentes previstas

| Fuente | Uso previsto | Consideración |
|---|---|---|
| ResStock 2025.1 | Perfiles residenciales, características de viviendas y resúmenes estatales | Son perfiles modelados, no mediciones directas de hogares. |
| U.S. Energy Information Administration (EIA) | Estadísticas residenciales por estado; demanda horaria del sistema como contexto opcional | Las estadísticas residenciales y la demanda multisectorial de red son productos distintos. EIA-930 se pospone hasta justificar su uso y normalizar el tiempo. |
| Open-Meteo | Variables meteorológicas históricas y previsiones disponibles | Se validará la compatibilidad espacial y temporal con las demás fuentes. |

La propuesta contempla iniciar el análisis detallado con al menos 10,000 perfiles. Un año de registros cada 15 minutos para esa selección equivaldría aproximadamente a 350.4 millones de filas. Son metas de escala de la propuesta, no el primer hito técnico: el MVP empieza con agregados geográficos y un subconjunto medido para reducir riesgo de tamaño, acceso y costo. Consulta la [decisión inicial de alcance](docs/decision-alcance-mvp.md).

## Arquitectura propuesta

La arquitectura objetivo plantea Amazon S3 para archivos y resultados, Amazon Kinesis Data Streams para recibir registros y Apache Spark en Amazon EMR para procesarlos. En el Learner Lab temporal ya se habilitó un bucket S3 privado para la página y los artefactos Gold del piloto. EMR Serverless no permitió iniciar la configuración por permisos; Kinesis y CloudFront no se desplegaron. El procesamiento validado se ejecutó localmente con Spark.

## Estado

- [x] Propuesta versión 2 elaborada.
- [x] Aprobación del profesor para continuar sin observaciones pendientes.
- [x] Repositorio público y documentación inicial.
- [x] Primer avance documental: validación preliminar de fuentes y esquema conceptual (16 de noviembre de 2026; con pendientes explícitos).
- [x] Primera muestra empírica reproducible: agregado ResStock de Colorado, 12 meses residenciales EIA y consulta climática horaria (16 de noviembre de 2026).
- [x] Tabla residencial EIA reproducida byte a byte desde el XLSX oficial con transformación versionada.
- [x] Piloto Parquet de 10 perfiles inspeccionado; contrato de datos v1 documenta columnas y controles observados.
- [x] Muestra climática Open-Meteo integrada con licencia y atribución documentadas.
- [x] Selección de 10,000 IDs candidatos y Parquet piloto de 10 perfiles ResStock integrados bajo CC BY 4.0 con atribución y disclaimer.
- [ ] Validación de disponibilidad, licencias, formatos y cobertura de las fuentes.
- [ ] Confirmar que el XLSX EIA no contenga material de terceros antes de copiar el archivo completo al repositorio.
- [x] Diseño técnico y configuración inicial del entorno local y de S3 privado.
- [ ] Implementación, evaluación y documentación de resultados.

Las casillas se actualizan con evidencia verificable. Se analizaron muestras acotadas; no se descargó el conjunto completo ni se completó la arquitectura cloud propuesta. La guía de demostración resume qué funciona y qué falta.

## Equipo

| Integrante | Matrícula |
|---|---|
| Brian Garcia Mares | 22030511 |
| Omar Gadiel Bolaños García | 22030591 |
| Christian Raul Páramo Bautista | 22031149 |
| Diego Emilio Ortiz Vilchez | 22030642 |

## Documentación

- [Descripción y alcance](docs/descripcion-del-proyecto.md)
- [Fuentes de datos y consideraciones](docs/fuentes-de-datos.md)
- [Arquitectura propuesta](docs/arquitectura-propuesta.md)
- [Criterios de trabajo y registro de avances](docs/seguimiento.md)
- [Plan de desarrollo y reparto por integrante](docs/plan-de-desarrollo.md)
- [Plan de ejecución integral para alcanzar 90%](docs/plan-ejecucion-integral-90.md)
- [División detallada de tareas por integrante, incluyendo AWS/nube](docs/division-tareas-integrantes-90.md)
- [Tareas para la revisión de avance del 17 de noviembre](docs/plan-avance-17-noviembre.md)
- [Validación inicial de fuentes](docs/validacion-inicial-fuentes.md)
- [Resultados de la primera muestra](docs/resultados-muestra-inicial.md)
- [Contenido resumido por diapositiva en JSON](docs/contenido-presentacion-avance.json)
- [Versión legible del contenido de presentación](docs/presentacion-avance-17-noviembre.md)
- [Presentación PDF compuesta directamente desde las ocho imágenes](presentaciones/Avance_Big_Data_17_noviembre_2026.pdf)
- [Imágenes PNG de las ocho diapositivas](presentaciones/diapositivas/)
- [Fondos originales generados para cada diapositiva](presentaciones/arte_generado/)
- [Evidencia visual: gráfica mensual real](presentaciones/evidencia/grafica-resstock-eia.png)
- [Script de composición PNG y PDF](scripts/armar_presentacion_imagenes.py)
- [PowerPoint editable de una versión visual anterior](presentaciones/Avance_Big_Data_17_noviembre_2026.pptx)
- [Esquema conceptual y calidad inicial de datos](docs/esquema-inicial-calidad-datos.md)
- [Catálogo actualizado de datos](docs/catalogo-datos-final.md)
- [Decisión de publicación y licencias](docs/decision-publicacion-datos.md)
- [Contrato de datos v1](docs/contrato-datos-v1.md)
- [CSV derivados y procedimiento de reproducción](datos/README.md)
- [Extractor reproducible EIA-861M](scripts/preparar_eia.py)
- [Decisión inicial de alcance y MVP](docs/decision-alcance-mvp.md)
- [Guía breve para mostrar el avance al profesor: fuentes, AWS y web](docs/guia-demostracion-profesor.md)
- [Job local PySpark Silver/Gold](docs/ejecucion-job-spark-local.md)
- [Despliegue de demo y resultados derivados en S3 privado](docs/despliegue-s3-demo.md)
- [Viabilidad observada del AWS Academy Learner Lab](docs/viabilidad-learner-lab.md)

El plan de desarrollo es una propuesta de organización basada en la guía disponible; se actualizará si el profesor comparte una rúbrica detallada o confirma fechas y requisitos adicionales.

La muestra y sus resultados son exploratorios. El job Spark local produjo Silver/Gold con 21 controles de calidad aprobados; la demo web actual aún no consume esas tablas Gold y las anomalías y estimaciones todavía no están implementadas. El despliegue en AWS se limita a S3 privado con el HTML y los artefactos Gold del piloto. EMR Serverless fue denegado por permisos en Learner Lab; Kinesis y CloudFront no están desplegados. Consultar el estado y los pasos pendientes en la [guía para mostrar el avance](docs/guia-demostracion-profesor.md).

## Repositorio

Este repositorio es la referencia compartida para código, documentación, decisiones y avances del proyecto. No se publicarán aquí credenciales, tokens, datos personales de terceros ni conjuntos de datos que no tengan autorización de redistribución.
