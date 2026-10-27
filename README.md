# Asistente Monitor-IoT

Aplicación web con un agente inteligente (GLM 4.6) que genera modelos de arquitecturas de
monitoreo IoT en formato XMI, conformes al metamodelo **Monitor-IoT** propuesto por
L. Erazo-Garzón, P. Cedillo, G. Rossi y J. Moyano, *"A Domain-Specific Language for Modeling
IoT System Architectures That Support Monitoring"*, IEEE Access, vol. 10, 2022 (RNF-24).

Equipo: Juan Pedro Pesántez, Joaquín Méndez, Jordan Quizhpi y Anaela Romero.

## Estructura

```
backend/                  API en Python (FastAPI)
  app/metamodel.py        Lee tesismetamodelo.ecore (base de todo lo demás)
  app/model.py            Modelo en memoria y referencias por posición
  app/builder.py          Especificación JSON del agente → modelo (completa relaciones opuestas e ids)
  app/xmi.py              Escritor y lector XMI compatibles con Obeo Designer
  app/validator.py        Validador independiente: metamodelo + coherencia del monitoreo
  app/agent/              Agente (workflow de 6 pasos) y capa intermedia hacia GLM 4.6
  app/knowledge/          Metamodelo y casos de ejemplo en inglés
  tests/                  Pruebas automáticas
frontend/                 Interfaz web (React + Vite + Cytoscape): chat, workflow y visor
tools/emf-check/          Verificación de XMI con EMF real (la librería de Obeo Designer)
docs/                     Documentación de los avances
```

## Cómo ejecutarlo

Requisitos: Python 3.11+ y Node.js 18+.

```bash
cd backend
pip install -r requirements.txt
```

```bash
cd frontend
npm install
npm run build
```

```bash
cd backend
python -m uvicorn app.main:app --port 8000
```

Abrir http://localhost:8000.

Para desarrollar la interfaz con recarga automática, dejar el backend corriendo y en otra
terminal ejecutar `npm run dev` dentro de `frontend` (abre http://localhost:5173).

### Conectar GLM 4.6

Copiar `backend/.env.example` como `backend/.env` y completar `GLM_API_KEY`. Sin clave, el
sistema funciona en **modo demostración** (el chat responde con instrucciones y se puede
cargar el caso de ejemplo o abrir un XMI).

## Pruebas

```bash
cd backend
python -m pytest -q
```

Verificar un XMI con EMF (requiere Java 11+ y los jars de EMF incluidos en Obeo Designer):

```bash
java -cp "<plugins>/org.eclipse.emf.common_2.16.0.v20190625-1131.jar;<plugins>/org.eclipse.emf.ecore_2.19.0.v20190822-1451.jar;<plugins>/org.eclipse.emf.ecore.xmi_2.16.0.v20190528-0725.jar" tools/emf-check/EmfCheck.java backend/app/knowledge/tesismetamodelo.ecore modelo.MonitorIoT
```
