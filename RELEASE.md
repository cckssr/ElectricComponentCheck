# GitHub Workflow für Releases (Optional)

Erstellen Sie `.github/workflows/release.yml` für automatische Releases:

```yaml
name: Build and Release

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install build twine
    
    - name: Build package
      run: python -m build
    
    - name: Create Release
      uses: softprops/action-gh-release@v1
      with:
        files: dist/*
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## GitLab CI/CD Workflow (Optional)

Erstellen Sie `.gitlab-ci.yml`:

```yaml
stages:
  - build
  - release

build:
  stage: build
  image: python:3.11
  script:
    - pip install build
    - python -m build
  artifacts:
    paths:
      - dist/
  only:
    - tags

release:
  stage: release
  image: python:3.11
  script:
    - echo "Creating release"
  dependencies:
    - build
  only:
    - tags
```

## Versionierung

Verwenden Sie semantische Versionierung (SemVer):
- **MAJOR.MINOR.PATCH** (z.B. 1.2.3)
- **MAJOR**: Inkompatible API-Änderungen
- **MINOR**: Neue Features, abwärtskompatibel
- **PATCH**: Bugfixes, abwärtskompatibel

Beispiel für Version Bump:
```bash
# Aktuelle Version: 0.1.0

# Patch Release (Bugfix)
# Neue Version: 0.1.1

# Minor Release (Neues Feature)
# Neue Version: 0.2.0

# Major Release (Breaking Change)
# Neue Version: 1.0.0
```
