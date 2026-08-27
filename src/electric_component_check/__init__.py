"""ElectricComponentCheck - LCR bench check workflow with OpenBIS integration."""

__version__ = "0.1.0"
__author__ = "Cedric Kessler"
__email__ = "cedric.kessler@me.com"

from .vcr_uncertainties import MeasurementError

__all__ = ["MeasurementError"]
