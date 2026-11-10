"""Package-local backport of Cangjie runtime module enumeration startup fix.

Only the exact, known 1.0.5 DLL is accepted. The original SDK is never modified.
Both upstream changes are applied: Init uses documented API enumeration,
and ReadModuleInfo passes the basename to WinModule. ABI, unwind records,
and PE directories are preserved.
Upstream source fix: d28cbe02df27c53e278d69a26d9c326ba99bffc2.
"""
import hashlib
import json
from pathlib import Path
import struct
import sys

EXPECTED_SHA256 = "03f4d59a13c7fc1d71523bdd42a05587657105aff14c8288adfdd8fbe5bea089"
PREFIX = "_ZN12MapleRuntime16WinModuleManager"


class PE:
    def __init__(self, data):
        self.data = data
        pe = struct.unpack_from("<I", data, 60)[0]
        if data[:2] != b"MZ" or data[pe:pe + 4] != b"PE\0\0":
            raise ValueError("Not a PE file")
        if struct.unpack_from("<H", data, pe + 4)[0] != 0x8664:
            raise ValueError("Runtime must be x64")
        optional = pe + 24
        if struct.unpack_from("<H", data, optional)[0] != 0x20B:
            raise ValueError("Runtime must be PE32+")
        section_start = optional + struct.unpack_from("<H", data, pe + 20)[0]
        count = struct.unpack_from("<H", data, pe + 6)[0]
        self.sections = [struct.unpack_from("<8sIIII", data, section_start + 40 * i) for i in range(count)]
        directory = self.offset(struct.unpack_from("<I", data, optional + 112)[0])
        fields = struct.unpack_from("<IIHHIIIIIII", data, directory)
        name_count, functions, names, ordinals = fields[7:]
        self.exports = {}
        for i in range(name_count):
            name_offset = self.offset(struct.unpack_from("<I", data, self.offset(names) + 4 * i)[0])
            name = data[name_offset:data.index(0, name_offset)].decode("ascii")
            ordinal = struct.unpack_from("<H", data, self.offset(ordinals) + 2 * i)[0]
            self.exports[name] = struct.unpack_from("<I", data, self.offset(functions) + 4 * ordinal)[0]

    def offset(self, rva):
        for _, _, address, raw_size, raw_offset in self.sections:
            if address <= rva < address + raw_size:
                return raw_offset + rva - address
        raise ValueError(f"RVA outside file sections: {rva:x}")


def backport(data):
    if hashlib.sha256(data).hexdigest() != EXPECTED_SHA256:
        raise ValueError("Unknown runtime hash; refusing to patch")
    pe = PE(data)
    init = pe.exports[PREFIX + "4InitEv"]
    legacy = pe.exports[PREFIX + "19ReadWinModuleAtInitEv"]
    documented_api = pe.exports[PREFIX + "22ReadWinModuleAtRunningEv"]
    offset = pe.offset(init)
    # push rbp; mov rbp,rsp; pop rbp; jmp rel32. No stack frame is
    # active at the branch, so redirecting this tail-call preserves unwind safety.
    if data[offset:offset + 6] != bytes.fromhex("55 48 89 e5 5d e9"):
        raise ValueError("Unexpected Init tail-call encoding")
    if init + 10 + struct.unpack_from("<i", data, offset + 6)[0] != legacy:
        raise ValueError("Init no longer calls the legacy enumeration function")
    result = bytearray(data)
    struct.pack_into("<i", result, offset + 6, documented_api - (init + 10))
    # Upstream also changes WinModule(..., moduleFName.c_str()) to
    # WinModule(..., moduleName.c_str()). ReadModuleInfo's live std::strings:
    # basename at rbp+0x50, full pathname at rbp+0x70. Select basename in both
    # libc++ small-string and heap-string branches. Same instruction lengths.
    name_rva = 0x1A874
    name_offset = pe.offset(name_rva)
    old_name = bytes.fromhex("f6 45 70 01 48 8d 55 71 74 07 48 8b 95 80 00 00 00")
    new_name = bytes.fromhex("f6 45 50 01 48 8d 55 51 74 07 48 8b 95 60 00 00 00")
    if data[name_offset:name_offset + len(old_name)] != old_name:
        raise ValueError("Unexpected ReadModuleInfo module-name argument encoding")
    result[name_offset:name_offset + len(new_name)] = new_name
    return bytes(result), {
        "upstreamCommit": "d28cbe02df27c53e278d69a26d9c326ba99bffc2",
        "method": "API enumeration plus basename WinModule argument (both upstream changes)",
        "moduleNameArgumentRva": hex(name_rva),
        "initRva": hex(init), "legacyRva": hex(legacy), "replacementRva": hex(documented_api),
        "sourceSha256": EXPECTED_SHA256,
        "patchedSha256": hashlib.sha256(result).hexdigest(),
        "changedFileOffsets": [hex(i) for i, (a, b) in enumerate(zip(data, result)) if a != b],
        "windowsRuntimeStatus": "Awaiting target machine test",
    }


if __name__ == "__main__":
    source, destination = map(Path, sys.argv[1:])
    if source.resolve() == destination.resolve() or destination.exists():
        raise SystemExit("Destination must be a new file; source cannot be overwritten")
    data, report = backport(source.read_bytes())
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    destination.with_suffix(".patch.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
