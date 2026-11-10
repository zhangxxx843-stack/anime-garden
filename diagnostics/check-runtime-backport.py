"""Static regression/guard checks; these do not claim Windows execution success."""
import importlib.util
from pathlib import Path
import struct
import sys

tool = Path(__file__).resolve().parents[1] / "tools/backport-runtime.py"
spec = importlib.util.spec_from_file_location("backport_runtime", tool)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
source = Path(sys.argv[1])
original = source.read_bytes()
original_pe = module.PE(original)
init = original_pe.exports[module.PREFIX + "4InitEv"]
target = original_pe.exports[module.PREFIX + "22ReadWinModuleAtRunningEv"]


def branch_target(data):
    pe = module.PE(data)
    return init + 10 + struct.unpack_from("<i", data, pe.offset(init) + 6)[0]


assert branch_target(original) != target, "Regression input must take the defective path"
patched, report = module.backport(original)
assert branch_target(patched) == target, "Patched startup must take the API enumeration path"
assert len(patched) == len(original)
assert module.PE(patched).exports == original_pe.exports
allowed = set(range(original_pe.offset(init) + 6, original_pe.offset(init) + 10))
allowed.update(original_pe.offset(0x1a874) + i for i in [2, 7, 13])
assert all(i in allowed for i, (a, b) in enumerate(zip(original, patched)) if a != b)
for bad in [original[:-1], bytes([original[0] ^ 1]) + original[1:], patched]:
    try:
        module.backport(bad)
    except ValueError:
        pass
    else:
        raise AssertionError("Unknown, corrupted, or already-patched DLL must be rejected")
assert source.read_bytes() == original, "Original SDK DLL must remain unchanged"
print("PASS: baseline defect, corrected branch, exports/size unchanged, localized change, hash guards, original preserved")
