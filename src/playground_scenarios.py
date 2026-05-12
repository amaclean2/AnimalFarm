import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "tests"))

_name = "test_cases"
if _name in sys.modules:
    _mod = importlib.reload(sys.modules[_name])
else:
    _mod = importlib.import_module(_name)

SCENARIOS = _mod.TEST_CASES
