# sys-snapshots-and-metrics

Local, portable system metrics snapshot tool for Windows.

---

## Descripción (ES)

**sys-snapshots-and-metrics** es una herramienta local y portable que captura métricas del sistema en intervalos regulares, guarda snapshots en una base de datos SQLite y genera un reporte automático en formatos Markdown y HTML.

El proyecto está diseñado para ejecutarse de forma **100% local**:
- No es una aplicación web
- No tiene interfaz gráfica propia
- No corre como servicio o daemon
- No envía datos a ningún servidor externo

Todo el procesamiento y los archivos generados permanecen en la carpeta donde se ejecuta el programa.

---

## Objetivos del proyecto

- Capturar métricas del sistema de manera reproducible
- Evitar ruido entre ejecuciones en distintas máquinas
- Generar reportes automáticos, portables y fáciles de visualizar
- Poder distribuir la herramienta como un ejecutable (`.exe`) sin dependencias externas

---

## Arquitectura general
```
sys-snapshots-and-metrics/
│
├─ src/
│ ├─ main.py # Orquestador CLI y modo automático
│ ├─ collector.py # Captura de métricas del sistema
│ ├─ runner.py # Loop de ejecución (interval / duration)
│ ├─ storage.py # Persistencia en SQLite
│ ├─ analyzer.py # Análisis estadístico y detección de anomalías
│ ├─ report.py # Generación de reportes (Markdown, HTML, gráficos)
│ └─ config.py # Configuración central del proyecto
│
├─ reports/ # Reportes generados
├─ snapshots.db # Base de datos SQLite (solo la corrida actual en autorun)
├─ README.md

```
---

## Funcionamiento

### Modo automático (recomendado)

El modo automático se ejecuta cuando el programa se corre **sin argumentos**
(doble click al `.exe` (empaquetado mas abajo) o `python -m src.main`).

Flujo completo:

1. Elimina `snapshots.db` si existe (reset de datos)
2. Inicializa una nueva base de datos SQLite
3. Captura métricas durante ~20 segundos
4. Genera:
   - `reports/report.md`
   - `reports/report.html`
   - gráfico PNG de recursos (si hay datos suficientes)
5. Abre automáticamente el reporte HTML en el navegador

Este modo garantiza resultados limpios y comparables entre distintas máquinas.

---

## Uso como ejecutable (.exe)

### Requisitos
- Windows 10 o 11
- No requiere Python instalado
- No requiere conexión a internet

### Uso rápido

1. Descomprimir la carpeta entregada
2. Ejecutar `sys-snapshots-and-metrics.exe`
3. Esperar la captura de métricas
4. El reporte se abre automáticamente en el navegador

### Archivos generados
```
snapshots.db
reports/
├─ report.md
├─ report.html
└─ report_resources.png
```

---

## Uso avanzado (CLI)

Desde PowerShell, dentro de la carpeta del ejecutable:

```powershell
.\sys-snapshots-and-metrics.exe init-db
.\sys-snapshots-and-metrics.exe run --interval 2 --duration 20
.\sys-snapshots-and-metrics.exe report --last 50 --out reports\report.md
```
---

## Métricas capturadas
CPU: porcentaje de uso

### Memoria:

total

usada

porcentaje

### Disco:

ruta

total

usado

porcentaje

### Red:

bytes enviados y recibidos

deltas por snapshot

### Procesos:

PID

nombre

uso de CPU

memoria RSS

## Análisis y anomalías

### El análisis incluye:

Valores mínimo, promedio y máximo de CPU, memoria y disco

Totales de red calculados a partir de deltas

### Detección de anomalías por snapshot:

uso alto de CPU

uso alto de memoria

uso alto de red (configurable)

Los umbrales se definen en config.py.

Reportes
Markdown (report.md)
Versión técnica del reporte

Útil para debugging y versionado

HTML (report.html)
Renderizado completo del reporte

Tablas, listas y gráficos

Compatible con cualquier navegador

Se abre automáticamente al finalizar la ejecución

Privacidad y seguridad
No se envían datos a ningún servidor

No se requiere acceso a internet

No se ejecutan servicios en segundo plano

Todos los datos permanecen localmente

Desarrollo (modo Python)
Ejecutar en desarrollo
```bash
python -m src.main
Comandos disponibles
python -m src.main init-db
python -m src.main run --interval 1 --duration 10
python -m src.main report --last 20
```
## Empaquetado
### El proyecto se empaqueta usando PyInstaller en modo carpeta:
```bash
pyinstaller --clean --noconfirm --name sys-snapshots-and-metrics --windowed src\main.py ^
  --hidden-import matplotlib ^
  --hidden-import matplotlib.backends.backend_agg ^
  --collect-all matplotlib ^
  --collect-all numpy ^
  --collect-all markdown
``` 
El entregable final es la carpeta:

dist\sys-snapshots-and-metrics\


---

# sys-snapshots-and-metrics

Local, portable system metrics snapshot tool for Windows.

---

## Description (EN)

**sys-snapshots-and-metrics** is a local and portable tool that captures system metrics at regular intervals, stores snapshots in a SQLite database, and generates an automatic report in Markdown and HTML formats.

The project is designed to run in a **100% local** manner:
- It is not a web application
- It does not provide its own graphical interface
- It does not run as a service or daemon
- It does not send data to any external server

All processing and generated files remain inside the folder where the program is executed.

---

## Project objectives

- Capture system metrics in a reproducible way
- Avoid noise between executions on different machines
- Generate automatic, portable, and easy-to-read reports
- Distribute the tool as a standalone executable (`.exe`) with no external dependencies

---

## General architecture
```
sys-snapshots-and-metrics/
│
├─ src/
│ ├─ main.py # CLI orchestrator and automatic mode
│ ├─ collector.py # System metrics capture
│ ├─ runner.py # Execution loop (interval / duration)
│ ├─ storage.py # SQLite persistence
│ ├─ analyzer.py # Statistical analysis and anomaly detection
│ ├─ report.py # Report generation (Markdown, HTML, charts)
│ └─ config.py # Central project configuration
│
├─ reports/ # Generated reports
├─ snapshots.db # SQLite database (current run only in autorun)
├─ README.md
```

---

## Execution flow

### Automatic mode (recommended)

Automatic mode is executed when the program runs **without arguments**
(double-clicking the `.exe` (packaged as described below) or using `python -m src.main`).

Complete flow:

1. Deletes `snapshots.db` if it exists (data reset)
2. Initializes a new SQLite database
3. Captures metrics for approximately 20 seconds
4. Generates:
   - `reports/report.md`
   - `reports/report.html`
   - resource usage PNG chart (if enough data is available)
5. Automatically opens the HTML report in the web browser

This mode guarantees clean and comparable outputs across different machines.

---

## Executable (.exe) usage

### Requirements
- Windows 10 or 11
- No Python installation required
- No internet connection required

### Quick usage

1. Extract the delivered folder
2. Run `sys-snapshots-and-metrics.exe`
3. Wait while metrics are captured
4. The report opens automatically in the browser

### Generated files
snapshots.db
```
reports/
├─ report.md
├─ report.html
└─ report_resources.png
```

---

## Advanced usage (CLI)

From PowerShell, inside the executable folder:

```powershell
.\sys-snapshots-and-metrics.exe init-db
.\sys-snapshots-and-metrics.exe run --interval 2 --duration 20
.\sys-snapshots-and-metrics.exe report --last 50 --out reports\report.md
```
Captured metrics
CPU:

usage percentage

Memory:
total

used

percentage

Disk:
path

total

used

percentage

Network:
bytes sent and received

per-snapshot deltas

Processes:
PID

name

CPU usage

RSS memory

Analysis and anomalies
The analysis includes:
Minimum, average, and maximum values for CPU, memory, and disk usage

Network totals calculated from deltas

Anomaly detection per snapshot:
high CPU usage

high memory usage

high network usage (configurable)

Thresholds are defined in config.py.

Reports
Markdown (report.md)
Technical version of the report

Useful for debugging and versioning

HTML (report.html)
Fully rendered report

Tables, lists, and charts

Compatible with any modern browser

Automatically opened at the end of execution

Privacy and security
No data is sent to any external server

No internet access is required

No background services are executed

All data remains local to the machine

Development (Python mode)
Run in development
```bash
python -m src.main
```
Available commands
```bash
python -m src.main init-db
python -m src.main run --interval 1 --duration 10
python -m src.main report --last 20
```
Packaging
The project is packaged using PyInstaller in folder mode:

```bash
pyinstaller --clean --noconfirm --name sys-snapshots-and-metrics --windowed src\main.py ^
  --hidden-import matplotlib ^
  --hidden-import matplotlib.backends.backend_agg ^
  --collect-all matplotlib ^
  --collect-all numpy ^
  --collect-all markdown
```
The final deliverable is the folder:

dist\sys-snapshots-and-metrics\

