# Asistente Monitor-IoT

Aplicación web con un agente inteligente (GLM 4.6) que genera modelos de arquitecturas de
monitoreo IoT en formato XMI, conformes al metamodelo **Monitor-IoT**. El usuario describe su
caso por chat y obtiene un modelo validado, dibujado en pantalla y listo para abrir en Obeo
Designer.

El metamodelo y su notación gráfica son de L. Erazo-Garzón, P. Cedillo, G. Rossi y J. Moyano,
*"A Domain-Specific Language for Modeling IoT System Architectures That Support Monitoring"*,
IEEE Access, vol. 10, pp. 61639-61665, 2022. DOI: 10.1109/ACCESS.2022.3181166.

**Equipo:** Juan Pedro Pesántez, Joaquín Méndez, Jordan Quizhpi y Anaela Romero.

---

## Estado del proyecto

El proyecto se entrega en tres avances.

| Avance | Contenido | Estado |
|---|---|---|
| **1. Base técnica** | Lector del metamodelo, generador y validador XMI, interfaz web (chat, workflow y visor), caso de ejemplo del artículo | ✅ Entregado |
| **2. Agente GLM 4.6** | El agente genera el modelo desde el caso del usuario, documentos PDF/DOCX/TXT, aclaraciones, ajustes por chat | ⏳ Pendiente |
| **3. Pulido y despliegue** | Vistas de sistema, redes y categorías, casos de prueba, evaluación TAM, publicación con HTTPS | ⏳ Pendiente |

Detalle del Avance 1: [docs/AVANCE_1.md](docs/AVANCE_1.md) ·
Presentación: [docs/presentacion/Avance1_Asistente_Monitor-IoT.pptx](docs/presentacion/Avance1_Asistente_Monitor-IoT.pptx)

---

## Especificaciones técnicas

| Parte | Tecnología |
|---|---|
| Backend | Python 3.11 o superior, FastAPI, Uvicorn |
| Frontend | Node.js 18 o superior, React 18, Vite 5, TypeScript, Cytoscape.js |
| Modelo de lenguaje | GLM 4.6 (Z.ai) a través de su API compatible con OpenAI |
| Metamodelo | `tesismetamodelo.ecore` (espacio de nombres `http://www.uazuay.edu.ec/MonitorIoT`) |
| Formato de salida | XMI 2.0, extensiones `.MonitorIoT` o `.xmi` |
| Verificación opcional con EMF | Java 11 o superior y los jars de EMF de Obeo Designer |
| Navegadores | Chrome, Edge o Firefox actuales; resolución mínima 1366 × 768 |
| Sistemas operativos probados | Windows 11 (también funciona en macOS y Linux) |

### Estructura del repositorio

```
backend/                  API en Python (FastAPI)
  app/metamodel.py        Lee tesismetamodelo.ecore (base de todo lo demás)
  app/model.py            Modelo en memoria y referencias por posición
  app/builder.py          Especificación JSON del agente → modelo (relaciones opuestas e ids)
  app/xmi.py              Escritor y lector XMI compatibles con Obeo Designer
  app/validator.py        Validador independiente: metamodelo + coherencia del monitoreo
  app/sessions.py         Sesiones, versiones del modelo y pasos del workflow
  app/agent/              Agente (workflow de 6 pasos) y capa intermedia hacia GLM 4.6
  app/knowledge/          Metamodelo y casos de ejemplo en inglés
  tests/                  Pruebas automáticas
frontend/                 Interfaz web: chat, workflow y visor gráfico
tools/emf-check/          Verificación de un XMI con EMF real
docs/                     Documentación y presentación de cada avance
```

---

## Cómo ejecutarlo en otra máquina

### 1. Instalar los requisitos

- **Git**: https://git-scm.com
- **Python 3.11 o superior**: https://www.python.org/downloads (en Windows, marcar
  *Add Python to PATH* durante la instalación).
- **Node.js 18 o superior** (versión LTS): https://nodejs.org

Comprobar en una terminal:

```bash
git --version
python --version
node --version
```

En macOS y Linux usar `python3` en lugar de `python` en todos los comandos.

### 2. Descargar el proyecto

```bash
git clone https://github.com/Jhampier-u/MonitorIOT.git
cd MonitorIOT
```

### 3. Instalar el backend

Se recomienda un entorno virtual para no mezclar librerías con otros proyectos.

Windows (PowerShell):

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cd ..
```

macOS / Linux:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ..
```

Si PowerShell no permite activar el entorno, ejecutar una vez
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

### 4. Compilar la interfaz web

```bash
cd frontend
npm install
npm run build
cd ..
```

Esto crea `frontend/dist`, que el backend sirve automáticamente.

### 5. Iniciar la aplicación

Con el entorno virtual activado:

```bash
cd backend
python -m uvicorn app.main:app --port 8000
```

Abrir **http://localhost:8000** en el navegador.

### 6. (Opcional) Conectar GLM 4.6

Sin clave, el sistema funciona en **modo demostración**: el chat responde con instrucciones,
se puede cargar el caso de ejemplo y se pueden abrir XMI existentes. Para activar el agente:

1. Copiar `backend/.env.example` como `backend/.env`.
2. Escribir la clave en `GLM_API_KEY=` (se obtiene en https://z.ai).
3. Reiniciar el backend. El chat mostrará "Agente: glm-4.6" en lugar de "Modo demostración".

El archivo `.env` está en `.gitignore`: **nunca** debe subirse al repositorio.

---

## Qué probar en el Avance 1

1. Pulsar **Cargar caso de ejemplo** (o escribir *ejemplo* en el chat): el workflow avanza paso
   a paso, el chat muestra un resumen y el visor dibuja la arquitectura.
2. En el visor: elegir un flujo para resaltar su camino, hacer clic en un elemento para ver sus
   datos y usar los botones de zoom.
3. Revisar las pestañas **Validación** y **XMI**.
4. Descargar el modelo como `.MonitorIoT` o `.xmi` y abrirlo en Obeo Designer.
5. Con el botón **+** abrir un XMI existente (por ejemplo, `ModeloP.MonitorIoT` del proyecto
   original) para ver cómo se informan sus errores. Al descargar un modelo inválido, el sistema
   advierte antes.

Un XMI de ejemplo ya generado está en `docs/ejemplos/EmergencyCase.MonitorIoT`.

---

## Desarrollo

Para trabajar en la interfaz con recarga automática, dejar el backend corriendo en el puerto
8000 y en otra terminal:

```bash
cd frontend
npm run dev
```

Abrir http://localhost:5173 (las llamadas a `/api` se redirigen al backend).

### Pruebas automáticas

```bash
cd backend
python -m pytest -q
```

### Verificar un XMI con EMF (opcional)

Comprueba que un XMI se abre y valida con EMF, la librería que usa Obeo Designer. Requiere
Java 11 o superior y los jars de EMF, que vienen en la carpeta `plugins` de Obeo Designer.

Windows (separador `;`):

```powershell
$P = "C:\ruta\a\ObeoDesigner\plugins"
java -cp "$P\org.eclipse.emf.common_2.16.0.v20190625-1131.jar;$P\org.eclipse.emf.ecore_2.19.0.v20190822-1451.jar;$P\org.eclipse.emf.ecore.xmi_2.16.0.v20190528-0725.jar" tools/emf-check/EmfCheck.java backend/app/knowledge/tesismetamodelo.ecore docs/ejemplos/EmergencyCase.MonitorIoT
```

En macOS y Linux el separador del classpath es `:`. Las versiones de los jars pueden variar
según la instalación de Obeo Designer.

### Formato que entrega el agente

El agente no escribe el XMI directamente. Entrega una especificación JSON con el modelo como
árbol; cada objeto lleva su clase en `eClass`, una `key` opcional y referencias a otras keys.
El generador calcula las referencias por posición, completa las relaciones de doble sentido y
asigna los identificadores. Ver el ejemplo completo en
`backend/app/knowledge/examples/emergency_case.json` y la explicación en
`backend/app/builder.py`.

---

## Problemas frecuentes

| Problema | Solución |
|---|---|
| La página muestra "Not Found" en http://localhost:8000 | Falta compilar la interfaz: `npm run build` dentro de `frontend`, y reiniciar el backend |
| `python` no se reconoce | Reinstalar Python marcando *Add Python to PATH*, o usar `py` en Windows / `python3` en macOS y Linux |
| `ModuleNotFoundError: fastapi` | Activar el entorno virtual antes de iniciar el backend |
| El puerto 8000 está ocupado | Iniciar con `--port 8001` y abrir http://localhost:8001 |
| El chat dice "modo demostración" | Es lo esperado sin `GLM_API_KEY` en `backend/.env` |
