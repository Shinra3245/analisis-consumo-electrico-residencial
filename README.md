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

## Estado actual

- [x] Propuesta versión 2 aprobada por el profesor.
- [x] Pipeline PySpark local ejecutado con 21 controles de calidad; lote exploratorio ampliado a 50 perfiles, con 1,752,000 intervalos verificados. Sus salidas ampliadas permanecen en `/tmp` y no se versionaron.
- [x] Tablero web con seis vistas. La versión incluida en el repositorio consume 10 tablas Gold JSON del manifiesto: piloto versionado de 10 perfiles más EIA, clima y analítica de anomalías/backtest. Filas, bytes y SHA-256 verificados.
- [x] Análisis EIA reproducible: 43 candidatos estadísticos (no eventos confirmados), sensibilidad con inyecciones sintéticas y backtest de 24 meses (2024–2025). El mejor modelo tiene sMAPE mediana 5.71% frente a 7.05% de la baseline en 51 jurisdicciones; gana en 46. No es proyección futura.
- [x] Patrones horarios del lote local de 50 perfiles convertidos a tiempo local por zona IANA; meses incompletos se identifican. Clima sigue separado y no se une al consumo.
- [x] HTML autónomo del tablero (8.5 MB) cargado en el prefijo privado `site/` de S3 en `us-east-1`; una URL prefirmada temporal se generó desde la consola. El objeto reúne los datos versionados de 10 perfiles, no el paquete temporal de 50.
- [ ] Llegar a 10,000 perfiles procesados: los IDs restantes continúan siendo candidatos, no descargas realizadas.
- [ ] Flujo AWS completo: EMR Serverless rechazó el inicio por falta de permisos; no existe stream Kinesis ni distribución CloudFront. S3 no es público; la URL prefirmada es temporal y no proporciona dominio permanente.
- [ ] Reproducir la razón Colorado/EIA de 87.16% desde su agregado fuente. No se presenta como precisión ni como resultado validado.

Los resultados versionados del tablero corresponden al piloto de 10 perfiles; el lote de 50 se conserva localmente para validación y presentación controlada. ResStock contiene perfiles modelados y EIA ventas agregadas de todo el sector residencial: sus coberturas son distintas. Clima permanece como serie independiente.

## Abrir el dashboard local

Desde la raíz del repositorio, ejecuta:

```bash
python3 -m http.server 8000 -d tablero
```

Después abre <http://localhost:8000/>. La interfaz no requiere instalación de paquetes ni conexión a internet; las tablas y el manifiesto ya están en `tablero/data/v1/`.

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
- [Plan definitivo del proyecto final](docs/plan-definitivo-general.md)
- [Plan de implementación del bloque Omar](docs/plan-bloque-omar.md)
- [Plan operativo de desarrollo V2 y observaciones del profesor](docs/plan-operativo-desarrollo-v2.md)
- [División del desarrollo en cuatro bloques y flujo de PR](docs/division-bloques-equipo-v2.md)
- [Tareas para la revisión de avance del 17 de noviembre](docs/plan-avance-17-noviembre.md)
- [Validación inicial de fuentes](docs/validacion-inicial-fuentes.md)
- [Resultados de la primera muestra](docs/resultados-muestra-inicial.md)
- [Contenido resumido por diapositiva en JSON](docs/contenido-presentacion-avance.json)
- [Versión legible del contenido de presentación](docs/presentacion-avance-17-noviembre.md)
- [PowerPoint borrador anterior, pendiente de aplicar el estilo final](presentaciones/Avance_Big_Data_17_noviembre_2026.pptx)
- [PDF borrador anterior](presentaciones/Avance_Big_Data_17_noviembre_2026.pdf)
- [Esquema conceptual y calidad inicial de datos](docs/esquema-inicial-calidad-datos.md)
- [Decisión inicial de alcance y MVP](docs/decision-alcance-mvp.md)
- [Especificación del tablero y dirección visual isométrica](docs/especificacion-tablero.md)
- [Plan urgente de la siguiente etapa: dashboard, AWS, escala y analítica](docs/plan-urgente-siguiente-etapa.md)
- [Contrato Gold consumido por el dashboard](docs/contrato-dashboard-datos.md)
- [Contrato de datos Gold v2 del dashboard](docs/contrato-dashboard-datos-v2.md)
- [Ejecución del pipeline y exportación al dashboard](docs/ejecucion-job-spark-local.md)
- [Ingesta de ResStock por lotes](docs/ingesta-resstock-lotes.md)
- [Adaptación del lote ResStock a Spark](docs/adaptador-lote-resstock-spark.md)
- [Publicación privada del dashboard v2 en S3](docs/publicacion-s3-dashboard-v2.md)
- [Lote exploratorio ResStock de 50 perfiles](docs/lote-resstock-50.md)
- [Anomalías y backtest de pronóstico EIA](docs/analitica-anomalias-pronostico.md)
- [Despliegue temporal en S3 privado](docs/despliegue-temporal-s3.md)
- [Guía breve para presentar el proyecto](docs/guia-demostracion-profesor.md)
- [Guía del dashboard local](tablero/README.md)

El plan de desarrollo es una propuesta de organización basada en la guía disponible; se actualizará si el profesor comparte una rúbrica detallada o confirma fechas y requisitos adicionales.

Los candidatos de anomalías y las métricas de backtest son exploratorios y están etiquetados en el tablero; las anomalías no se confirmaron con eventos externos y el backtest no genera una predicción futura.

## Repositorio

Este repositorio es la referencia compartida para código, documentación, decisiones y avances del proyecto. No se publicarán aquí credenciales, tokens, datos personales de terceros ni conjuntos de datos que no tengan autorización de redistribución.
