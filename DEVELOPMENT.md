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

## Configuration

`electric_component_check.config.load_config()` resolves a TOML config, overlaid on the
shipped `default_config.toml`. Search order, first match wins:

1. `$ECC_CONFIG` — an explicit path
2. `./ecc.toml` — convenient for running from a repo checkout
3. the OS user-config directory (`platformdirs.user_config_dir("ElectricComponentCheck", "TU-Berlin")`)

A user file only needs to set what differs from the default (deep-merged). Validation fails
fast with a `ConfigError` naming the offending dotted key — e.g. a drive level outside the
LCR-500's supported `{300, 600}` mV, or a sweep frequency not specified in
`vcr_uncertainties.json`. `get_config()` caches the result per process; `reload_config()`
clears the cache.

## The component cycle

`electric_component_check.component_session.ComponentSession` is an explicit state machine
(`CycleState`: `AWAITING_BARCODE → LOOKING_UP → LOADED_KNOWN|LOADED_NEW → MEASURING → MEASURED
→ UPLOADING → DONE|FAILED`) that `MainWindow._apply_state()` uses as the single place deciding
which widgets are enabled — not scattered `setEnabled()` calls in each signal handler. A
successful upload auto-resets the form and returns focus to the barcode field
(`MainWindow.reset_for_next_component()`), so a barcode scanner can drive the whole
scan → measure → upload → scan-next-component loop without a mouse; `Ctrl+N` is the manual
equivalent. When changing this flow, add the transition to `component_session.py`'s allowed-transitions
table first — `MainWindow._transition()` reports (rather than crashes on) anything not listed there.

## Testing

`make test` runs the whole suite; none of it needs the LCR-500 or a live OpenBIS server.
`test_openbis_save.py` exercises `OpenBISController` against a hand-written fake `Openbis` rather
than the real client — see `FakeOpenbis`/`FakeSample`/`FakeDataSet` there for the pattern to extend
if you add a new server call. There is currently no equivalent fake for the LCR-500 driver, so
`LCRController`/`lcr_controller.LCR500HardwareController` are exercised only indirectly (through
`mainwindow.py`'s handlers, driving them by hand with constructed result dicts, as the manual
end-to-end checks in this branch's commits did) — a `pymeasure` `ProtocolAdapter`-based fake would
be the natural next step if this needs to become an automated test.

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
