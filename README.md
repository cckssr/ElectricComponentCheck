# ElectricComponentCheck: LCR-Unsicherheiten

Dieses Modul berechnet Messunsicherheiten für LCR-Messungen (Kapazität, Induktivität,
Impedanz, D und Phasenwinkel) auf Basis einer JSON-Spezifikation.

## JSON-Struktur (Kurzfassung)

- Top-Level-Schlüssel: `capacitance`, `inductance`, `impedance`
- Je Type: mehrere Frequenz-Blöcke, z. B. `"10k"`, `"1k_4k"`, jeder mit
  - `freqs_Hz`: Liste der Frequenzen (z. B. `[10000]`)
  - `ranges`: Liste von Bereichen mit Eigenschaften, z. B.:
    - `min`, `max`, `unit` (z. B. `"µF"`, `"nF"`, `"Ω"`, `"kΩ"`, `"MΩ"`)
    - `resolution` (Anzeigeauflösung)
    - Fehlerparameter pro Typ:
      - C: `Ce_pct`, `Ce_digits`, optional `De_abs`, `equiv`
      - L: `Le_pct`, `Le_digits`, optional `De_abs`, `equiv`
      - Z: `Ze_pct`, `Ze_digits`, optional `theta_deg`, `equiv`

## Unterstützte Einheiten

Das Modul akzeptiert sowohl ASCII- als auch Unicode-Varianten:

- Ohm: `Ohm`, `Ω`, `kOhm`, `kΩ`, `MOhm`, `MΩ`
- Kapazität: `F`, `mF`, `uF`, `µF`, `nF`, `pF`
- Induktivität: `H`, `mH`, `uH`, `µH`, `nH`

## Nutzung

```python
from pathlib import Path
from vcr_uncertainties import MeasurementError

spec = MeasurementError(Path("vcr_uncertainties.json"))

# Beispiel: Kapazität
uC, uD, r = spec.uncertainty_capacitance(C_SI=1e-6, freq_hz=10000)
print("uC, uD:", uC, uD)
print("Verwendeter Bereich:", r)

# EQUIV-Modus
mode = spec.find_equiv_mode("capacitance", value_SI=1e-6, freq_hz=10000)
print("EQUIV:", mode)
```

## Tests

```bash
python -m unittest -v test_measurementerror.py
# oder
pytest -q
```

## Hinweise

- Wird ein Wert außerhalb aller Anzeigebereiche übergeben, wird ein `ValueError` geworfen.
- Für `q_rel_error` gilt die Bedingung `Qx*De < 1`.
