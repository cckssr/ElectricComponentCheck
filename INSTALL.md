# Installation

## Requirements

- Python 3.11 or newer
- A VISA backend for talking to the LCR-500 — [NI-VISA](https://www.ni.com/en/support/downloads/drivers/download.ni-visa.html)
  or the pure-Python `pyvisa-py` (installed automatically as a `pyvisa` dependency)

## Install from source

```bash
git clone https://github.com/cckssr/ElectricComponentCheck.git
cd ElectricComponentCheck
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install .
```

## Development install

Installs the package in editable mode plus lint/type-check/test tooling:

```bash
pip install -e . --group dev
pre-commit install
```

(`--group` requires pip 25.1+; on an older pip, install the dev tools listed under
`[dependency-groups]` in `pyproject.toml` by hand.)

## Running

```bash
electric-component-check
# or
python -m electric_component_check
```

On first launch, enter an OpenBIS session token and pick the LCR-500's VISA resource from
the dropdown (refresh if it isn't listed yet).

## Building a distributable package

```bash
pip install build
python -m build
```

Produces `dist/electric_component_check-<version>-py3-none-any.whl` and a matching
source distribution. Install the wheel elsewhere with `pip install dist/*.whl`.

See [DEVELOPMENT.md](DEVELOPMENT.md) for the full development, testing, and release workflow.
