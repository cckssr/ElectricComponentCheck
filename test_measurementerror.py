import unittest
from pathlib import Path
import importlib.util
import sys


def _load_module_from_path(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, str(file_path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Kann Modul {module_name} aus {file_path} nicht laden")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


class TestMeasurementError(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec_path = Path("vcr_uncertainties.json")
        module_path = Path(__file__).parent / "vcr_uncertainties.py"
        mod = _load_module_from_path("vcr_uncertainties_module", module_path)
        cls.MeasurementError = getattr(mod, "MeasurementError")
        cls.m_error = cls.MeasurementError(cls.spec_path)

    def test_uncertainty_capacitance(self):
        uC, uD, r = self.m_error.uncertainty_capacitance(1e-6, 10000, 0.01, 0.005)
        self.assertIsInstance(uC, float)
        self.assertIsInstance(uD, float)
        self.assertIsInstance(r, dict)

    def test_uncertainty_inductance(self):
        uL, uD, r = self.m_error.uncertainty_inductance(1e-3, 4000, 0.02, 0.01)
        self.assertIsInstance(uL, float)
        self.assertIsInstance(uD, float)
        self.assertIsInstance(r, dict)

    def test_uncertainty_impedance(self):
        uZ, uTh, r = self.m_error.uncertainty_impedance(100, 100, 0.05, 0.1)
        self.assertIsInstance(uZ, float)
        self.assertIsInstance(uTh, float)
        self.assertIsInstance(r, dict)

    def test_uncertainty_Q_from_D(self):
        # Erst einen Bereich holen
        blk = self.m_error.select_block("capacitance", 10000)
        r, _ = self.m_error.match_range(blk, 1e-6)
        uq = self.m_error.uncertainty_Q_from_D(0.5, r, 0.01)
        self.assertIsInstance(uq, float)

    def test_find_equiv_mode(self):
        equiv = self.m_error.find_equiv_mode("capacitance", 1e-6, 10000)
        self.assertIsInstance(equiv, str)


if __name__ == "__main__":
    unittest.main()
