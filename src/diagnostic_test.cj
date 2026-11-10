package xin_xuan_glass_probe

import std.fs.{Directory, exists, remove}

@Test
func diagnosticWriteFailureDoesNotPreventApplicationStartup(): Unit {
    if (!exists("target/diagnostic-tests")) { Directory.create("target/diagnostic-tests", recursive: true) }
    let directory = Directory.createTemp("target/diagnostic-tests")
    try {
        writeDiagnostic(directory.toString(), "stage")
        @Expect(Directory.isEmpty(directory))
    } finally { remove(directory, recursive: true) }
}
