# ElectricComponentCheck - Quick Start

## Installation

### Option 1: Von lokalem Verzeichnis
```bash
cd /pfad/zum/ElectricComponentCheck
pip install .
```

### Option 2: Von Git Repository
```bash
# Direkt von GitHub/GitLab
pip install git+https://github.com/yourusername/ElectricComponentCheck.git

# Spezifische Version
pip install git+https://github.com/yourusername/ElectricComponentCheck.git@v0.1.0
```

### Option 3: Development Installation
```bash
cd /pfad/zum/ElectricComponentCheck
pip install -e .
```

## Paket bauen

```bash
# Build-Tools installieren
pip install build

# Paket bauen
python -m build
```

Dies erstellt die Distribution-Dateien in `dist/`:
- `electric_component_check-0.1.0.tar.gz` (Source Distribution)
- `electric_component_check-0.1.0-py3-none-any.whl` (Wheel Distribution)

## Anwendung starten

Nach der Installation können Sie die Anwendung starten mit:

```bash
electric-component-check
```

Oder mit Python:

```bash
python -m mainwindow
```

## Weitere Informationen

Siehe `BUILD.md` für detaillierte Anweisungen zur Distribution und Veröffentlichung.
