# Build und Distribution

## Paket bauen

### 1. Build-Tools installieren
```bash
pip install --upgrade pip setuptools wheel build twine
```

### 2. Paket bauen
```bash
python -m build
```

Dies erstellt zwei Dateien im `dist/` Verzeichnis:
- Eine `.tar.gz` Source Distribution
- Eine `.whl` Wheel Distribution

## Installation aus lokalem Repository

### Aus lokalem Verzeichnis installieren
```bash
pip install /pfad/zum/ElectricComponentCheck
```

### Aus lokalem Build installieren
```bash
pip install dist/electric_component_check-0.1.0-py3-none-any.whl
```

## Distribution über eigenes Git-Repository

### 1. Direktinstallation von GitHub/GitLab
```bash
# Von GitHub
pip install git+https://github.com/yourusername/ElectricComponentCheck.git

# Von einem spezifischen Branch
pip install git+https://github.com/yourusername/ElectricComponentCheck.git@branch-name

# Von einem spezifischen Tag/Release
pip install git+https://github.com/yourusername/ElectricComponentCheck.git@v0.1.0

# Von GitLab
pip install git+https://gitlab.com/yourusername/ElectricComponentCheck.git
```

### 2. In requirements.txt verwenden
```txt
# Von GitHub
git+https://github.com/yourusername/ElectricComponentCheck.git

# Spezifische Version
git+https://github.com/yourusername/ElectricComponentCheck.git@v0.1.0

# Mit Egg-Fragment (für editable installs)
git+https://github.com/yourusername/ElectricComponentCheck.git#egg=electric-component-check
```

### 3. Eigenen PyPI-Server aufsetzen (Optional)

#### Mit `pypiserver`
```bash
# Installieren
pip install pypiserver passlib

# Server starten
pypi-server run -p 8080 ./packages

# Paket hochladen
twine upload --repository-url http://localhost:8080 dist/*

# Von eigenem Server installieren
pip install --index-url http://localhost:8080/simple/ electric-component-check
```

#### Mit pip.conf konfigurieren
Erstellen Sie `~/.pip/pip.conf` (Linux/macOS) oder `%APPDATA%\pip\pip.ini` (Windows):
```ini
[global]
extra-index-url = http://your-server:8080/simple/
trusted-host = your-server
```

## Development Installation

Für die Entwicklung (editierbare Installation):
```bash
pip install -e .

# Mit dev dependencies
pip install -e ".[dev]"
```

## Paket testen

```bash
# Unit Tests ausführen
python -m pytest test/

# Mit Coverage
python -m pytest --cov=src test/
```

## Version aktualisieren

1. Version in folgenden Dateien aktualisieren:
   - `setup.py` (version)
   - `pyproject.toml` ([project] version)
   - `src/__init__.py` (__version__)

2. Git Tag erstellen:
```bash
git tag -a v0.1.0 -m "Version 0.1.0"
git push origin v0.1.0
```

## GitHub Release erstellen

1. Gehe zu deinem Repository auf GitHub
2. Klicke auf "Releases" → "Draft a new release"
3. Wähle den Tag (z.B. v0.1.0)
4. Füge die built artifacts aus `dist/` hinzu
5. Beschreibe die Änderungen
6. Publish Release

## Troubleshooting

### Import-Probleme
Stelle sicher, dass `src/__init__.py` existiert und die wichtigsten Module exportiert.

### UI-Dateien nicht gefunden
Überprüfe `MANIFEST.in` und `package_data` in `setup.py`.

### Dependencies fehlen
Prüfe ob alle Dependencies in `requirements.txt` und `pyproject.toml` aufgeführt sind.
