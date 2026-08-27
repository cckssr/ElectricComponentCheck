# ElectricComponentCheck

A PySide6 desktop app for a single workflow: **plug an electrical component into a
Voltcraft LCR-500 meter, scan its barcode, and record it in [OpenBIS](https://openbis.ch/)** —
either creating a new `ELEKTRONISCHES_BAUTEIL` object or updating an existing one, complete
with measured values and a generated PDF certificate. Built for the TU Berlin physics lab.

## What it does

1. Connect to OpenBIS with a session token and to the LCR-500 over VISA.
2. Scan or type a component's barcode.
   - **Known barcode** → the object's current properties load into the form.
   - **Unknown barcode** → a new object is prepared, ready to create.
3. Fill in or correct manufacturer, status, and type-specific fields (capacitor, resistor,
   inductor, transistor, switch, fuse).
4. Run the full LCR sweep (all specified frequencies, both drive levels). Progress is shown
   live; a plot updates as points come in.
5. Upload: writes the measured reference value + uncertainty into the object's properties
   and attaches a PDF report as a `CALI_CERT` dataset.
6. The form resets and focus returns to the barcode field — ready for the next component.

## Requirements

- Python 3.11+
- A Voltcraft LCR-500 reachable over VISA (USB or serial)
- An OpenBIS server and a valid session token

See [INSTALL.md](INSTALL.md) to get set up.

## Configuration

The OpenBIS server URL, the fixed collection new objects are created into, the sweep's
frequencies and drive levels, and the property codes measurements are written to all live in
a TOML config, not in code -- see `src/electric_component_check/default_config.toml` for
every key and [DEVELOPMENT.md](DEVELOPMENT.md) for the search path. At minimum, set
`[openbis.target].collection` before creating new objects; updating existing objects works
with the shipped default.

## Measurement uncertainty module

`electric_component_check.vcr_uncertainties` computes measurement uncertainties for LCR
readings (capacitance, inductance, impedance, D, and phase angle) from a JSON spec
(`vcr_uncertainties.json`), independent of the GUI:

```python
from electric_component_check.vcr_uncertainties import MeasurementError

spec = MeasurementError(Path("vcr_uncertainties.json"))
uC, uD, r = spec.uncertainty_capacitance(C_SI=1e-6, freq_hz=10000)
```

Supported units (ASCII and Unicode): `Ohm`/`Ω`, `kOhm`/`kΩ`, `MOhm`/`MΩ`, `F`/`mF`/`uF`/`µF`/`nF`/`pF`,
`H`/`mH`/`uH`/`µH`/`nH`.

## Development

See [DEVELOPMENT.md](DEVELOPMENT.md) for building, testing, and releasing.
