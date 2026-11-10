package xin_xuan_glass_probe.importing

import std.fs.{File, FileInfo}
import cui.Surface
import xin_xuan_glass_probe.shopping.{CsvIssue, CsvReport, validateProductCsv}

/** CPU-side decode check; creates no desktop window and always releases the surface. */
public func checkLocalProductImage(path: String): ?String {
    try {
        let info = FileInfo(path)
        if (!info.isRegular()) { return Some("图片路径不是普通文件，请选择本地图片。") }
        if (!info.canRead()) { return Some("图片无法读取，请检查文件权限。") }
        let surface = Surface.load(path)
        surface.close()
        None
    } catch (_: Exception) {
        Some("图片不存在、无法读取或不是可解码的图片，请补齐后重新校验。")
    }
}

/** Read-only batch preflight. No partial import, catalog mutation or file copying. */
public func readProductCsv(path: String): CsvReport {
    let text = try {
        if (!FileInfo(path).isRegular()) { throw IllegalArgumentException("请选择 CSV 文件。") }
        String.fromUtf8(File.readFrom(path))
    } catch (_: Exception) {
        return CsvReport([], [CsvIssue(0, "CSV 文件", "无法读取 CSV，请确认文件存在，并另存为 CSV UTF-8 编码。")], 0, 0)
    }
    validateProductCsv(text, path, checkLocalProductImage)
}
