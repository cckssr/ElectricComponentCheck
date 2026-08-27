# Development

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e . --group dev
pre-commit install
```

## Project layout

```text
src/electric_component_check/   # the installable package
  mainwindow.py                 # app entry point / main window
  openbis_controller.py         # OpenBIS session, lookup, create/update, dataset upload
  lcr_controller.py             # LCR-500 connection + sweep, Qt-signal based
  plot_controller.py            # live sweep plot (pyqtgraph)
  ui/                           # Qt Designer source (form.ui) + generated *_ui.py
test/                           # pytest suite
docs/                           # reference material (OpenBIS schema export, etc.)
```

## The UI: `form.ui` is the source of truth

Widgets are laid out in Qt Designer (`src/electric_component_check/ui/form.ui`), not in
Python. After editing it, regenerate the Python module:

```bash
make ui
```

Never hand-edit `form_ui.py` or `calibration_ui.py` — they are overwritten by `make ui` and
the comment at the top of each says so.

## Common tasks

```bash
make lint        # ruff check
make format      # ruff format
make typecheck    # mypy
make test         # pytest
make run          # launch the app from source
```

`pre-commit` runs ruff (lint + format) and mypy on every commit once installed.

## Versioning and releases

The version lives in `pyproject.toml` (`[project].version`) and `src/electric_component_check/__init__.py`
(`__version__`) — update both together.

To cut a release:

```bash
git tag -a v0.2.0 -m "Version 0.2.0"
git push origin v0.2.0
```

Pushing a `v*` tag triggers `.github/workflows/ci.yml`'s test matrix; publishing a wheel
to a package index or GitHub Release is a manual `python -m build` + upload for now — there
is no automated release workflow yet.
