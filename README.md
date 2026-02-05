# sys-snapshots-and-metrics

Local, portable system metrics snapshot tool for Windows.

---

## Table of Contents

- [Español (Spanish)](#español)
  - [Descripción](#descripción)
  - [Características](#características)
  - [Requisitos](#requisitos)
  - [Instalación](#instalación)
  - [Uso](#uso)
  - [Arquitectura](#arquitectura)
  - [Métricas Capturadas](#métricas-capturadas)
  - [Empaquetado](#empaquetado)
  - [Solución de Problemas](#solución-de-problemas)
- [English](#english)
  - [Description](#description)
  - [Features](#features)
  - [Requirements](#requirements)
  - [Installation](#installation)
  - [Usage](#usage)
  - [Architecture](#architecture)
  - [Captured Metrics](#captured-metrics)
  - [Packaging](#packaging)
  - [Troubleshooting](#troubleshooting)

---

# Español

## Descripción

**sys-snapshots-and-metrics** es una herramienta local y portable que captura métricas del sistema en intervalos regulares, almacena snapshots en una base de datos SQLite y genera reportes automáticos en formatos Markdown y HTML.

El proyecto está diseñado para ejecutarse de forma **100% local**:
- No es una aplicación web
- No tiene interfaz gráfica propia
- No corre como servicio o daemon
- No envía datos a ningún servidor externo

Todo el procesamiento y los archivos generados permanecen en la carpeta donde se ejecuta el programa.

## Características

- **Captura automática** de métricas del sistema (CPU, RAM, disco, red, procesos)
- **Almacenamiento local** en base de datos SQLite
- **Análisis estadístico** con detección de anomalías
- **Reportes automáticos** en Markdown y HTML con gráficos
- **Modo portable** - ejecutable standalone sin dependencias
- **100% privado** - sin conexión a internet requerida

## Requisitos

### Para usar el ejecutable (.exe)
- Windows 10 o 11
- No requiere Python instalado
- No requiere conexión a internet

### Para desarrollo
- Python 3.10 o superior
- Dependencias listadas en `requirements.txt`

## Instalación

### Opción 1: Usar el ejecutable (recomendado)

1. Descomprimir la carpeta `dist\sys-snapshots-and-metrics\`
2. Ejecutar `sys-snapshots-and-metrics.exe`
3. Esperar la captura de métricas (~20 segundos)
4. El reporte se abre automáticamente en el navegador

### Opción 2: Desde código fuente

```bash
# Clonar el repositorio
git clone <repository-url>
cd sys-snapshots-and-metrics

# Crear entorno virtual (recomendado)
python -m venv .venv
.venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar en modo automático
python -m src.main
```

## Uso

### Modo Automático (Recomendado)

Ejecutar sin argumentos (doble click al `.exe` o `python -m src.main`):

```bash
python -m src.main
```

**Flujo completo:**
1. Elimina `snapshots.db` si existe (reset de datos)
2. Inicializa una nueva base de datos SQLite
3. Captura métricas durante ~20 segundos
4. Genera:
   - `reports/report.md`
   - `reports/report.html`
   - `reports/report_resources.png` (gráfico de recursos)
5. Abre automáticamente el reporte HTML en el navegador

### Modo CLI (Avanzado)

#### Inicializar base de datos
```bash
python -m src.main init-db [--db ruta/a/db.sqlite]
```

#### Ejecutar captura de métricas
```bash
python -m src.main run --interval 2 --duration 20 [--db ruta/a/db.sqlite]
```

**Parámetros:**
- `--interval`: Segundos entre capturas (por defecto: 1)
- `--duration`: Duración total en segundos; 0 = infinito (por defecto: 10)
- `--db`: Ruta a la base de datos (opcional)

#### Generar reporte
```bash
python -m src.main report --last 50 [--out reports\custom.md] [--db ruta/a/db.sqlite]
```

**Parámetros:**
- `--last`: Número de snapshots a incluir (por defecto: 20)
- `--out`: Ruta del archivo de salida (opcional)
- `--db`: Ruta a la base de datos (opcional)

### Archivos Generados

```
sys-snapshots-and-metrics/
├── snapshots.db                    # Base de datos SQLite
└── reports/
    ├── report.md                   # Reporte en Markdown
    ├── report.html                 # Reporte en HTML
    └── report_resources.png        # Gráfico de recursos
```

## Arquitectura

```
sys-snapshots-and-metrics/
│
├── src/
│   ├── main.py         # Orquestador CLI y modo automático
│   ├── collector.py    # Captura de métricas del sistema
│   ├── runner.py       # Loop de ejecución (interval / duration)
│   ├── storage.py      # Persistencia en SQLite
│   ├── analyzer.py     # Análisis estadístico y detección de anomalías
│   ├── report.py       # Generación de reportes (Markdown, HTML, gráficos)
│   └── config.py       # Configuración central del proyecto
│
├── reports/            # Reportes generados
├── snapshots.db        # Base de datos SQLite
└── README.md
```

### Flujo de Datos

```
collector.py → runner.py → storage.py → analyzer.py → report.py
     ↓            ↓            ↓            ↓            ↓
  Métricas    Deltas de    SQLite      Estadísticas   MD/HTML
   del SO       red                    y anomalías    + gráficos
```

## Métricas Capturadas

### CPU
- Porcentaje de uso (0-100%)

### Memoria
- Total (bytes)
- Usada (bytes)
- Porcentaje de uso (0-100%)

### Disco
- Ruta monitoreada
- Total (bytes)
- Usado (bytes)
- Porcentaje de uso (0-100%)

### Red
- Bytes enviados (contador absoluto)
- Bytes recibidos (contador absoluto)
- Deltas por snapshot (calculados entre capturas)

### Procesos
- Top N procesos (configurable, por defecto 5)
- PID, nombre, uso de CPU, memoria RSS

## Empaquetado

El proyecto se empaqueta usando PyInstaller en modo carpeta:

```bash
pyinstaller --clean --noconfirm --name sys-snapshots-and-metrics --windowed src\main.py ^
  --hidden-import matplotlib ^
  --hidden-import matplotlib.backends.backend_agg ^
  --collect-all matplotlib ^
  --collect-all numpy ^
  --collect-all markdown
```

**Entregable final:** `dist\sys-snapshots-and-metrics\`

## Solución de Problemas

### El ejecutable no inicia
- Verificar que no esté bloqueado por antivirus
- Ejecutar como administrador si es necesario
- Revisar logs en la consola (si se ejecuta desde terminal)

### No se genera el reporte
- Verificar que la carpeta `reports/` tenga permisos de escritura
- Asegurar que hay snapshots en la base de datos
- Revisar que las dependencias estén instaladas (modo desarrollo)

### Errores de permisos al capturar procesos
- Normal en Windows - algunos procesos del sistema requieren privilegios elevados
- La herramienta continúa capturando los procesos accesibles

### Base de datos bloqueada
- Cerrar otras instancias del programa
- Eliminar `snapshots.db` y reiniciar

---

# English

## Description

**sys-snapshots-and-metrics** is a local and portable tool that captures system metrics at regular intervals, stores snapshots in a SQLite database, and generates automatic reports in Markdown and HTML formats.

The project is designed to run in a **100% local** manner:
- It is not a web application
- It does not provide its own graphical interface
- It does not run as a service or daemon
- It does not send data to any external server

All processing and generated files remain inside the folder where the program is executed.

## Features

- **Automatic capture** of system metrics (CPU, RAM, disk, network, processes)
- **Local storage** in SQLite database
- **Statistical analysis** with anomaly detection
- **Automatic reports** in Markdown and HTML with charts
- **Portable mode** - standalone executable with no dependencies
- **100% private** - no internet connection required

## Requirements

### To use the executable (.exe)
- Windows 10 or 11
- No Python installation required
- No internet connection required

### For development
- Python 3.10 or higher
- Dependencies listed in `requirements.txt`

## Installation

### Option 1: Use the executable (recommended)

1. Extract the `dist\sys-snapshots-and-metrics\` folder
2. Run `sys-snapshots-and-metrics.exe`
3. Wait for metrics capture (~20 seconds)
4. The report opens automatically in the browser

### Option 2: From source code

```bash
# Clone the repository
git clone <repository-url>
cd sys-snapshots-and-metrics

# Create virtual environment (recommended)
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run in automatic mode
python -m src.main
```

## Usage

### Automatic Mode (Recommended)

Run without arguments (double-click the `.exe` or `python -m src.main`):

```bash
python -m src.main
```

**Complete flow:**
1. Deletes `snapshots.db` if it exists (data reset)
2. Initializes a new SQLite database
3. Captures metrics for ~20 seconds
4. Generates:
   - `reports/report.md`
   - `reports/report.html`
   - `reports/report_resources.png` (resource chart)
5. Automatically opens the HTML report in the browser

### CLI Mode (Advanced)

#### Initialize database
```bash
python -m src.main init-db [--db path/to/db.sqlite]
```

#### Run metrics capture
```bash
python -m src.main run --interval 2 --duration 20 [--db path/to/db.sqlite]
```

**Parameters:**
- `--interval`: Seconds between captures (default: 1)
- `--duration`: Total duration in seconds; 0 = infinite (default: 10)
- `--db`: Database path (optional)

#### Generate report
```bash
python -m src.main report --last 50 [--out reports\custom.md] [--db path/to/db.sqlite]
```

**Parameters:**
- `--last`: Number of snapshots to include (default: 20)
- `--out`: Output file path (optional)
- `--db`: Database path (optional)

### Generated Files

```
sys-snapshots-and-metrics/
├── snapshots.db                    # SQLite database
└── reports/
    ├── report.md                   # Markdown report
    ├── report.html                 # HTML report
    └── report_resources.png        # Resource chart
```

## Architecture

```
sys-snapshots-and-metrics/
│
├── src/
│   ├── main.py         # CLI orchestrator and automatic mode
│   ├── collector.py    # System metrics capture
│   ├── runner.py       # Execution loop (interval / duration)
│   ├── storage.py      # SQLite persistence
│   ├── analyzer.py     # Statistical analysis and anomaly detection
│   ├── report.py       # Report generation (Markdown, HTML, charts)
│   └── config.py       # Central project configuration
│
├── reports/            # Generated reports
├── snapshots.db        # SQLite database
└── README.md
```

### Data Flow

```
collector.py → runner.py → storage.py → analyzer.py → report.py
     ↓            ↓            ↓            ↓            ↓
   OS          Network      SQLite      Statistics    MD/HTML
  Metrics       deltas                  & anomalies   + charts
```

## Captured Metrics

### CPU
- Usage percentage (0-100%)

### Memory
- Total (bytes)
- Used (bytes)
- Usage percentage (0-100%)

### Disk
- Monitored path
- Total (bytes)
- Used (bytes)
- Usage percentage (0-100%)

### Network
- Bytes sent (absolute counter)
- Bytes received (absolute counter)
- Per-snapshot deltas (calculated between captures)

### Processes
- Top N processes (configurable, default 5)
- PID, name, CPU usage, RSS memory

## Packaging

The project is packaged using PyInstaller in folder mode:

```bash
pyinstaller --clean --noconfirm --name sys-snapshots-and-metrics --windowed src\main.py ^
  --hidden-import matplotlib ^
  --hidden-import matplotlib.backends.backend_agg ^
  --collect-all matplotlib ^
  --collect-all numpy ^
  --collect-all markdown
```

**Final deliverable:** `dist\sys-snapshots-and-metrics\`

## Troubleshooting

### Executable won't start
- Verify it's not blocked by antivirus
- Run as administrator if necessary
- Check logs in console (if running from terminal)

### Report not generated
- Verify `reports/` folder has write permissions
- Ensure there are snapshots in the database
- Check that dependencies are installed (development mode)

### Permission errors when capturing processes
- Normal on Windows - some system processes require elevated privileges
- The tool continues capturing accessible processes

### Database locked
- Close other instances of the program
- Delete `snapshots.db` and restart

---

## License

This project is provided as-is for system monitoring purposes.

## Contributing

Contributions are welcome! Please ensure all code is well-documented and follows the existing code style.
