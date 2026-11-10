package xin_xuan_glass_probe

import std.fs.File

// Diagnostic failures must never prevent startup in a read-only program directory.
func writeDiagnostic(path: String, stage: String): Unit {
    try { File.writeTo(path, (stage + "\n").toArray()) }
    catch (_: Exception) { println(stage) }
}

func diagnosticStage(stage: String): Unit { writeDiagnostic("glass-last-stage.txt", stage) }
