# Avance 1 — Base técnica funcionando

**Fecha:** 28 de octubre de 2026 · **Proyecto:** Asistente Monitor-IoT (AMIoT)

## Objetivo del avance

Tener funcionando, de punta a punta, la cadena que convierte una descripción del modelo en un
XMI válido y lo muestra en la interfaz web, con la estructura definida en la ERS (chat,
workflow y visor en una sola pantalla). El agente con GLM 4.6 se conecta en el avance 2 sobre
esta base.

## Qué se entrega

| Componente (WBS) | Estado | Requisitos cubiertos |
|---|---|---|
| Lector del metamodelo `.ecore` | Completo | RF-27 (parcial), RNF-17 |
| Generador XMI (5.2) | Completo | RF-10, RNF-07, RNF-08 |
| Validador XMI independiente (5.2) | Completo | RF-11, RF-12, RNF-09, RNF-12 |
| Interfaz web: chat y workflow (6.2) | Completo (sin carga de PDF/DOCX) | RI-01, RI-02, RI-04, RI-05, RF-01, RF-16, RF-17 |
| Visor gráfico (6.3) | Vista Arquitectura | RF-18, RF-19, RF-21, RF-22, RF-23, RI-03 |
| Descarga del XMI | Completo | RF-24, RF-25, RF-26 (versiones en la sesión) |
| Capa intermedia hacia GLM 4.6 (4.2) | Lista, en modo demostración | RNF-06, RNF-13, respuesta a R001/R011 |
| Caso de ejemplo del artículo en inglés (3.2) | 1 caso | RF-28 (parcial), RNF-11 |

## Decisiones técnicas

- **El agente no escribirá el XMI directamente** (respuesta planificada al riesgo R002). Entrega
  una especificación JSON con el modelo en forma de árbol y referencias por clave; el programa
  calcula las referencias por posición (`//@containsEntity.0/@containsComputingNode.1`), completa
  las relaciones de doble sentido y asigna los identificadores.
- **Todo se guía por el `.ecore`**: generador, lector y validador leen el metamodelo en tiempo de
  ejecución. Si el metamodelo cambia, basta con reemplazar el archivo (RNF-17).
- **Se valida exactamente lo que se entrega**: cada versión se escribe en XMI, se vuelve a leer
  y se valida lo leído.
- **Capa intermedia de modelo de lenguaje**: el agente usa la API compatible con OpenAI de GLM
  4.6; cambiar de proveedor o de versión es cuestión de configuración.

## Evidencias de calidad

- El XMI del caso de ejemplo (99 elementos, 3 flujos, 13 enlaces) pasa nuestra validación sin
  errores ni advertencias **y se abre y valida sin errores con EMF**, la misma librería que usa
  Obeo Designer (`tools/emf-check`). Mitiga el riesgo R007.
- Sobre los tres modelos existentes, el validador detecta los problemas que la ERS menciona
  (enlaces incompletos y propiedades sin plantilla). En `ModeloArquitecturaIoT.MonitorIoT`
  coincide con EMF en las 6 propiedades sin plantilla, y además detecta cadenas de enlaces
  cortadas y relaciones de doble sentido incompletas, que EMF no revisa.
- Los tres modelos existentes se leen y se vuelven a escribir sin perder información.
- 7 pruebas automáticas (`backend/tests`).

## Cómo demostrarlo

1. Ejecutar la aplicación (ver README) y abrir http://localhost:8000.
2. Pulsar **Cargar caso de ejemplo**: el workflow avanza paso a paso, el chat muestra el resumen
   y el visor dibuja la arquitectura.
3. En el visor: elegir un flujo para resaltar su camino, hacer clic en un elemento para ver sus
   datos, revisar las pestañas **Validación** y **XMI**.
4. Descargar el XMI (.MonitorIoT o .xmi) y abrirlo en Obeo Designer.
5. Con el botón **+** abrir `ModeloP.MonitorIoT` para ver cómo se informan sus errores; al
   descargarlo, el sistema advierte que no es válido.

## Plan de los siguientes avances

**Avance 2 — Agente GLM 4.6**
- Conexión real con GLM 4.6 y especialización con el metamodelo, el proceso de diseño y los
  casos de ejemplo (RF-07 a RF-09, RF-27).
- El agente produce la especificación JSON a partir del caso del usuario; preguntas de
  aclaración y supuestos visibles (RF-04, RF-05).
- Corrección automática: los errores del validador se devuelven al agente (RF-13).
- Ajustes por chat sobre el modelo actual con nuevas versiones (RF-14), resumen final (RF-15).
- Carga de documentos PDF, DOCX y TXT (RF-02, RF-03).
- Traducción y corrección de los modelos existentes y nuevos casos de ejemplo (R003).

**Avance 3 — Pulido, pruebas y despliegue**
- Vistas Sistema, Redes y Categorías (RF-20).
- Casos de prueba y medición del % de XMI válidos (RF-29, RNF-22); pruebas con modelos de 200
  elementos (RNF-03).
- Evaluación con usuarios (TAM, RNF-23), publicación con HTTPS (RNF-15), manuales.
