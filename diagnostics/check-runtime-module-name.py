"""Check constructor argument selection for both libc++ string layouts."""
import runpy
from pathlib import Path
import sys
module=runpy.run_path(str(Path(__file__).resolve().parents[1]/'tools/backport-runtime.py'))
original=Path(sys.argv[1]).read_bytes()
patched,_=module['backport'](original)
pe=module['PE'](patched)
# ReadModuleInfo holds basename at rbp+0x50 and full path at rbp+0x70.
# WinModule copies the selected name for exact lookup during InitAddressScope.
at=pe.offset(0x1a874)
code=patched[at:at+17]
assert code[:3]==bytes.fromhex('f6 45 50'), 'FAIL: WinModule still tests full-path string instead of basename'
assert code[4:7]==bytes.fromhex('48 8d 55') and code[7]==0x51, 'Short string must use basename inline storage'
assert code[10:13]==bytes.fromhex('48 8b 95') and int.from_bytes(code[13:17],'little')==0x60, 'Long string must use basename heap pointer'
print('PASS: WinModule uses basename for both short and long strings')
