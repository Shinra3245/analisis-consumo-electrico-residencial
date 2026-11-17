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

La propuesta plantea Amazon S3 para archivos y resultados, Amazon Kinesis Data Streams para recibir registros y Apache Spark en Amazon EMR para procesarlos. El tablero consumirá resultados agregados. La elección final y configuración se documentarán antes de activar servicios; las pruebas en nube serán acotadas y tendrán presupuesto definido.

## Estado

- [x] Propuesta versión 2 elaborada.
- [x] Aprobación del profesor para continuar sin observaciones pendientes.
- [x] Repositorio público y documentación inicial.
- [x] Primer avance documental: validación preliminar de fuentes y esquema conceptual (16 de noviembre de 2026; con pendientes explícitos).
- [x] Primera muestra empírica reproducible: agregado ResStock de Colorado, 12 meses residenciales EIA y consulta climática horaria (16 de noviembre de 2026).
- [ ] Validación de disponibilidad, licencias, formatos y cobertura de las fuentes.
- [ ] Diseño técnico y configuración del entorno.
- [ ] Implementación, evaluación y documentación de resultados.

Las casillas se actualizan con evidencia verificable. Ya se descargaron y analizaron tres muestras acotadas; no se descargó el conjunto completo ni se desplegó la arquitectura en nube.

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
- [Tareas para la revisión de avance del 17 de noviembre](docs/plan-avance-17-noviembre.md)
- [Validación inicial de fuentes](docs/validacion-inicial-fuentes.md)
- [Resultados de la primera muestra](docs/resultados-muestra-inicial.md)
- [Contenido resumido por diapositiva en JSON](docs/contenido-presentacion-avance.json)
- [Versión legible del contenido de presentación](docs/presentacion-avance-17-noviembre.md)
- [PowerPoint borrador anterior, pendiente de aplicar el estilo final](presentaciones/Avance_Big_Data_17_noviembre_2026.pptx)
- [PDF borrador anterior](presentaciones/Avance_Big_Data_17_noviembre_2026.pdf)
- [Esquema conceptual y calidad inicial de datos](docs/esquema-inicial-calidad-datos.md)
- [Decisión inicial de alcance y MVP](docs/decision-alcance-mvp.md)

El plan de desarrollo es una propuesta de organización basada en la guía disponible; se actualizará si el profesor comparte una rúbrica detallada o confirma fechas y requisitos adicionales.

La muestra y sus resultados son exploratorios: no acreditan que la plataforma final, la detección de anomalías ni el modelo de estimación estén implementados.

## Repositorio

Este repositorio es la referencia compartida para código, documentación, decisiones y avances del proyecto. No se publicarán aquí credenciales, tokens, datos personales de terceros ni conjuntos de datos que no tengan autorización de redistribución.
