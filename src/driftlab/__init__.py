"""DriftLab: reproducible, risk-aware behavioral drift evaluation."""
__version__ = "0.1.0"

# Lazy public imports keep importing statistics independent of application infrastructure.
def __getattr__(name):
    if name == "DriftLab":
        from driftlab.client import DriftLab
        return DriftLab
    raise AttributeError(name)

__all__ = ["DriftLab", "__version__"]
